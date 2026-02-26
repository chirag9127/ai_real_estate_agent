"""Unit tests for the WhatsApp integration (service + webhook router)."""

from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base, SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.pipeline_run import PipelineRun, PipelineStage, PipelineStatus  # noqa: E402
from app.models.transcript import Transcript  # noqa: E402
from app.services import whatsapp_service  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _setup_db():
    """Create tables before each test and drop after."""
    import app.models  # noqa: F401 -- register all models
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _clear_conversations():
    """Reset in-memory conversation state between tests."""
    whatsapp_service._active_conversations.clear()
    yield
    whatsapp_service._active_conversations.clear()


@pytest.fixture()
def client(db):
    """FastAPI test client with overridden DB dependency."""

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


class TestHandleIncomingMessage:
    """Tests for whatsapp_service.handle_incoming_message."""

    def test_empty_body_returns_prompt(self, db):
        reply, run_id = whatsapp_service.handle_incoming_message(
            db, from_number="whatsapp:+1111111111", body="   "
        )
        assert "describing what kind of property" in reply
        assert run_id is None

    def test_first_message_creates_transcript_and_pipeline(self, db):
        reply, run_id = whatsapp_service.handle_incoming_message(
            db,
            from_number="whatsapp:+2222222222",
            body="Looking for a 3-bed house in Austin under 500k",
            profile_name="Alice",
        )
        assert "Thanks Alice" in reply
        assert run_id is not None

        # Verify transcript was created
        transcript = db.query(Transcript).filter(Transcript.upload_method == "whatsapp").first()
        assert transcript is not None
        assert "3-bed house" in transcript.raw_text

        # Verify pipeline run was created
        pipeline_run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        assert pipeline_run is not None
        assert pipeline_run.status == PipelineStatus.IN_PROGRESS.value
        assert pipeline_run.current_stage == PipelineStage.EXTRACTION.value
        assert pipeline_run.transcript_id == transcript.id

    def test_duplicate_message_while_pipeline_running(self, db):
        # First message
        _, run_id = whatsapp_service.handle_incoming_message(
            db,
            from_number="whatsapp:+3333333333",
            body="I want a condo in Miami",
        )
        assert run_id is not None

        # Second message from same number while pipeline is in progress
        reply, run_id2 = whatsapp_service.handle_incoming_message(
            db,
            from_number="whatsapp:+3333333333",
            body="Actually I want a house",
        )
        assert "still in progress" in reply
        assert run_id2 is None

    def test_new_message_after_pipeline_completed(self, db):
        # First message
        _, run_id = whatsapp_service.handle_incoming_message(
            db,
            from_number="whatsapp:+4444444444",
            body="Looking for a house in Denver",
        )
        # Mark pipeline as completed
        pipeline_run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        pipeline_run.status = PipelineStatus.COMPLETED.value
        db.commit()

        # New message should create a new pipeline
        reply, run_id2 = whatsapp_service.handle_incoming_message(
            db,
            from_number="whatsapp:+4444444444",
            body="Now looking for a condo in Seattle",
        )
        assert "Thanks" in reply
        assert run_id2 is not None
        assert run_id2 != run_id

    def test_new_message_after_pipeline_failed(self, db):
        # First message
        _, run_id = whatsapp_service.handle_incoming_message(
            db,
            from_number="whatsapp:+5555555555",
            body="Looking for a house",
        )
        # Mark pipeline as failed
        pipeline_run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        pipeline_run.status = PipelineStatus.FAILED.value
        db.commit()

        # New message should create a new pipeline
        reply, run_id2 = whatsapp_service.handle_incoming_message(
            db,
            from_number="whatsapp:+5555555555",
            body="Looking for a house in Portland",
        )
        assert run_id2 is not None
        assert run_id2 != run_id

    def test_profile_name_omitted(self, db):
        reply, _ = whatsapp_service.handle_incoming_message(
            db,
            from_number="whatsapp:+6666666666",
            body="3 bed house in Chicago",
        )
        assert "Thanks!" in reply


class TestConversationTracking:
    def test_get_active_conversations(self, db):
        whatsapp_service.handle_incoming_message(
            db, from_number="whatsapp:+1000000001", body="house in LA"
        )
        convos = whatsapp_service.get_active_conversations()
        assert "whatsapp:+1000000001" in convos

    def test_clear_conversation(self, db):
        whatsapp_service.handle_incoming_message(
            db, from_number="whatsapp:+1000000002", body="house in LA"
        )
        assert whatsapp_service.clear_conversation("whatsapp:+1000000002") is True
        assert whatsapp_service.clear_conversation("whatsapp:+1000000002") is False

    def test_get_pipeline_status_message(self, db):
        whatsapp_service.handle_incoming_message(
            db, from_number="whatsapp:+1000000003", body="house in LA"
        )
        msg = whatsapp_service.get_pipeline_status_message(db, "whatsapp:+1000000003")
        assert msg is not None
        assert "extraction" in msg

    def test_get_pipeline_status_no_conversation(self, db):
        msg = whatsapp_service.get_pipeline_status_message(db, "whatsapp:+9999999999")
        assert msg is None


class TestSendWhatsAppMessage:
    def test_simulated_send_when_no_credentials(self):
        result = whatsapp_service.send_whatsapp_message(
            "whatsapp:+1234567890", "Hello!"
        )
        assert result["status"] == "simulated"
        assert result["to"] == "whatsapp:+1234567890"
        assert result["body"] == "Hello!"

    @patch("app.services.whatsapp_service.TwilioClient")
    def test_real_send_with_credentials(self, mock_twilio_cls):
        mock_message = MagicMock()
        mock_message.sid = "SM_TEST_SID"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_twilio_cls.return_value = mock_client

        with patch.object(whatsapp_service.settings, "twilio_account_sid", "ACTEST"), \
             patch.object(whatsapp_service.settings, "twilio_auth_token", "test_token"), \
             patch.object(whatsapp_service.settings, "twilio_whatsapp_number", "whatsapp:+15551234567"):
            result = whatsapp_service.send_whatsapp_message(
                "+1234567890", "Hello!"
            )

        assert result["status"] == "sent"
        assert result["sid"] == "SM_TEST_SID"
        assert result["to"] == "whatsapp:+1234567890"
        mock_client.messages.create.assert_called_once_with(
            body="Hello!",
            from_="whatsapp:+15551234567",
            to="whatsapp:+1234567890",
        )

    def test_whatsapp_prefix_not_duplicated(self):
        result = whatsapp_service.send_whatsapp_message(
            "whatsapp:+1234567890", "Test"
        )
        # In simulated mode, just verify the to field is preserved
        assert result["to"] == "whatsapp:+1234567890"


# ---------------------------------------------------------------------------
# Webhook endpoint tests
# ---------------------------------------------------------------------------


class TestWhatsAppWebhook:
    """Tests for the /api/v1/whatsapp/webhook endpoint."""

    def test_webhook_creates_transcript_and_returns_twiml(self, client, db):
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            data={
                "From": "whatsapp:+19998887777",
                "Body": "I need a 2-bed apartment in San Francisco under 800k",
                "ProfileName": "Bob",
                "To": "whatsapp:+14155238886",
                "MessageSid": "SM_FAKE_SID",
            },
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/xml; charset=utf-8"
        # TwiML should contain a <Message> element with the reply
        assert "<Message>" in resp.text
        assert "Thanks Bob" in resp.text
        assert "Pipeline #" in resp.text

    def test_webhook_empty_body(self, client):
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            data={
                "From": "whatsapp:+10000000000",
                "Body": "",
            },
        )
        assert resp.status_code == 200
        assert "describing what kind of property" in resp.text

    def test_webhook_duplicate_sender(self, client, db):
        # First message
        client.post(
            "/api/v1/whatsapp/webhook",
            data={
                "From": "whatsapp:+17776665555",
                "Body": "House in Dallas",
            },
        )
        # Second message from same sender
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            data={
                "From": "whatsapp:+17776665555",
                "Body": "Any updates?",
            },
        )
        assert resp.status_code == 200
        assert "still in progress" in resp.text

    @patch("app.routers.whatsapp._validate_twilio_signature", return_value=False)
    def test_webhook_rejects_invalid_signature(self, mock_validate, client):
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            data={
                "From": "whatsapp:+10000000000",
                "Body": "Hello",
            },
        )
        assert resp.status_code == 403


class TestManagementEndpoints:
    """Tests for the dashboard management API."""

    def test_list_conversations_empty(self, client):
        resp = client.get("/api/v1/whatsapp/conversations")
        assert resp.status_code == 200
        assert resp.json() == {"conversations": {}}

    def test_list_conversations_after_message(self, client, db):
        client.post(
            "/api/v1/whatsapp/webhook",
            data={
                "From": "whatsapp:+11112223333",
                "Body": "House in NYC",
            },
        )
        resp = client.get("/api/v1/whatsapp/conversations")
        assert resp.status_code == 200
        convos = resp.json()["conversations"]
        assert "whatsapp:+11112223333" in convos

    def test_get_status_no_conversation(self, client):
        resp = client.get("/api/v1/whatsapp/status/whatsapp:+19999999999")
        assert resp.status_code == 200
        assert resp.json()["status"] == "no_active_pipeline"

    def test_send_message_simulated(self, client):
        resp = client.post(
            "/api/v1/whatsapp/send-message",
            json={
                "to_number": "whatsapp:+12223334444",
                "message": "Test message",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "simulated"

    def test_send_results_no_rankings(self, client, db):
        # Create a pipeline run with no rankings
        transcript = Transcript(raw_text="test", upload_method="whatsapp", status="uploaded")
        db.add(transcript)
        db.commit()
        db.refresh(transcript)

        run = PipelineRun(
            transcript_id=transcript.id,
            current_stage=PipelineStage.REVIEW.value,
            status=PipelineStatus.COMPLETED.value,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        resp = client.post(
            "/api/v1/whatsapp/send-results",
            json={
                "to_number": "whatsapp:+15556667777",
                "pipeline_run_id": run.id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "simulated"
        assert "no ranked listings" in data["body"].lower()


# ---------------------------------------------------------------------------
# Background pipeline execution tests
# ---------------------------------------------------------------------------


class TestRunPipelineAsync:
    """Tests for whatsapp_service.run_pipeline_async."""

    def _make_pipeline_run(self, db) -> tuple[Transcript, PipelineRun]:
        transcript = Transcript(raw_text="3-bed house in Austin", upload_method="whatsapp", status="uploaded")
        db.add(transcript)
        db.commit()
        db.refresh(transcript)

        run = PipelineRun(
            transcript_id=transcript.id,
            current_stage=PipelineStage.EXTRACTION.value,
            status=PipelineStatus.IN_PROGRESS.value,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return transcript, run

    @patch("app.services.whatsapp_service.send_whatsapp_message")
    @patch("app.services.whatsapp_service.send_pipeline_results")
    @patch("app.services.whatsapp_service.pipeline_service")
    @patch("app.services.whatsapp_service.get_llm_provider")
    def test_happy_path_all_steps_succeed(
        self, mock_llm, mock_pipeline_svc, mock_send_results, mock_send_msg, db
    ):
        _, run = self._make_pipeline_run(db)
        from_number = "whatsapp:+18001111111"
        whatsapp_service._active_conversations[from_number] = run.id

        # Mock all three pipeline steps to return a successful run
        successful_run = MagicMock()
        successful_run.status = PipelineStatus.COMPLETED.value

        mock_pipeline_svc.run_extraction_step = AsyncMock(return_value=successful_run)
        mock_pipeline_svc.run_search_step = AsyncMock(return_value=successful_run)
        mock_pipeline_svc.run_ranking_step = AsyncMock(return_value=successful_run)

        # Patch SessionLocal to return our test db
        with patch("app.services.whatsapp_service.SessionLocal", return_value=db):
            asyncio.run(whatsapp_service.run_pipeline_async(run.id, from_number))

        # All three steps should have been called
        mock_pipeline_svc.run_extraction_step.assert_called_once()
        mock_pipeline_svc.run_search_step.assert_called_once()
        mock_pipeline_svc.run_ranking_step.assert_called_once()

        # Results should be sent and conversation cleared
        mock_send_results.assert_called_once()
        assert from_number not in whatsapp_service._active_conversations

    @patch("app.services.whatsapp_service.send_whatsapp_message")
    @patch("app.services.whatsapp_service.send_pipeline_results")
    @patch("app.services.whatsapp_service.pipeline_service")
    @patch("app.services.whatsapp_service.get_llm_provider")
    def test_extraction_fails_stops_pipeline(
        self, mock_llm, mock_pipeline_svc, mock_send_results, mock_send_msg, db
    ):
        _, run = self._make_pipeline_run(db)
        from_number = "whatsapp:+18002222222"
        whatsapp_service._active_conversations[from_number] = run.id

        # Extraction fails
        failed_run = MagicMock()
        failed_run.status = PipelineStatus.FAILED.value
        failed_run.error_message = "LLM extraction error"

        mock_pipeline_svc.run_extraction_step = AsyncMock(return_value=failed_run)

        with patch("app.services.whatsapp_service.SessionLocal", return_value=db):
            asyncio.run(whatsapp_service.run_pipeline_async(run.id, from_number))

        # Only extraction should have been called
        mock_pipeline_svc.run_extraction_step.assert_called_once()
        mock_pipeline_svc.run_search_step.assert_not_called()
        mock_pipeline_svc.run_ranking_step.assert_not_called()

        # Error message sent, results NOT sent
        mock_send_msg.assert_called_once()
        assert "extraction" in mock_send_msg.call_args[0][1].lower()
        mock_send_results.assert_not_called()

        # Conversation cleared
        assert from_number not in whatsapp_service._active_conversations

    @patch("app.services.whatsapp_service.send_whatsapp_message")
    @patch("app.services.whatsapp_service.pipeline_service")
    @patch("app.services.whatsapp_service.get_llm_provider")
    def test_unexpected_error_marks_pipeline_failed(
        self, mock_llm, mock_pipeline_svc, mock_send_msg, db
    ):
        _, run = self._make_pipeline_run(db)
        run_id = run.id
        from_number = "whatsapp:+18003333333"
        whatsapp_service._active_conversations[from_number] = run_id

        # LLM provider raises an unexpected error
        mock_llm.side_effect = RuntimeError("LLM provider unavailable")

        with patch("app.services.whatsapp_service.SessionLocal", return_value=db):
            asyncio.run(whatsapp_service.run_pipeline_async(run_id, from_number))

        # Pipeline run should be marked as failed in DB -- re-query to avoid
        # stale ORM identity-map issues after the background task modified it.
        db.expire_all()
        updated_run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        assert updated_run is not None
        assert updated_run.status == PipelineStatus.FAILED.value
        assert "Unexpected error" in updated_run.error_message

        # Error message sent to user
        mock_send_msg.assert_called_once()
        assert "unexpected error" in mock_send_msg.call_args[0][1].lower()

        # Conversation cleared
        assert from_number not in whatsapp_service._active_conversations

    @patch("app.services.whatsapp_service.send_whatsapp_message")
    def test_pipeline_run_not_found(self, mock_send_msg, db):
        from_number = "whatsapp:+18004444444"
        whatsapp_service._active_conversations[from_number] = 99999

        with patch("app.services.whatsapp_service.SessionLocal", return_value=db):
            asyncio.run(whatsapp_service.run_pipeline_async(99999, from_number))

        # Error message sent
        mock_send_msg.assert_called_once()
        assert "something went wrong" in mock_send_msg.call_args[0][1].lower()

        # Conversation cleared
        assert from_number not in whatsapp_service._active_conversations

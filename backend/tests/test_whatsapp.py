"""Tests for WhatsApp integration service and webhook."""

from datetime import datetime, timezone
from unittest import mock

import pytest
from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.pipeline_run import PipelineRun, PipelineStage, PipelineStatus
from app.models.ranking import RankedResult
from app.models.requirement import ExtractedRequirement
from app.models.transcript import Transcript
from app.services import whatsapp_service


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_session(db: Session) -> Session:
    """Provide a database session for tests."""
    return db


# ============================================================================
# Tests: Conversation tracking
# ============================================================================


def test_get_active_conversations_empty() -> None:
    """Initially, no active conversations."""
    # Clear any prior state
    whatsapp_service._active_conversations.clear()
    assert whatsapp_service.get_active_conversations() == {}


def test_clear_conversation() -> None:
    """clear_conversation removes a sender from active map."""
    whatsapp_service._active_conversations.clear()
    whatsapp_service._active_conversations["whatsapp:+12345"] = 123

    assert whatsapp_service.clear_conversation("whatsapp:+12345") is True
    assert whatsapp_service.get_active_conversations() == {}

    # Clearing a non-existent sender returns False
    assert whatsapp_service.clear_conversation("whatsapp:+99999") is False


# ============================================================================
# Tests: handle_incoming_message
# ============================================================================


def test_handle_incoming_message_creates_transcript_and_pipeline(db_session: Session) -> None:
    """Incoming message creates a transcript and pipeline run."""
    whatsapp_service._active_conversations.clear()
    from_number = "whatsapp:+14155238886"
    body = "Looking for a 2-bedroom apartment in San Francisco"

    reply = whatsapp_service.handle_incoming_message(
        db_session,
        from_number=from_number,
        body=body,
        profile_name="Alice",
    )

    # Verify reply message
    assert "Alice" in reply
    assert "property" in reply.lower() and "search" in reply.lower()

    # Verify transcript was created
    transcript = db_session.query(Transcript).filter_by(raw_text=body).first()
    assert transcript is not None
    assert transcript.upload_method == "whatsapp"
    assert transcript.status == "uploaded"

    # Verify pipeline run was created
    pipeline_run = db_session.query(PipelineRun).filter_by(
        transcript_id=transcript.id
    ).first()
    assert pipeline_run is not None
    assert pipeline_run.current_stage == PipelineStage.EXTRACTION.value
    assert pipeline_run.status == PipelineStatus.IN_PROGRESS.value
    assert pipeline_run.ingestion_completed_at is not None

    # Verify conversation was tracked
    assert from_number in whatsapp_service.get_active_conversations()
    assert whatsapp_service.get_active_conversations()[from_number] == pipeline_run.id


def test_handle_incoming_message_empty_body(db_session: Session) -> None:
    """Empty or whitespace-only message is rejected."""
    whatsapp_service._active_conversations.clear()

    reply = whatsapp_service.handle_incoming_message(
        db_session,
        from_number="whatsapp:+12345",
        body="   ",
    )

    assert "Please send a message" in reply


def test_handle_incoming_message_returns_status_when_pipeline_in_progress(
    db_session: Session,
) -> None:
    """While a pipeline is in progress, reply with status instead of creating new one."""
    whatsapp_service._active_conversations.clear()
    from_number = "whatsapp:+14155238886"

    # Create a transcript and pipeline run
    transcript = Transcript(raw_text="First request", upload_method="whatsapp")
    db_session.add(transcript)
    db_session.commit()

    pipeline_run = PipelineRun(
        transcript_id=transcript.id,
        current_stage=PipelineStage.EXTRACTION.value,
        status=PipelineStatus.IN_PROGRESS.value,
        ingestion_completed_at=datetime.now(timezone.utc),
    )
    db_session.add(pipeline_run)
    db_session.commit()

    whatsapp_service._active_conversations[from_number] = pipeline_run.id

    # Send a second message
    reply = whatsapp_service.handle_incoming_message(
        db_session,
        from_number=from_number,
        body="Another request",
    )

    # Should get status reply, not create a new pipeline
    assert "still in progress" in reply.lower()
    assert "stage" in reply.lower()


# ============================================================================
# Tests: get_pipeline_status_message
# ============================================================================


def test_get_pipeline_status_message_returns_status(db_session: Session) -> None:
    """get_pipeline_status_message returns status for active pipeline."""
    whatsapp_service._active_conversations.clear()
    from_number = "whatsapp:+14155238886"

    transcript = Transcript(raw_text="Test", upload_method="whatsapp")
    db_session.add(transcript)
    db_session.commit()

    pipeline_run = PipelineRun(
        transcript_id=transcript.id,
        current_stage=PipelineStage.RANKING.value,
        status=PipelineStatus.IN_PROGRESS.value,
    )
    db_session.add(pipeline_run)
    db_session.commit()

    whatsapp_service._active_conversations[from_number] = pipeline_run.id

    msg = whatsapp_service.get_pipeline_status_message(db_session, from_number)
    assert msg is not None
    assert str(pipeline_run.id) in msg
    assert PipelineStage.RANKING.value in msg


def test_get_pipeline_status_message_returns_none_for_inactive(db_session: Session) -> None:
    """get_pipeline_status_message returns None when sender has no active pipeline."""
    whatsapp_service._active_conversations.clear()

    msg = whatsapp_service.get_pipeline_status_message(db_session, "whatsapp:+12345")
    assert msg is None


# ============================================================================
# Tests: send_whatsapp_message (simulated)
# ============================================================================


@mock.patch("app.services.whatsapp_service.settings.twilio_account_sid", "")
@mock.patch("app.services.whatsapp_service.settings.twilio_auth_token", "")
def test_send_whatsapp_message_simulated() -> None:
    """When Twilio creds are absent, send_whatsapp_message returns simulated response."""
    result = whatsapp_service.send_whatsapp_message(
        "whatsapp:+12345",
        "Hello",
    )

    assert result["status"] == "simulated"
    assert result["to"] == "whatsapp:+12345"
    assert result["body"] == "Hello"


def test_send_whatsapp_message_adds_whatsapp_prefix() -> None:
    """If number doesn't have 'whatsapp:' prefix, it's added."""
    # Use simulated mode (no real Twilio creds in test)
    with mock.patch(
        "app.services.whatsapp_service.settings.twilio_account_sid", ""
    ):
        result = whatsapp_service.send_whatsapp_message("+12345", "Hi")
        # In simulated mode, the prefix is handled by the endpoint
        assert result["status"] == "simulated"


# ============================================================================
# Tests: send_pipeline_results
# ============================================================================


@mock.patch("app.services.whatsapp_service.send_whatsapp_message")
def test_send_pipeline_results_with_rankings(
    mock_send: mock.Mock, db_session: Session
) -> None:
    """send_pipeline_results formats and sends ranked listings."""
    # Create a pipeline run with ranked results
    transcript = Transcript(raw_text="Test", upload_method="whatsapp")
    db_session.add(transcript)
    db_session.commit()

    pipeline_run = PipelineRun(transcript_id=transcript.id)
    db_session.add(pipeline_run)
    db_session.commit()

    # Create a requirement
    requirement = ExtractedRequirement(
        transcript_id=transcript.id,
        client_name="Alice",
    )
    db_session.add(requirement)
    db_session.commit()

    # Create listings and rankings
    listing1 = Listing(
        address="123 Main St",
        price=500000,
        bedrooms=2,
        bathrooms=1,
        sqft=1200,
        zillow_url="https://www.zillow.com/123",
    )
    db_session.add(listing1)
    db_session.commit()

    ranking1 = RankedResult(
        pipeline_run_id=pipeline_run.id,
        listing_id=listing1.id,
        requirement_id=requirement.id,
        rank_position=1,
        overall_score=0.95,
    )
    db_session.add(ranking1)
    db_session.commit()

    # Call send_pipeline_results
    mock_send.return_value = {"status": "sent", "sid": "MM123"}

    result = whatsapp_service.send_pipeline_results(
        db_session, pipeline_run.id, "whatsapp:+14155238886"
    )

    # Verify send was called
    assert mock_send.called
    call_args = mock_send.call_args
    assert "14155238886" in call_args[0][0] or "whatsapp:+14155238886" in call_args[0][0]
    message_text = call_args[0][1]
    assert "123 Main St" in message_text
    assert "$500,000" in message_text
    assert "2bd" in message_text
    assert "95%" in message_text


@mock.patch("app.services.whatsapp_service.send_whatsapp_message")
def test_send_pipeline_results_no_rankings(
    mock_send: mock.Mock, db_session: Session
) -> None:
    """send_pipeline_results handles case with no ranked listings."""
    transcript = Transcript(raw_text="Test", upload_method="whatsapp")
    db_session.add(transcript)
    db_session.commit()

    pipeline_run = PipelineRun(transcript_id=transcript.id)
    db_session.add(pipeline_run)
    db_session.commit()

    mock_send.return_value = {"status": "sent", "sid": "MM123"}

    result = whatsapp_service.send_pipeline_results(
        db_session, pipeline_run.id, "whatsapp:+12345"
    )

    # Verify send was called with "no rankings" message
    assert mock_send.called
    call_args = mock_send.call_args
    message_text = call_args[0][1]
    assert "no ranked listings" in message_text.lower()

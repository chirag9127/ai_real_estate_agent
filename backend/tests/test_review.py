"""Unit tests for the review / rejection workflow."""

from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base
from app.models.client import Client
from app.models.transcript import Transcript
from app.models.pipeline_run import PipelineRun
from app.models.requirement import ExtractedRequirement
from app.models.listing import Listing
from app.models.ranking import RankedResult
from app.models.rejection import RejectionReason, REJECTION_REASON_KEYS
from app.schemas.rejection import RejectRequest, RejectionReasonResponse
from app.services import review_service


@pytest.fixture()
def db():
    """Create an in-memory SQLite database with all tables."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture()
def sample_data(db: Session):
    """Insert minimal related rows so we can create RankedResult records."""
    client = Client(name="Test Client")
    db.add(client)
    db.flush()

    transcript = Transcript(
        client_id=client.id,
        raw_text="test transcript",
    )
    db.add(transcript)
    db.flush()

    pipeline_run = PipelineRun(transcript_id=transcript.id)
    db.add(pipeline_run)
    db.flush()

    requirement = ExtractedRequirement(
        transcript_id=transcript.id,
    )
    db.add(requirement)
    db.flush()

    listing = Listing(external_id="Z1")
    db.add(listing)
    db.flush()

    ranked = RankedResult(
        pipeline_run_id=pipeline_run.id,
        listing_id=listing.id,
        requirement_id=requirement.id,
        overall_score=0.85,
        must_have_pass=True,
        nice_to_have_score=0.7,
        rank_position=1,
    )
    db.add(ranked)
    db.commit()
    return {
        "pipeline_run": pipeline_run,
        "ranked": ranked,
        "listing": listing,
    }


class TestRejectionModel:
    """Tests for the RejectionReason model."""

    def test_predefined_keys(self):
        assert "location_mismatch" in REJECTION_REASON_KEYS
        assert "overpriced" in REJECTION_REASON_KEYS
        assert "other" in REJECTION_REASON_KEYS
        assert len(REJECTION_REASON_KEYS) == 7

    def test_create_rejection_reason(self, db: Session, sample_data: dict):
        rr = sample_data["ranked"]
        pr = sample_data["pipeline_run"]

        rejection = RejectionReason(
            ranked_result_id=rr.id,
            pipeline_run_id=pr.id,
            reason="overpriced",
            details=None,
        )
        db.add(rejection)
        db.commit()
        db.refresh(rejection)

        assert rejection.id is not None
        assert rejection.reason == "overpriced"
        assert rejection.details is None
        assert rejection.created_at is not None

    def test_create_rejection_with_details(self, db: Session, sample_data: dict):
        rr = sample_data["ranked"]
        pr = sample_data["pipeline_run"]

        rejection = RejectionReason(
            ranked_result_id=rr.id,
            pipeline_run_id=pr.id,
            reason="other",
            details="The yard faces a highway.",
        )
        db.add(rejection)
        db.commit()
        db.refresh(rejection)

        assert rejection.reason == "other"
        assert rejection.details == "The yard faces a highway."


class TestRejectionSchema:
    """Tests for the rejection Pydantic schemas."""

    def test_reject_request_minimal(self):
        req = RejectRequest(reason="overpriced")
        assert req.reason == "overpriced"
        assert req.details is None

    def test_reject_request_with_details(self):
        req = RejectRequest(reason="other", details="Too noisy")
        assert req.details == "Too noisy"

    def test_rejection_response_from_attributes(self, db: Session, sample_data: dict):
        rr = sample_data["ranked"]
        pr = sample_data["pipeline_run"]

        rejection = RejectionReason(
            ranked_result_id=rr.id,
            pipeline_run_id=pr.id,
            reason="lot_too_small",
        )
        db.add(rejection)
        db.commit()
        db.refresh(rejection)

        resp = RejectionReasonResponse.model_validate(rejection)
        assert resp.id == rejection.id
        assert resp.reason == "lot_too_small"
        assert resp.details is None
        assert resp.ranked_result_id == rr.id


class TestReviewService:
    """Tests for the review_service reject_listing and get_rejections."""

    def test_reject_listing_persists(self, db: Session, sample_data: dict):
        pr = sample_data["pipeline_run"]
        rr = sample_data["ranked"]

        result = review_service.reject_listing(
            db, pr.id, rr.id, reason="overpriced", details=None
        )

        assert result.approved_by_harry is False
        assert result.rejection_reason == "overpriced"
        assert result.rejection_details is None

        # Verify a RejectionReason record was created
        reasons = db.query(RejectionReason).filter_by(ranked_result_id=rr.id).all()
        assert len(reasons) == 1
        assert reasons[0].reason == "overpriced"

    def test_reject_listing_with_details(self, db: Session, sample_data: dict):
        pr = sample_data["pipeline_run"]
        rr = sample_data["ranked"]

        result = review_service.reject_listing(
            db, pr.id, rr.id, reason="other", details="Bad neighborhood"
        )

        assert result.rejection_reason == "other"
        assert result.rejection_details == "Bad neighborhood"

        reasons = db.query(RejectionReason).filter_by(ranked_result_id=rr.id).all()
        assert len(reasons) == 1
        assert reasons[0].details == "Bad neighborhood"

    def test_reject_listing_not_found(self, db: Session, sample_data: dict):
        pr = sample_data["pipeline_run"]
        with pytest.raises(ValueError, match="not found"):
            review_service.reject_listing(db, pr.id, 9999, reason="overpriced")

    def test_get_rejections(self, db: Session, sample_data: dict):
        pr = sample_data["pipeline_run"]
        rr = sample_data["ranked"]

        # Create two rejections (simulating re-rejection)
        review_service.reject_listing(db, pr.id, rr.id, reason="overpriced")

        rejections = review_service.get_rejections(db, pr.id)
        assert len(rejections) == 1
        assert rejections[0].reason == "overpriced"

    def test_get_rejections_empty(self, db: Session, sample_data: dict):
        pr = sample_data["pipeline_run"]
        rejections = review_service.get_rejections(db, pr.id)
        assert rejections == []

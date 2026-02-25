"""WhatsApp integration: receive messages, trigger pipeline, send results."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from twilio.rest import Client as TwilioClient

from app.config import settings
from app.database import SessionLocal
from app.llm.factory import get_llm_provider
from app.models.listing import Listing
from app.models.pipeline_run import PipelineRun, PipelineStage, PipelineStatus
from app.models.ranking import RankedResult
from app.models.requirement import ExtractedRequirement
from app.models.transcript import Transcript
from app.services import extraction_service, ranking_service, search_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory conversation tracker
# ---------------------------------------------------------------------------
# Maps a WhatsApp sender number to the pipeline_run_id they are waiting on.
# In production this would live in the DB or a cache; keeping it simple here.
_active_conversations: dict[str, int] = {}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_active_conversations() -> dict[str, int]:
    """Return a shallow copy of the active conversation map."""
    return dict(_active_conversations)


def handle_incoming_message(
    db: Session,
    from_number: str,
    body: str,
    profile_name: str | None = None,
) -> tuple[str, int | None]:
    """Process an incoming WhatsApp message.

    Returns ``(reply_text, pipeline_run_id)``.  *pipeline_run_id* is set only
    when a **new** pipeline was created and should be scheduled for background
    execution; otherwise it is ``None``.

    The first message from a number is treated as a property-requirement
    transcript.  Subsequent messages while a pipeline is running return a
    status update.
    """
    body = body.strip()
    if not body:
        return (
            "Please send a message describing what kind of property you're looking for.",
            None,
        )

    # If the user already has a pipeline in progress, return status
    if from_number in _active_conversations:
        run_id = _active_conversations[from_number]
        run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if run and run.status == PipelineStatus.IN_PROGRESS.value:
            return (
                f"Your property search is still in progress "
                f"(stage: {run.current_stage}). "
                "I'll message you when results are ready!",
                None,
            )
        # Previous run finished or failed -- allow a new one
        del _active_conversations[from_number]

    # Create a transcript from the WhatsApp message
    transcript = Transcript(
        raw_text=body,
        upload_method="whatsapp",
        status="uploaded",
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)

    # Create a pipeline run (ingestion complete)
    pipeline_run = PipelineRun(
        transcript_id=transcript.id,
        current_stage=PipelineStage.EXTRACTION.value,
        status=PipelineStatus.IN_PROGRESS.value,
        ingestion_completed_at=datetime.now(timezone.utc),
    )
    db.add(pipeline_run)
    db.commit()
    db.refresh(pipeline_run)

    _active_conversations[from_number] = pipeline_run.id

    logger.info(
        "WhatsApp message from %s (%s) created transcript=%d pipeline_run=%d",
        from_number,
        profile_name or "unknown",
        transcript.id,
        pipeline_run.id,
    )

    return (
        f"Thanks{(' ' + profile_name) if profile_name else ''}! "
        f"I've received your property requirements and started searching. "
        f"Pipeline #{pipeline_run.id} is now running. "
        "I'll send you the results once they're ready!",
        pipeline_run.id,
    )


async def run_pipeline_async(pipeline_run_id: int, from_number: str) -> None:
    """Execute the full pipeline (extract -> search -> rank) in the background.

    Uses its own DB session so it is independent of the request lifecycle.
    On completion (or failure) sends a WhatsApp message back to the user.
    """
    db = SessionLocal()
    try:
        pipeline_run = (
            db.query(PipelineRun).filter(PipelineRun.id == pipeline_run_id).first()
        )
        if not pipeline_run:
            logger.error("Pipeline run %d not found for background execution", pipeline_run_id)
            return

        llm = get_llm_provider()

        # --- Extraction ---
        try:
            await extraction_service.extract_requirements(
                db, pipeline_run.transcript_id, llm
            )
            pipeline_run.extraction_completed_at = datetime.now(timezone.utc)
            pipeline_run.current_stage = PipelineStage.SEARCH.value
            db.commit()
        except Exception as exc:
            logger.exception("WhatsApp pipeline failed at extraction")
            pipeline_run.status = PipelineStatus.FAILED.value
            pipeline_run.error_message = str(exc)
            db.commit()
            send_whatsapp_message(
                from_number,
                f"Sorry, I couldn't extract requirements from your message. "
                f"Error: {exc}. Please try again with more detail.",
            )
            return

        # --- Search ---
        requirement = (
            db.query(ExtractedRequirement)
            .filter(ExtractedRequirement.transcript_id == pipeline_run.transcript_id)
            .first()
        )
        if not requirement:
            pipeline_run.status = PipelineStatus.FAILED.value
            pipeline_run.error_message = "No extracted requirement found"
            db.commit()
            send_whatsapp_message(
                from_number,
                "Sorry, I couldn't find any requirements in your message. Please try again.",
            )
            return

        try:
            await search_service.search_listings(
                db, requirement.id, pipeline_run_id=pipeline_run.id
            )
            pipeline_run.search_completed_at = datetime.now(timezone.utc)
            pipeline_run.current_stage = PipelineStage.RANKING.value
            db.commit()
        except Exception as exc:
            logger.exception("WhatsApp pipeline failed at search")
            pipeline_run.status = PipelineStatus.FAILED.value
            pipeline_run.error_message = str(exc)
            db.commit()
            send_whatsapp_message(
                from_number,
                f"Sorry, the property search failed. Error: {exc}. Please try again.",
            )
            return

        # --- Ranking ---
        listings = (
            db.query(Listing)
            .filter(Listing.pipeline_run_id == pipeline_run.id)
            .all()
        )
        if not listings:
            pipeline_run.status = PipelineStatus.FAILED.value
            pipeline_run.error_message = "No listings found to rank"
            db.commit()
            send_whatsapp_message(
                from_number,
                "I searched but couldn't find any matching properties. "
                "Try sending a new message with different criteria.",
            )
            return

        try:
            await ranking_service.rank_results(
                db=db,
                pipeline_run_id=pipeline_run.id,
                requirement=requirement,
                listings=listings,
                llm=llm,
            )
            pipeline_run.ranking_completed_at = datetime.now(timezone.utc)
            pipeline_run.current_stage = PipelineStage.REVIEW.value
            pipeline_run.status = PipelineStatus.COMPLETED.value
            db.commit()
        except Exception as exc:
            logger.exception("WhatsApp pipeline failed at ranking")
            pipeline_run.status = PipelineStatus.FAILED.value
            pipeline_run.error_message = str(exc)
            db.commit()
            send_whatsapp_message(
                from_number,
                f"Sorry, ranking failed. Error: {exc}. Please try again.",
            )
            return

        # --- Send results back via WhatsApp ---
        send_pipeline_results(db, pipeline_run.id, from_number)

        # Clean up the conversation so the user can start a new search
        clear_conversation(from_number)

        logger.info(
            "WhatsApp pipeline %d completed successfully for %s",
            pipeline_run.id,
            from_number,
        )

    except Exception:
        logger.exception(
            "Unexpected error in WhatsApp background pipeline %d", pipeline_run_id
        )
        send_whatsapp_message(
            from_number,
            "An unexpected error occurred while processing your request. Please try again.",
        )
    finally:
        db.close()


def schedule_pipeline(pipeline_run_id: int, from_number: str) -> None:
    """Schedule the async pipeline to run in the current event loop.

    Called from the webhook handler after the TwiML response is prepared.
    """
    loop = asyncio.get_event_loop()
    loop.create_task(run_pipeline_async(pipeline_run_id, from_number))


def get_pipeline_status_message(db: Session, from_number: str) -> str | None:
    """Return a human-readable status for the caller's active pipeline, or None."""
    run_id = _active_conversations.get(from_number)
    if run_id is None:
        return None
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        return None
    return (
        f"Pipeline #{run.id} -- stage: {run.current_stage}, "
        f"status: {run.status}"
    )


# ---------------------------------------------------------------------------
# Outbound: send WhatsApp message via Twilio REST API
# ---------------------------------------------------------------------------


def send_whatsapp_message(to_number: str, body: str) -> dict:
    """Send a WhatsApp message.  Falls back to simulation when creds are absent."""
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.warning("Twilio credentials not configured -- simulating WhatsApp send")
        return {
            "status": "simulated",
            "to": to_number,
            "body": body,
        }

    client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
    # Ensure the 'whatsapp:' prefix
    to_wa = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
    from_wa = settings.twilio_whatsapp_number

    message = client.messages.create(
        body=body,
        from_=from_wa,
        to=to_wa,
    )
    logger.info("WhatsApp message sent sid=%s to=%s", message.sid, to_wa)
    return {
        "status": "sent",
        "sid": message.sid,
        "to": to_wa,
    }


def send_pipeline_results(db: Session, pipeline_run_id: int, to_number: str) -> dict:
    """Build a summary of ranked results and send via WhatsApp."""
    rankings: list[RankedResult] = (
        db.query(RankedResult)
        .filter(RankedResult.pipeline_run_id == pipeline_run_id)
        .order_by(RankedResult.rank_position.asc())
        .limit(5)
        .all()
    )

    if not rankings:
        body = (
            f"Pipeline #{pipeline_run_id} completed but no ranked listings were found. "
            "Try sending a new message with different requirements."
        )
        return send_whatsapp_message(to_number, body)

    lines = [f"Here are your top {len(rankings)} property matches:\n"]
    for rr in rankings:
        listing: Listing = rr.listing
        price = f"${listing.price:,.0f}" if listing.price else "Price N/A"
        details: list[str] = []
        if listing.bedrooms is not None:
            details.append(f"{listing.bedrooms}bd")
        if listing.bathrooms is not None:
            details.append(f"{listing.bathrooms}ba")
        if listing.sqft is not None:
            details.append(f"{listing.sqft:,}sqft")
        score_pct = round((rr.overall_score or 0) * 100)
        line = (
            f"{rr.rank_position}. {listing.address or 'N/A'}\n"
            f"   {price} | {' | '.join(details)}\n"
            f"   Match: {score_pct}%"
        )
        if listing.zillow_url:
            line += f"\n   {listing.zillow_url}"
        lines.append(line)

    lines.append("\nReply with a new message to start another search!")
    body = "\n".join(lines)
    return send_whatsapp_message(to_number, body)


def clear_conversation(from_number: str) -> bool:
    """Remove a sender from the active-conversations map.  Returns True if removed."""
    return _active_conversations.pop(from_number, None) is not None

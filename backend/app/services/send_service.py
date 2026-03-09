"""Send workflow: email approved listings to client via Resend."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import resend

from app.config import settings
from app.models.email_send import EmailSend
from app.models.pipeline_run import PipelineRun
from app.models.ranking import RankedResult
from app.models.requirement import ExtractedRequirement

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

AVAILABLE_TEMPLATES = [
    {
        "key": "professional",
        "label": "Professional",
        "description": "Formal tone with structured layout. Suitable for new or corporate clients.",
    },
    {
        "key": "casual",
        "label": "Casual",
        "description": "Friendly, conversational tone. Great for established client relationships.",
    },
    {
        "key": "advisory",
        "label": "Advisory",
        "description": "Expert consultative tone with market insights framing.",
    },
]

DEFAULT_SUBJECTS: dict[str, str] = {
    "professional": "Your Curated Property Listings ({listing_count} properties)",
    "casual": "Found some great places for you! ({listing_count} picks)",
    "advisory": "Market-Informed Property Recommendations ({listing_count} properties)",
}

DEFAULT_BODIES: dict[str, str] = {
    "professional": (
        "Following our recent conversation, I have identified {listing_count}"
        " {word} that closely align with your stated requirements."
        " Please find the details below."
    ),
    "casual": (
        "I just wrapped up a fresh search and found {listing_count} {word}"
        " that I think you're really going to like. Take a look!"
    ),
    "advisory": (
        "After a thorough review of the current inventory, I've selected"
        " {listing_count} {word} that offer the best combination of value"
        " and fit for your criteria."
    ),
}


def get_email_templates() -> list[dict]:
    """Return the list of available email templates with keys and descriptions."""
    return AVAILABLE_TEMPLATES


def _load_template(tone: str) -> str:
    """Load an HTML template file by tone key."""
    template_path = TEMPLATES_DIR / f"{tone}.html"
    if not template_path.exists():
        logger.warning("Template %s not found, falling back to professional", tone)
        template_path = TEMPLATES_DIR / "professional.html"
    return template_path.read_text(encoding="utf-8")


def _get_approved_rankings(db: Session, pipeline_run_id: int) -> list[RankedResult]:
    return (
        db.query(RankedResult)
        .filter(
            RankedResult.pipeline_run_id == pipeline_run_id,
            RankedResult.approved_by_harry == True,  # noqa: E712
        )
        .order_by(RankedResult.rank_position.asc())
        .all()
    )


def _build_listing_html(rr: RankedResult) -> str:
    listing = rr.listing
    price = f"${listing.price:,.0f}" if listing.price else "Price N/A"
    details = []
    if listing.bedrooms is not None:
        details.append(f"{listing.bedrooms} bed")
    if listing.bathrooms is not None:
        details.append(f"{listing.bathrooms} bath")
    if listing.sqft is not None:
        details.append(f"{listing.sqft:,} sqft")
    details_str = " &middot; ".join(details) if details else ""

    score_pct = round((rr.overall_score or 0) * 100)

    zillow_link = ""
    if listing.zillow_url:
        zillow_link = f' &middot; <a href="{listing.zillow_url}" style="color:#ff5e25;">View on Zillow</a>'

    desc_html = ""
    if listing.description and len(listing.description) > 50:
        truncated = listing.description[:200] + (
            "..." if len(listing.description) > 200 else ""
        )
        desc_html = (
            f'<div style="color:#888;font-size:13px;margin-top:6px;">{truncated}</div>'
        )

    return f"""
    <tr>
      <td style="padding:16px 20px;border-bottom:1px solid #e5e5e5;">
        <div style="font-size:16px;font-weight:bold;margin-bottom:4px;">{listing.address or "Address N/A"}</div>
        <div style="color:#666;font-size:14px;">{price} &middot; {details_str}</div>
        {desc_html}
        <div style="margin-top:8px;font-size:13px;">
          <span style="color:#4f9664;font-weight:bold;">Match: {score_pct}%</span>
          {zillow_link}
        </div>
      </td>
    </tr>"""


def _build_email_html(
    rankings: list[RankedResult],
    client_name: str | None,
    tone: str = "professional",
    subject_override: str | None = None,
    body_override: str | None = None,
    agent_name: str = "Harry",
    locations: str | None = None,
    agent_phone: str = "",
    agent_email: str = "",
    brokerage_name: str = "",
    brokerage_logo_url: str = "",
) -> tuple[str, str]:
    """Build the full email HTML and subject line.

    Returns (html_body, subject_line).
    """
    count = len(rankings)
    word = "properties" if count != 1 else "property"
    display_name = client_name or "there"
    display_locations = locations or "your preferred areas"

    # Resolve subject
    subject_line = subject_override or DEFAULT_SUBJECTS.get(
        tone, DEFAULT_SUBJECTS["professional"]
    ).format(listing_count=count, word=word)

    # Resolve body text
    body_text = body_override or DEFAULT_BODIES.get(
        tone, DEFAULT_BODIES["professional"]
    ).format(listing_count=count, word=word)

    listing_rows = "\n".join(_build_listing_html(rr) for rr in rankings)

    # Build signature contact details (only include lines with values)
    sig_phone = f"Phone: {agent_phone}<br>" if agent_phone else ""
    sig_email = f"Email: {agent_email}<br>" if agent_email else ""
    sig_brokerage = brokerage_name if brokerage_name else ""

    # Build footer branding
    footer_logo = (
        f'<br><img src="{brokerage_logo_url}" alt="{brokerage_name}" '
        f'style="max-height:40px;margin-top:8px;">'
        if brokerage_logo_url
        else ""
    )

    template = _load_template(tone)
    html = template.format(
        client_name=display_name,
        agent_name=agent_name,
        listing_count=count,
        listing_rows=listing_rows,
        subject_line=subject_line,
        custom_body=body_text,
        locations=display_locations,
        agent_phone=sig_phone,
        agent_email=sig_email,
        brokerage_name=sig_brokerage,
        brokerage_logo_url=footer_logo,
    )

    return html, subject_line


def _get_requirement_for_rankings(
    db: Session, rankings: list[RankedResult]
) -> ExtractedRequirement | None:
    """Look up the requirement associated with the first ranked result."""
    if not rankings:
        return None
    first_rr = rankings[0]
    return (
        db.query(ExtractedRequirement)
        .filter(ExtractedRequirement.id == first_rr.requirement_id)
        .first()
    )


def preview_email(
    db: Session,
    pipeline_run_id: int,
    tone: str = "professional",
    subject: str | None = None,
    body: str | None = None,
    agent_name: str = "Harry",
    agent_phone: str = "",
    agent_email: str = "",
    brokerage_name: str = "",
) -> dict:
    """Generate a full HTML preview of the email without sending."""
    rankings = _get_approved_rankings(db, pipeline_run_id)
    if not rankings:
        return {
            "html": "",
            "subject": "",
            "error": "No approved listings to preview.",
        }

    requirement = _get_requirement_for_rankings(db, rankings)
    client_name = requirement.client_name if requirement else None
    locations = requirement.locations if requirement else None

    html_body, subject_line = _build_email_html(
        rankings,
        client_name,
        tone=tone,
        subject_override=subject,
        body_override=body,
        agent_name=agent_name,
        locations=locations,
        agent_phone=agent_phone,
        agent_email=agent_email,
        brokerage_name=brokerage_name,
    )

    return {"html": html_body, "subject": subject_line}


def send_email(
    db: Session,
    pipeline_run_id: int,
    recipient_email: str,
    tone: str = "professional",
    subject_override: str | None = None,
    body_override: str | None = None,
    agent_name: str = "Harry",
    agent_phone: str = "",
    agent_email: str = "",
    brokerage_name: str = "",
) -> dict:
    """Send approved listings via Resend and update DB records."""
    rankings = _get_approved_rankings(db, pipeline_run_id)
    if not rankings:
        return {
            "pipeline_run_id": pipeline_run_id,
            "status": "error",
            "message": "No approved listings to send.",
        }

    requirement = _get_requirement_for_rankings(db, rankings)
    client_name = requirement.client_name if requirement else None
    locations = requirement.locations if requirement else None

    html_body, subject_line = _build_email_html(
        rankings,
        client_name,
        tone=tone,
        subject_override=subject_override,
        body_override=body_override,
        agent_name=agent_name,
        locations=locations,
        agent_phone=agent_phone,
        agent_email=agent_email,
        brokerage_name=brokerage_name,
    )
    count = len(rankings)

    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured — simulating send")
    else:
        resend.api_key = settings.resend_api_key
        try:
            resend.Emails.send(
                {
                    "from": settings.email_from,
                    "to": [recipient_email],
                    "subject": subject_line,
                    "html": html_body,
                }
            )
            logger.info(
                "Email sent to %s with %d listings for pipeline_run_id=%d",
                recipient_email,
                count,
                pipeline_run_id,
            )
        except Exception:
            logger.exception("Resend email failed for %s", recipient_email)
            return {
                "pipeline_run_id": pipeline_run_id,
                "status": "error",
                "message": "Failed to send email. Check Resend API key.",
            }

    # Mark ranked results as sent
    for rr in rankings:
        rr.sent_to_client = True

    # Update pipeline run
    pipeline_run = (
        db.query(PipelineRun).filter(PipelineRun.id == pipeline_run_id).first()
    )
    if pipeline_run:
        pipeline_run.send_completed_at = datetime.now(UTC)
        pipeline_run.current_stage = "send"

    # Record the send in email_sends tracking table
    email_send = EmailSend(
        pipeline_run_id=pipeline_run_id,
        recipient_email=recipient_email,
        tone=tone,
        subject=subject_line,
        status="sent",
    )
    db.add(email_send)

    db.commit()

    return {
        "pipeline_run_id": pipeline_run_id,
        "status": "sent",
        "recipient": recipient_email,
        "listings_sent": count,
        "message": f"Successfully sent {count} listings to {recipient_email}."
        if settings.resend_api_key
        else f"Resend not configured. {count} listings marked as sent (simulated).",
    }


def get_send_status(db: Session, pipeline_run_id: int) -> dict:
    """Check whether listings have been sent for a pipeline run."""
    rankings = _get_approved_rankings(db, pipeline_run_id)
    sent_count = sum(1 for rr in rankings if rr.sent_to_client)
    total = len(rankings)

    pipeline_run = (
        db.query(PipelineRun).filter(PipelineRun.id == pipeline_run_id).first()
    )
    sent_at = pipeline_run.send_completed_at if pipeline_run else None

    return {
        "pipeline_run_id": pipeline_run_id,
        "status": "sent" if sent_count > 0 else "not_sent",
        "sent_count": sent_count,
        "approved_count": total,
        "sent_at": sent_at.isoformat() if sent_at else None,
    }


def get_email_history(db: Session, pipeline_run_id: int) -> list[EmailSend]:
    """Return all email send records for a pipeline run."""
    return (
        db.query(EmailSend)
        .filter(EmailSend.pipeline_run_id == pipeline_run_id)
        .order_by(EmailSend.sent_at.desc())
        .all()
    )


VALID_FEEDBACK_VALUES = {
    "interested",
    "not_interested",
    "need_more_info",
    "scheduled_viewing",
}


def record_feedback(db: Session, send_id: int, feedback: str) -> EmailSend | None:
    """Record client feedback on a sent email."""
    email_send = db.query(EmailSend).filter(EmailSend.id == send_id).first()
    if not email_send:
        return None

    email_send.client_feedback = feedback
    email_send.client_feedback_at = datetime.now(UTC)
    email_send.status = "responded"
    db.commit()
    db.refresh(email_send)
    return email_send

"""Send workflow: email approved listings to client via Resend."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import resend
from sqlalchemy.orm import Session

from app.config import settings
from app.models.pipeline_run import PipelineRun
from app.models.ranking import RankedResult
from app.models.requirement import ExtractedRequirement

logger = logging.getLogger(__name__)


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

    source_link = ""
    if listing.listing_url:
        source_label = listing.source.title() if listing.source else "Listing"
        source_link = f' &middot; <a href="{listing.listing_url}" style="color:#ff5e25;">View on {source_label}</a>'

    desc_html = ""
    if listing.description and len(listing.description) > 50:
        truncated = listing.description[:200] + ("..." if len(listing.description) > 200 else "")
        desc_html = f'<div style="color:#888;font-size:13px;margin-top:6px;">{truncated}</div>'

    return f"""
    <tr>
      <td style="padding:16px 20px;border-bottom:1px solid #e5e5e5;">
        <div style="font-size:16px;font-weight:bold;margin-bottom:4px;">{listing.address or "Address N/A"}</div>
        <div style="color:#666;font-size:14px;">{price} &middot; {details_str}</div>
        {desc_html}
        <div style="margin-top:8px;font-size:13px;">
          <span style="color:#4f9664;font-weight:bold;">Match: {score_pct}%</span>
          {source_link}
        </div>
      </td>
    </tr>"""


def _build_email_html(
    rankings: list[RankedResult],
    client_name: str | None,
) -> str:
    greeting = f"Hi {client_name}," if client_name else "Hi,"
    listing_rows = "\n".join(_build_listing_html(rr) for rr in rankings)
    count = len(rankings)
    word = "properties" if count != 1 else "property"

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#0d0d0d;">
  <div style="max-width:600px;margin:0 auto;padding:20px;">
    <div style="border-bottom:2px solid #0d0d0d;padding-bottom:12px;margin-bottom:24px;">
      <h1 style="margin:0;font-size:20px;text-transform:uppercase;letter-spacing:1px;">
        Curated Property Listings
      </h1>
    </div>

    <p style="font-size:14px;line-height:1.6;">{greeting}</p>
    <p style="font-size:14px;line-height:1.6;">
      Based on our conversation, I've found {count} {word} that match your requirements.
      Here are my top picks for you:
    </p>

    <table style="width:100%;border-collapse:collapse;margin:24px 0;border:1px solid #e5e5e5;">
      {listing_rows}
    </table>

    <p style="font-size:14px;line-height:1.6;">
      Let me know if any of these catch your eye, or if you'd like to schedule viewings.
      Happy to adjust the search if your priorities have changed.
    </p>

    <p style="font-size:14px;line-height:1.6;margin-top:24px;">
      Best regards,<br>
      <strong>Harry</strong>
    </p>
  </div>
</body>
</html>"""


def send_email(
    db: Session,
    pipeline_run_id: int,
    recipient_email: str,
) -> dict:
    """Send approved listings via Resend and update DB records."""
    rankings = _get_approved_rankings(db, pipeline_run_id)
    if not rankings:
        return {
            "pipeline_run_id": pipeline_run_id,
            "status": "error",
            "message": "No approved listings to send.",
        }

    # Look up client name from the requirement
    first_rr = rankings[0]
    requirement = (
        db.query(ExtractedRequirement)
        .filter(ExtractedRequirement.id == first_rr.requirement_id)
        .first()
    )
    client_name = requirement.client_name if requirement else None

    html_body = _build_email_html(rankings, client_name)
    count = len(rankings)

    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured — simulating send")
    else:
        resend.api_key = settings.resend_api_key
        try:
            resend.Emails.send({
                "from": settings.email_from,
                "to": [recipient_email],
                "subject": f"Your Curated Property Listings ({count} properties)",
                "html": html_body,
            })
            logger.info(
                "Email sent to %s with %d listings for pipeline_run_id=%d",
                recipient_email, count, pipeline_run_id,
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
        pipeline_run.send_completed_at = datetime.now(timezone.utc)
        pipeline_run.current_stage = "send"

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

"""Tests for the email template system."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.send_service import (
    AVAILABLE_TEMPLATES,
    DEFAULT_BODIES,
    DEFAULT_SUBJECTS,
    TEMPLATES_DIR,
    VALID_FEEDBACK_VALUES,
    _build_email_html,
    _load_template,
    get_email_templates,
    preview_email,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_ranking(
    address: str = "123 Main St",
    price: float = 500_000,
    bedrooms: int = 3,
    bathrooms: int = 2,
    sqft: int = 1800,
    overall_score: float = 0.85,
    zillow_url: str | None = "https://zillow.com/123",
    description: str = "A wonderful property with spacious rooms and a great backyard for the family.",
    requirement_id: int = 1,
) -> MagicMock:
    listing = MagicMock()
    listing.address = address
    listing.price = price
    listing.bedrooms = bedrooms
    listing.bathrooms = bathrooms
    listing.sqft = sqft
    listing.zillow_url = zillow_url
    listing.description = description

    rr = MagicMock()
    rr.listing = listing
    rr.overall_score = overall_score
    rr.requirement_id = requirement_id
    return rr


# ---------------------------------------------------------------------------
# Template file existence
# ---------------------------------------------------------------------------

class TestTemplateFiles:
    def test_templates_dir_exists(self):
        assert TEMPLATES_DIR.is_dir()

    @pytest.mark.parametrize("tone", ["professional", "casual", "advisory"])
    def test_template_file_exists(self, tone: str):
        path = TEMPLATES_DIR / f"{tone}.html"
        assert path.exists(), f"{tone}.html not found"

    @pytest.mark.parametrize("tone", ["professional", "casual", "advisory"])
    def test_template_has_required_placeholders(self, tone: str):
        content = (TEMPLATES_DIR / f"{tone}.html").read_text()
        for placeholder in [
            "{client_name}",
            "{agent_name}",
            "{listing_rows}",
            "{subject_line}",
            "{custom_body}",
        ]:
            assert placeholder in content, f"{placeholder} missing in {tone}.html"

    def test_advisory_has_locations_placeholder(self):
        content = (TEMPLATES_DIR / "advisory.html").read_text()
        assert "{locations}" in content

    @pytest.mark.parametrize("tone", ["professional", "casual", "advisory"])
    def test_template_has_branding_placeholders(self, tone: str):
        content = (TEMPLATES_DIR / f"{tone}.html").read_text()
        for placeholder in [
            "{agent_phone}",
            "{agent_email}",
            "{brokerage_name}",
            "{brokerage_logo_url}",
        ]:
            assert placeholder in content, f"{placeholder} missing in {tone}.html"


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

class TestLoadTemplate:
    def test_load_known_tone(self):
        html = _load_template("professional")
        assert "{client_name}" in html

    def test_fallback_for_unknown_tone(self):
        html = _load_template("nonexistent_tone")
        # Falls back to professional
        assert "{client_name}" in html


# ---------------------------------------------------------------------------
# get_email_templates
# ---------------------------------------------------------------------------

class TestGetEmailTemplates:
    def test_returns_list(self):
        result = get_email_templates()
        assert isinstance(result, list)
        assert len(result) == 3

    def test_template_keys(self):
        keys = {t["key"] for t in get_email_templates()}
        assert keys == {"professional", "casual", "advisory"}

    def test_template_has_label_and_description(self):
        for t in get_email_templates():
            assert "label" in t
            assert "description" in t
            assert len(t["description"]) > 0


# ---------------------------------------------------------------------------
# _build_email_html
# ---------------------------------------------------------------------------

class TestBuildEmailHtml:
    def setup_method(self):
        self.rankings = [
            _make_mock_ranking(address="10 Downing St", price=750_000),
            _make_mock_ranking(address="221B Baker St", price=600_000),
        ]

    @pytest.mark.parametrize("tone", ["professional", "casual", "advisory"])
    def test_renders_without_error(self, tone: str):
        html, subject = _build_email_html(
            self.rankings, client_name="Alice", tone=tone
        )
        assert isinstance(html, str)
        assert len(html) > 100
        assert isinstance(subject, str)

    def test_professional_greeting(self):
        html, _ = _build_email_html(
            self.rankings, client_name="Bob", tone="professional"
        )
        assert "Dear Bob" in html

    def test_casual_greeting(self):
        html, _ = _build_email_html(
            self.rankings, client_name="Bob", tone="casual"
        )
        assert "Hey Bob!" in html

    def test_advisory_greeting(self):
        html, _ = _build_email_html(
            self.rankings, client_name="Bob", tone="advisory"
        )
        assert "Hi Bob" in html

    def test_professional_closing(self):
        html, _ = _build_email_html(
            self.rankings, client_name="X", tone="professional", agent_name="Jane"
        )
        assert "Kind regards" in html
        assert "Jane" in html

    def test_casual_closing(self):
        html, _ = _build_email_html(
            self.rankings, client_name="X", tone="casual", agent_name="Jane"
        )
        assert "Cheers" in html
        assert "Jane" in html

    def test_advisory_closing(self):
        html, _ = _build_email_html(
            self.rankings, client_name="X", tone="advisory", agent_name="Jane"
        )
        assert "Best," in html
        assert "Jane" in html

    def test_listing_rows_included(self):
        html, _ = _build_email_html(
            self.rankings, client_name="X", tone="professional"
        )
        assert "10 Downing St" in html
        assert "221B Baker St" in html
        assert "$750,000" in html

    def test_subject_override(self):
        _, subject = _build_email_html(
            self.rankings,
            client_name="X",
            tone="professional",
            subject_override="Custom Subject Here",
        )
        assert subject == "Custom Subject Here"

    def test_body_override(self):
        html, _ = _build_email_html(
            self.rankings,
            client_name="X",
            tone="professional",
            body_override="This is a custom body paragraph.",
        )
        assert "This is a custom body paragraph." in html

    def test_default_subject_contains_count(self):
        _, subject = _build_email_html(
            self.rankings, client_name="X", tone="professional"
        )
        assert "2" in subject

    def test_no_client_name_uses_there(self):
        html, _ = _build_email_html(
            self.rankings, client_name=None, tone="casual"
        )
        assert "Hey there!" in html

    def test_advisory_includes_locations(self):
        html, _ = _build_email_html(
            self.rankings,
            client_name="X",
            tone="advisory",
            locations="Downtown, Midtown",
        )
        assert "Downtown, Midtown" in html

    def test_branding_phone_included(self):
        html, _ = _build_email_html(
            self.rankings,
            client_name="X",
            tone="professional",
            agent_phone="(555) 123-4567",
        )
        assert "(555) 123-4567" in html

    def test_branding_email_included(self):
        html, _ = _build_email_html(
            self.rankings,
            client_name="X",
            tone="casual",
            agent_email="agent@realty.com",
        )
        assert "agent@realty.com" in html

    def test_branding_brokerage_included(self):
        html, _ = _build_email_html(
            self.rankings,
            client_name="X",
            tone="advisory",
            brokerage_name="Sunrise Realty",
        )
        assert "Sunrise Realty" in html

    def test_branding_empty_by_default(self):
        """When no branding is provided, signature area should be clean."""
        html, _ = _build_email_html(
            self.rankings,
            client_name="X",
            tone="professional",
        )
        # Should not contain literal placeholder text
        assert "{agent_phone}" not in html
        assert "{agent_email}" not in html
        assert "{brokerage_name}" not in html

    def test_no_robotic_language(self):
        """Ensure templates don't contain known robotic phrases."""
        robotic_phrases = [
            "I am writing to inform you",
            "Please find attached",
            "Please do not hesitate to reach out",
        ]
        for tone in ["professional", "casual", "advisory"]:
            html, _ = _build_email_html(
                self.rankings, client_name="X", tone=tone
            )
            for phrase in robotic_phrases:
                assert phrase not in html, f'Robotic phrase "{phrase}" found in {tone}'


# ---------------------------------------------------------------------------
# Email send tracking
# ---------------------------------------------------------------------------

class TestEmailSendTracking:
    def test_valid_feedback_values(self):
        expected = {"interested", "not_interested", "need_more_info", "scheduled_viewing"}
        assert VALID_FEEDBACK_VALUES == expected


# ---------------------------------------------------------------------------
# preview_email (integration-style with mocked DB)
# ---------------------------------------------------------------------------

class TestPreviewEmail:
    def _setup_db_mock(self):
        rankings = [
            _make_mock_ranking(address="42 Wallaby Way"),
        ]
        requirement = MagicMock()
        requirement.client_name = "Nemo"
        requirement.locations = "Sydney"

        db = MagicMock()
        query_mock = MagicMock()
        # Chain: db.query().filter().order_by().all() -> rankings
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = rankings
        # Chain: db.query().filter().first() -> requirement
        db.query.return_value.filter.return_value.first.return_value = requirement

        return db

    def test_preview_returns_html_and_subject(self):
        db = self._setup_db_mock()
        result = preview_email(db, pipeline_run_id=1, tone="professional")
        assert "html" in result
        assert "subject" in result
        assert len(result["html"]) > 0
        assert "42 Wallaby Way" in result["html"]

    def test_preview_with_no_approved(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        result = preview_email(db, pipeline_run_id=1)
        assert result["html"] == ""
        assert "error" in result

    def test_preview_respects_tone(self):
        db = self._setup_db_mock()
        result = preview_email(db, pipeline_run_id=1, tone="casual")
        assert "Hey Nemo!" in result["html"]

    def test_preview_respects_agent_name(self):
        db = self._setup_db_mock()
        result = preview_email(
            db, pipeline_run_id=1, tone="professional", agent_name="Marlin"
        )
        assert "Marlin" in result["html"]

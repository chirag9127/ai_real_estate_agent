from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Test: get_auth_url() generation
# ---------------------------------------------------------------------------

@patch("app.services.google_docs_service.Flow")
def test_get_auth_url(mock_flow_cls):
    """get_auth_url should build a Google OAuth URL via Flow."""
    from app.services.google_docs_service import get_auth_url

    mock_flow = MagicMock()
    mock_flow.authorization_url.return_value = (
        "https://accounts.google.com/o/oauth2/auth?client_id=test",
        "state123",
    )
    mock_flow_cls.from_client_config.return_value = mock_flow

    url = get_auth_url()

    mock_flow_cls.from_client_config.assert_called_once()
    mock_flow.authorization_url.assert_called_once()
    assert url.startswith("https://accounts.google.com/")


# ---------------------------------------------------------------------------
# Test: fetch_document_text() with mocked Docs API response
# ---------------------------------------------------------------------------

@patch("app.services.google_docs_service.build")
@patch("app.services.google_docs_service._build_credentials")
def test_fetch_document_text(mock_creds, mock_build):
    """fetch_document_text should extract text from structural elements."""
    from app.services.google_docs_service import fetch_document_text

    fake_doc = {
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Hello "}},
                            {"textRun": {"content": "World\n"}},
                        ]
                    }
                },
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Second paragraph\n"}},
                        ]
                    }
                },
            ]
        }
    }

    mock_service = MagicMock()
    mock_service.documents.return_value.get.return_value.execute.return_value = fake_doc
    mock_build.return_value = mock_service
    mock_creds.return_value = MagicMock()

    text = fetch_document_text({"token": "fake"}, "doc123")

    assert "Hello World" in text
    assert "Second paragraph" in text
    mock_build.assert_called_once_with("docs", "v1", credentials=mock_creds.return_value)


@patch("app.services.google_docs_service.build")
@patch("app.services.google_docs_service._build_credentials")
def test_fetch_document_text_with_table(mock_creds, mock_build):
    """fetch_document_text should handle table elements."""
    from app.services.google_docs_service import fetch_document_text

    fake_doc = {
        "body": {
            "content": [
                {
                    "table": {
                        "tableRows": [
                            {
                                "tableCells": [
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {"textRun": {"content": "Cell 1"}},
                                                    ]
                                                }
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }
    }

    mock_service = MagicMock()
    mock_service.documents.return_value.get.return_value.execute.return_value = fake_doc
    mock_build.return_value = mock_service
    mock_creds.return_value = MagicMock()

    text = fetch_document_text({"token": "fake"}, "doc456")
    assert "Cell 1" in text


# ---------------------------------------------------------------------------
# Test: callback router endpoint with mocked exchange
# ---------------------------------------------------------------------------

@patch("app.routers.google_auth.google_docs_service.exchange_code")
def test_callback_endpoint(mock_exchange):
    """POST /api/v1/google/callback should exchange code and return creds."""
    from app.main import app

    mock_exchange.return_value = {
        "token": "access-token-123",
        "refresh_token": "refresh-token-456",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "cid",
        "client_secret": "csecret",
        "scopes": ["https://www.googleapis.com/auth/documents.readonly"],
    }

    client = TestClient(app)
    resp = client.post("/api/v1/google/callback", json={"code": "auth-code-xyz"})

    assert resp.status_code == 200
    body = resp.json()
    assert "credentials" in body
    assert body["credentials"]["token"] == "access-token-123"
    mock_exchange.assert_called_once_with("auth-code-xyz")


# ---------------------------------------------------------------------------
# Test: list_recent_docs with mocked Drive API
# ---------------------------------------------------------------------------

@patch("app.services.google_docs_service.build")
@patch("app.services.google_docs_service._build_credentials")
def test_list_recent_docs(mock_creds, mock_build):
    """list_recent_docs should return formatted doc list from Drive API."""
    from app.services.google_docs_service import list_recent_docs

    fake_files = {
        "files": [
            {"id": "abc1", "name": "Meeting Notes", "modifiedTime": "2024-01-15T10:00:00Z"},
            {"id": "abc2", "name": "Client Call", "modifiedTime": "2024-01-14T09:00:00Z"},
        ]
    }

    mock_service = MagicMock()
    mock_service.files.return_value.list.return_value.execute.return_value = fake_files
    mock_build.return_value = mock_service
    mock_creds.return_value = MagicMock()

    docs = list_recent_docs({"token": "fake"}, limit=10)

    assert len(docs) == 2
    assert docs[0]["id"] == "abc1"
    assert docs[0]["name"] == "Meeting Notes"
    assert docs[1]["id"] == "abc2"

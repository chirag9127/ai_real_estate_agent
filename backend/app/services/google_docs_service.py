from __future__ import annotations

import logging

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import settings

logger = logging.getLogger(__name__)


def _build_client_config() -> dict:
    """Build the OAuth client config dict expected by google_auth_oauthlib."""
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def get_auth_url() -> str:
    """Build Google OAuth 2.0 authorization URL."""
    scopes = settings.google_scopes.split()
    flow = Flow.from_client_config(
        _build_client_config(),
        scopes=scopes,
        redirect_uri=settings.google_redirect_uri,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def exchange_code(code: str) -> dict:
    """Exchange authorization code for credentials. Return credentials as a dict."""
    scopes = settings.google_scopes.split()
    flow = Flow.from_client_config(
        _build_client_config(),
        scopes=scopes,
        redirect_uri=settings.google_redirect_uri,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else scopes,
    }


def _build_credentials(credentials: dict) -> Credentials:
    """Reconstruct a google Credentials object from a dict."""
    return Credentials(
        token=credentials["token"],
        refresh_token=credentials.get("refresh_token"),
        token_uri=credentials.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=credentials.get("client_id", settings.google_client_id),
        client_secret=credentials.get("client_secret", settings.google_client_secret),
        scopes=credentials.get("scopes"),
    )


def _read_structural_elements(elements: list[dict]) -> str:
    """Recursively extract text from Google Docs structural elements."""
    text_parts: list[str] = []
    for element in elements:
        if "paragraph" in element:
            paragraph = element["paragraph"]
            for elem in paragraph.get("elements", []):
                text_run = elem.get("textRun")
                if text_run:
                    text_parts.append(text_run.get("content", ""))
        elif "table" in element:
            table = element["table"]
            for row in table.get("tableRows", []):
                for cell in row.get("tableCells", []):
                    text_parts.append(
                        _read_structural_elements(cell.get("content", []))
                    )
        elif "tableOfContents" in element:
            toc = element["tableOfContents"]
            text_parts.append(
                _read_structural_elements(toc.get("content", []))
            )
    return "".join(text_parts)


def fetch_document_text(credentials: dict, document_id: str) -> str:
    """Use Google Docs API to fetch document content as plain text."""
    creds = _build_credentials(credentials)
    service = build("docs", "v1", credentials=creds)
    doc = service.documents().get(documentId=document_id).execute()
    body = doc.get("body", {})
    content = body.get("content", [])
    return _read_structural_elements(content)


def list_recent_docs(credentials: dict, limit: int = 20) -> list[dict]:
    """Use Google Drive API to list recent Google Docs the user has access to."""
    creds = _build_credentials(credentials)
    service = build("drive", "v3", credentials=creds)
    results = (
        service.files()
        .list(
            q="mimeType='application/vnd.google-apps.document'",
            pageSize=limit,
            fields="files(id, name, modifiedTime)",
            orderBy="modifiedTime desc",
        )
        .execute()
    )
    files = results.get("files", [])
    return [
        {"id": f["id"], "name": f["name"], "modifiedTime": f["modifiedTime"]}
        for f in files
    ]

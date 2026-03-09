"""Unit tests for multi-format file parsing (DOCX, PDF, TXT)."""

from __future__ import annotations

import io
import os
import sys

import pytest

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.utils.file_handling import (  # noqa: E402
    _extract_text_from_docx,
    _extract_text_from_pdf,
    _extract_text_from_txt,
    read_upload_text,
    validate_file,
)


# ---------------------------------------------------------------------------
# Plain text extraction
# ---------------------------------------------------------------------------

class TestTxtExtraction:
    def test_basic_utf8(self):
        text = _extract_text_from_txt(b"Hello, world!")
        assert text == "Hello, world!"

    def test_multiline(self):
        content = b"line1\nline2\nline3"
        assert _extract_text_from_txt(content) == "line1\nline2\nline3"

    def test_unicode(self):
        content = "Héllo wörld".encode("utf-8")
        assert _extract_text_from_txt(content) == "Héllo wörld"


# ---------------------------------------------------------------------------
# DOCX extraction
# ---------------------------------------------------------------------------

class TestDocxExtraction:
    def _make_docx_bytes(self, paragraphs: list[str]) -> bytes:
        """Create an in-memory .docx file with the given paragraphs."""
        from docx import Document

        doc = Document()
        for p in paragraphs:
            doc.add_paragraph(p)
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def test_single_paragraph(self):
        content = self._make_docx_bytes(["Hello from DOCX"])
        text = _extract_text_from_docx(content)
        assert "Hello from DOCX" in text

    def test_multiple_paragraphs(self):
        content = self._make_docx_bytes(["First paragraph", "Second paragraph"])
        text = _extract_text_from_docx(content)
        assert "First paragraph" in text
        assert "Second paragraph" in text

    def test_empty_document(self):
        content = self._make_docx_bytes([])
        text = _extract_text_from_docx(content)
        assert text.strip() == ""


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

class TestPdfExtraction:
    def _make_pdf_bytes(self, text: str) -> bytes:
        """Create a minimal PDF with the given text.

        We manually construct valid PDF bytes so that PyPDF2's PdfReader
        can extract the text back out.
        """
        # A minimal but valid PDF 1.4 with a single page containing the text
        stream_content = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET"
        stream_length = len(stream_content)

        pdf = (
            "%PDF-1.4\n"
            "1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            "2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            "3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            "/Contents 4 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1"
            "/BaseFont/Helvetica>>>>>>>>endobj\n"
            f"4 0 obj<</Length {stream_length}>>stream\n"
            f"{stream_content}\n"
            "endstream endobj\n"
        )
        # Build xref
        xref_offset = len(pdf.encode("latin-1"))
        pdf += (
            "xref\n"
            "0 5\n"
            "0000000000 65535 f \n"
        )
        # Rough offsets - PdfReader is fairly tolerant for testing
        offsets = []
        encoded = pdf.encode("latin-1")
        # We'll recalculate properly
        raw = (
            b"%PDF-1.4\n"
        )
        parts = [
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n",
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n",
            (
                b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
                b"/Contents 4 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1"
                b"/BaseFont/Helvetica>>>>>>>>endobj\n"
            ),
            (
                f"4 0 obj<</Length {stream_length}>>stream\n"
                f"{stream_content}\n"
                "endstream endobj\n"
            ).encode("latin-1"),
        ]
        offsets = []
        pos = len(raw)
        for part in parts:
            offsets.append(pos)
            pos += len(part)

        body = raw + b"".join(parts)
        xref_pos = len(body)

        xref = "xref\n0 5\n"
        xref += "0000000000 65535 f \n"
        for off in offsets:
            xref += f"{off:010d} 00000 n \n"
        xref += (
            "trailer<</Size 5/Root 1 0 R>>\n"
            "startxref\n"
            f"{xref_pos}\n"
            "%%EOF"
        )

        return body + xref.encode("latin-1")

    def test_extract_text(self):
        pdf_bytes = self._make_pdf_bytes("Hello PDF World")
        text = _extract_text_from_pdf(pdf_bytes)
        assert "Hello PDF World" in text

    def test_empty_pdf(self):
        pdf_bytes = self._make_pdf_bytes("")
        text = _extract_text_from_pdf(pdf_bytes)
        # Should not raise; text may be empty
        assert isinstance(text, str)


# ---------------------------------------------------------------------------
# read_upload_text routing
# ---------------------------------------------------------------------------

class FakeUploadFile:
    """Minimal stand-in for FastAPI's UploadFile."""

    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


class TestReadUploadTextRouting:
    @pytest.mark.asyncio
    async def test_txt_routing(self):
        fake = FakeUploadFile("notes.txt", b"plain text")
        text = await read_upload_text(fake)
        assert text == "plain text"

    @pytest.mark.asyncio
    async def test_md_routing(self):
        fake = FakeUploadFile("notes.md", b"# Markdown")
        text = await read_upload_text(fake)
        assert text == "# Markdown"


# ---------------------------------------------------------------------------
# validate_file
# ---------------------------------------------------------------------------

class TestValidateFile:
    def test_allowed_extensions(self):
        for ext in [".txt", ".pdf", ".docx", ".doc"]:
            fake = FakeUploadFile(f"test{ext}", b"")
            validate_file(fake)  # Should not raise

    def test_disallowed_extension(self):
        fake = FakeUploadFile("test.exe", b"")
        with pytest.raises(ValueError, match="not allowed"):
            validate_file(fake)

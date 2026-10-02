"""
Unit tests for PDFService text extraction and scanned document detection using PyMuPDF.
"""

import pytest
import pymupdf
from app.services.pdf_service import PDFService


def create_sample_pdf_bytes(text: str = "Hello from NoteMate AI test suite.") -> bytes:
    """Helper to generate a clean PDF in memory."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_extract_text_from_valid_pdf():
    """Verify text is accurately extracted from a multi-line digital PDF."""
    sample_content = "Distributed Systems Lecture: Consensus Algorithms like Raft and Paxos."
    pdf_bytes = create_sample_pdf_bytes(sample_content)

    res = PDFService.extract_text_from_bytes(pdf_bytes, filename="lecture.pdf")
    assert res.page_count == 1
    assert sample_content in res.extracted_text
    assert res.is_scanned_or_empty is False
    assert res.char_count > 0


def test_extract_text_from_empty_bytes():
    """Verify handling of 0-byte invalid upload."""
    res = PDFService.extract_text_from_bytes(b"", filename="empty.pdf")
    assert res.is_scanned_or_empty is True
    assert res.extracted_text == ""
    assert "empty" in res.message.lower()


def test_scanned_or_image_only_pdf_detection():
    """Verify detection when PDF contains blank or scanned pages without text."""
    # Blank PDF page without text
    doc = pymupdf.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    res = PDFService.extract_text_from_bytes(pdf_bytes, filename="scanned.pdf")
    assert res.is_scanned_or_empty is True
    assert res.char_count == 0


def test_invalid_pdf_corrupted_data():
    """Verify ValueError is raised when corrupted non-PDF bytes are passed."""
    corrupted_data = b"This is not a PDF file header at all."
    with pytest.raises(ValueError) as excinfo:
        PDFService.extract_text_from_bytes(corrupted_data, filename="corrupt.pdf")
    assert "Could not open file" in str(excinfo.value)

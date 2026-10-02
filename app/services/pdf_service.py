"""
PDF Text Extraction Service using PyMuPDF for NoteMate AI.
Extracts text from multi-page PDFs with fallback detection for scanned/image-only documents.
"""

from typing import Dict, Any
import pymupdf
from app.models import PDFExtractResponse


class PDFService:
    @staticmethod
    def extract_text_from_bytes(file_bytes: bytes, filename: str = "document.pdf") -> PDFExtractResponse:
        """Extract text from PDF file bytes using PyMuPDF."""
        if not file_bytes:
            return PDFExtractResponse(
                filename=filename,
                page_count=0,
                char_count=0,
                extracted_text="",
                is_scanned_or_empty=True,
                message="Uploaded file is empty (0 bytes).",
            )

        try:
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Could not open file as valid PDF: {str(e)}")

        page_count = len(doc)
        pages_text = []

        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text").strip()
            if text:
                pages_text.append(f"--- Page {page_num + 1} ---\n{text}")

        doc.close()

        full_text = "\n\n".join(pages_text).strip()
        char_count = len(full_text)

        # Scanned document detection: if pages exist but almost no text was extracted
        is_scanned = (char_count < 20 and page_count > 0)

        message = None
        if is_scanned:
            message = (
                "The uploaded PDF appears to be a scanned image or contains no extractable text. "
                "NoteMate AI currently supports text-based PDFs. Please upload a digital PDF with selectable text."
            )
        elif char_count == 0:
            message = "No text could be found in the document."

        return PDFExtractResponse(
            filename=filename,
            page_count=page_count,
            char_count=char_count,
            extracted_text=full_text,
            is_scanned_or_empty=is_scanned or (char_count == 0),
            message=message,
        )


pdf_service = PDFService()

import io
import os
import logging
from pypdf import PdfReader
from docx import Document

logger = logging.getLogger(__name__)

class DocumentParser:
    """Helper service to extract text from PDF, DOCX, and TXT files."""

    @staticmethod
    def extract_text_from_file(file_storage) -> tuple[str, str | None]:
        """
        Extracts plain text from a Flask FileStorage object.
        Returns (extracted_text, error_message).
        """
        filename = file_storage.filename or ""
        ext = os.path.splitext(filename)[1].lower()

        if not filename or ext not in ['.pdf', '.docx', '.txt']:
            return "", "Unsupported file format. Please upload a PDF, DOCX, or TXT document."

        try:
            file_bytes = file_storage.read()
            
            if len(file_bytes) > 10 * 1024 * 1024:
                return "", "File size exceeds 10MB limit."

            text = ""

            if ext == '.pdf':
                reader = PdfReader(io.BytesIO(file_bytes))
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"

            elif ext == '.docx':
                doc = Document(io.BytesIO(file_bytes))
                for paragraph in doc.paragraphs:
                    if paragraph.text:
                        text += paragraph.text + "\n"

            elif ext == '.txt':
                text = file_bytes.decode('utf-8', errors='ignore')

            text = text.strip()

            if not text:
                return "", f"Could not extract readable text from '{filename}'. The file may be scanned or empty."

            return text, None

        except Exception as e:
            logger.error(f"Error parsing file '{filename}': {str(e)}")
            return "", f"Failed to read file content: {str(e)}"

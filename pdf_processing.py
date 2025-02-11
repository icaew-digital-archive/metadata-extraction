# pdf_processing.py
import pdfplumber
from config import log_message

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF using pdfplumber."""
    text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        extracted_text = "\n".join(text)
        log_message(f"Extracted {len(extracted_text)} characters from {pdf_path}")
        return extracted_text
    except Exception as e:
        log_message(f"Error extracting text from {pdf_path}: {e}")
        return ""
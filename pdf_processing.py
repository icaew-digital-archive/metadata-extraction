# pdf_processing.py
import pdfplumber
import pytesseract
from PIL import Image
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

def extract_text_from_first_page_image(pdf_path):
    """Extract text from the first page of a scanned PDF using OCR."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            image = pdf.pages[0].to_image().original
            ocr_text = pytesseract.image_to_string(image)
            log_message(f"Extracted {len(ocr_text)} characters from OCR on {pdf_path}")
            return ocr_text
    except Exception as e:
        log_message(f"Error extracting OCR text from {pdf_path}: {e}")
        return ""

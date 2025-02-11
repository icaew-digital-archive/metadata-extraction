import docx2txt
import textract
from config import log_message


def extract_text_from_doc(file_path):
    """Extract text from .docx and .doc files."""
    try:
        file_extension = file_path.lower().rsplit('.', 1)[-1]
        if file_extension == "docx":
            return docx2txt.process(file_path)
        elif file_extension == "doc":
            # Textract handles older .doc files
            return textract.process(file_path).decode("utf-8")
    except Exception as e:
        log_message(f"Error extracting text from {file_path}: {e}")
        return ""

    return ""  # Return empty string if extraction fails

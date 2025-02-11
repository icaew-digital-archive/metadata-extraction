import os
import subprocess
import docx2txt
import textract
from config import log_message


def convert_doc_to_docx(file_path):
    """Convert a .doc file to .docx using LibreOffice."""
    try:
        output_dir = os.path.dirname(file_path)
        subprocess.run(
            ["libreoffice", "--headless", "--convert-to",
                "docx", file_path, "--outdir", output_dir],
            check=True,
            capture_output=True
        )
        new_docx_path = file_path.rsplit(".", 1)[0] + ".docx"
        if os.path.exists(new_docx_path):
            log_message(
                f"✅ Successfully converted {file_path} to {new_docx_path}")
            return new_docx_path
        else:
            log_message(f"⚠ Conversion failed: {file_path}")
            return None
    except Exception as e:
        log_message(f"⚠ Error converting {file_path} to .docx: {e}")
        return None


def extract_text_from_doc(file_path):
    """Extract text from .docx and .doc files using multiple fallbacks."""
    converted_docx = None  # Track if a conversion was done

    try:
        file_extension = file_path.lower().rsplit('.', 1)[-1]

        if file_extension == "docx":
            return docx2txt.process(file_path)

        elif file_extension == "doc":
            # 🔹 First attempt with textract
            try:
                return textract.process(file_path).decode("utf-8")
            except Exception:
                pass  # Move to next fallback

            # 🔹 Second attempt with antiword (better for old .doc files)
            try:
                result = subprocess.run(
                    ["antiword", file_path], capture_output=True, text=True, check=True)
                if result.stdout.strip():
                    return result.stdout
            except Exception:
                pass  # Move to next fallback

            # 🔹 Third attempt: Convert .doc to .docx and extract text
            converted_docx = convert_doc_to_docx(file_path)
            if converted_docx:
                return docx2txt.process(converted_docx)

    except Exception:
        pass  # Catch any unexpected errors and return empty

    finally:
        # Cleanup: Delete the converted .docx file if it was created
        if converted_docx and os.path.exists(converted_docx):
            try:
                os.remove(converted_docx)
                log_message(f"🧹 Cleaned up temporary file: {converted_docx}")
            except Exception as e:
                log_message(f"⚠ Error deleting {converted_docx}: {e}")

    return ""  # Return empty string if all methods fail

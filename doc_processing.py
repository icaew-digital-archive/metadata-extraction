import os
import subprocess

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

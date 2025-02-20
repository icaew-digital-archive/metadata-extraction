import hashlib
import time
from pathlib import Path

import magic


def get_file_metadata(file_path):
    """Extract standard file properties (format, size, modified/created time, hash, extension)."""

    file = Path(file_path)

    if not file.exists():
        return {"error": "File does not exist."}

    # File properties
    file_size = file.stat().st_size
    modified_time = time.strftime(
        '%Y-%m-%d %H:%M:%S', time.localtime(file.stat().st_mtime))
    creation_time = time.strftime(
        '%Y-%m-%d %H:%M:%S', time.localtime(file.stat().st_ctime))

    # File hash (SHA-256)
    with open(file, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    # File format detection
    mime = magic.Magic(mime=True)
    file_format = mime.from_file(str(file))

    return {
        "filename": file.name,
        "format": file_format,
        "size": file_size,
        "modified_time": modified_time,
        "creation_time": creation_time,
        "file_hash": file_hash,
        "extension": file.suffix.lower().replace(".", "")  # Standardized extension
    }


# Example usage
if __name__ == "__main__":
    file_path = "example.pdf"  # Change this to your file
    metadata = get_file_metadata(file_path)

    # Pretty-print output
    import pprint
    pprint.pprint(metadata)


VALID_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
    "application/msword",  # For .doc files
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # For .docx files
}

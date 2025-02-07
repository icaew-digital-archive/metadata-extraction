import os
import time
import hashlib
import mimetypes
import magic
import fitz
from PIL import Image

VALID_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
    "application/msword",  # For .doc files
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # For .docx files
}


def get_file_metadata(file_path):
    stat_info = os.stat(file_path)
    return {
        "format": magic.Magic(mime=True).from_file(file_path),
        "size": stat_info.st_size,
        "modified_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_info.st_mtime)),
        "creation_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_info.st_ctime)),
        "file_hash": hashlib.sha256(open(file_path, 'rb').read()).hexdigest(),
        "extension": os.path.splitext(file_path)[-1].lower().replace('.', '')
    }

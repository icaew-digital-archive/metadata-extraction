import json

from config import *


def load_context():
    """Load Dublin Core metadata definitions from a local JSON file."""
    try:
        with open(METADATA_CONTEXT_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        log_message("Loaded metadata context from local file.")
        return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_message(f"Error loading metadata context: {e}")
        return {}

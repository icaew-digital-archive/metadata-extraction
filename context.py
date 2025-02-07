import json
import os
from config import log_message

DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "context.json")

def load_context():
    """Load Dublin Core metadata definitions from a local JSON file."""
    try:
        with open(DATA_FILE_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        log_message("Loaded metadata context from local file.")
        return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_message(f"Error loading metadata context: {e}")
        return {}

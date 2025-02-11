import json
from typing import List
from pydantic import BaseModel
from dateutil import parser
from openai import OpenAI
from config import OPENAI_API_KEY, log_message
from config import METADATA_PROMPT_SETTINGS

from file_metadata import VALID_MIME_TYPES

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# ✅ Function: Normalize Date Format


def normalize_date(date_str):
    """Convert date to ISO 8601 format (YYYY-MM-DD)."""
    try:
        parsed_date = parser.parse(date_str, fuzzy=True)
        return parsed_date.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return date_str  # Return original value if parsing fails

# ✅ Define Metadata Extraction Schema with Pydantic


class MetadataExtraction(BaseModel):
    title: str
    creator: List[str]
    subject: List[str]
    description: str
    publisher: str
    contributor: List[str]
    date: str  # ISO 8601 format
    type: str
    format: str
    identifier: str
    source: str
    language: str
    relation: List[str]
    coverage: str
    rights: str


# ✅ Define JSON Schema for OpenAI Structured Outputs
metadata_schema = {
    "name": "metadata_extraction",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Document title"},
            "creator": {"type": "array", "items": {"type": "string"}, "description": "Authors or creators"},
            "subject": {"type": "array", "items": {"type": "string"}, "description": "Relevant topics or keywords"},
            "description": {"type": "string", "description": "Brief summary of the document"},
            "publisher": {"type": "string", "description": "Publishing entity"},
            "contributor": {"type": "array", "items": {"type": "string"}, "description": "Other contributors"},
            "date": {"type": "string", "description": "Publication date in ISO 8601 format (YYYY-MM-DD)"},
            "type": {
                "type": "string",
                "enum": ["Text", "Image", "Dataset", "InteractiveResource"],
                "description": "Dublin Core document type"
            },
            "format": {
                "type": "string",
                "enum": list(VALID_MIME_TYPES),
                "description": "MIME type of the document"
            },
            "identifier": {"type": "string", "description": "Unique identifier (e.g., ISBN, DOI)"},
            "source": {"type": "string", "description": "Original document source"},
            "language": {"type": "string", "description": "ISO 639-1 language code"},
            "relation": {"type": "array", "items": {"type": "string"}, "description": "Related documents"},
            "coverage": {"type": "string", "description": "Geographic or temporal coverage"},
            "rights": {"type": "string", "description": "Copyright or usage rights"}
        },
        "required": [
            "title", "creator", "subject", "description", "publisher", "contributor",
            "date", "type", "format", "identifier", "source", "language",
            "relation", "coverage", "rights"
        ],
        "additionalProperties": False
    }
}


def generate_metadata(text, context_data, ocr_text=None):
    """Generate structured metadata using OpenAI's JSON Schema enforcement."""

    if not text.strip() and not ocr_text:
        log_message("Skipping metadata generation due to empty text.")
        return "{}"

    combined_text = text.strip()
    if ocr_text:
        combined_text += f"\n[OCR Extracted Content]\n{ocr_text}"

    # Generate a list of fields that should be included
    included_fields = [
        field for field, enabled in METADATA_PROMPT_SETTINGS["include_fields"].items() if enabled
    ]
    included_fields_str = ", ".join(included_fields)

    # Dynamically modify the JSON schema to include only the selected fields
    custom_metadata_schema = {
        "name": "metadata_extraction",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {key: metadata_schema["schema"]["properties"][key] for key in included_fields},
            "required": included_fields,
            "additionalProperties": False
        }
    }

    # Construct the prompt with explicit field inclusion
    prompt_instructions = f"""
    Extract structured Dublin Core metadata following these guidelines:
    {json.dumps(context_data)}

    Additional Constraints:
    - Description length should be limited to {METADATA_PROMPT_SETTINGS["description_length"]} characters.
    - Provide a {METADATA_PROMPT_SETTINGS["verbosity"]} metadata output.
    - Only extract and return the following metadata fields: {included_fields_str}.
    - Do NOT include any fields that are not explicitly listed.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_instructions},
                {"role": "user", "content": combined_text}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": custom_metadata_schema
            }
        )

        metadata_json = response.choices[0].message.content
        log_message(f"Generated structured metadata: {metadata_json}")

        return metadata_json  # Returning raw OpenAI response directly, no extra validation

    except Exception as e:
        log_message(f"Error during OpenAI structured request: {e}")
        return "{}"

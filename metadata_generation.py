import json
from typing import List
from pydantic import BaseModel, ValidationError
from dateutil import parser
from openai import OpenAI
from config import OPENAI_API_KEY, log_message
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

# ✅ Function: Generate Metadata with OpenAI


def generate_metadata(text, context_data, ocr_text=None):
    """Generate structured metadata using OpenAI's JSON Schema enforcement."""

    if not text.strip() and not ocr_text:
        log_message("Skipping metadata generation due to empty text.")
        return "{}"

    combined_text = text.strip()
    if ocr_text:
        combined_text += f"\n[OCR Extracted Content]\n{ocr_text}"

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in metadata extraction. Extract structured Dublin Core metadata."},
                {"role": "user", "content": combined_text}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": metadata_schema
            }
        )

        metadata_json = response.choices[0].message.content
        log_message(f"Generated structured metadata: {metadata_json}")
        return metadata_json

    except Exception as e:
        log_message(f"Error during OpenAI structured request: {e}")
        return "{}"

# ✅ Function: Parse and Validate OpenAI’s Response


def parse_metadata_response(response_content):
    """Safely parse and validate the OpenAI response using Pydantic."""
    try:
        metadata = MetadataExtraction.parse_raw(response_content)

        # ✅ Normalize the date to ISO 8601 format
        metadata_dict = metadata.dict()
        metadata_dict["date"] = normalize_date(metadata_dict["date"])

        return metadata_dict  # ✅ Ensure final output is a properly formatted dictionary
    except ValidationError as e:
        log_message(f"Metadata validation error: {e.json()}")
        return None


# ✅ Example Execution & Testing
if __name__ == "__main__":
    sample_text = """
    Title: The Future of AI in Research
    Author: Dr. John Smith
    Abstract: This paper explores the advancements in AI and its impact on research methodologies.
    Keywords: AI, Research, Machine Learning, Automation
    """

    try:
        response_content = generate_metadata(sample_text, context_data={})
        parsed_metadata = parse_metadata_response(response_content)

        if parsed_metadata:
            print("✅ Successfully extracted structured metadata:")
            # ✅ Fix Unicode display
            print(json.dumps(parsed_metadata, indent=4, ensure_ascii=False))
        else:
            print("❌ Failed to parse metadata.")
    except Exception as e:
        print(f"Unexpected error: {e}")

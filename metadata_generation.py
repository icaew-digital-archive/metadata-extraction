import json

from openai import OpenAI

from config import *
from context import *
from metadata_prompt import get_prompt_instructions
from metadata_schema import metadata_schema

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def generate_metadata(text, ocr_text=None):
    """Generate structured metadata using OpenAI’s JSON Schema enforcement."""

    if not text.strip() and not ocr_text:
        log_message("Skipping metadata generation due to empty text.")
        return "{}"

    # Merge OCR text if available
    combined_text = text.strip()
    if ocr_text:
        combined_text += f"\n[OCR Extracted Content]\n{ocr_text}"

    # Get prompt instructions
    prompt_instructions = get_prompt_instructions()

    # Dynamically modify JSON schema based on included fields
    included_fields = [
        field for field, enabled in METADATA_PROMPT_SETTINGS["include_fields"].items() if enabled
    ]
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

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": prompt_instructions},
                {"role": "user", "content": combined_text}
            ],
            response_format={"type": "json_schema",
                             "json_schema": custom_metadata_schema}
        )

        metadata_json = response.choices[0].message.content
        log_message(f"Generated structured metadata: {metadata_json}")

        return metadata_json

    except Exception as e:
        log_message(f"Error during OpenAI structured request: {e}")
        return "{}"

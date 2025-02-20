import json

from openai import OpenAI

from config import *
from context import *
from metadata_prompt import get_prompt_instructions
from metadata_schema import metadata_schema

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def generate_metadata(text):
    """Generate structured metadata using OpenAI’s JSON Schema enforcement,
    respecting OUTPUT_EMPTY_FIELDS to include disabled fields as empty values."""

    # Get prompt instructions
    prompt_instructions = get_prompt_instructions()

    # Get enabled fields from config
    enabled_fields = [
        field for field, enabled in METADATA_PROMPT_SETTINGS["include_fields"].items() if enabled
    ]

    # If OUTPUT_EMPTY_FIELDS is True, include all possible fields in the final output
    if OUTPUT_EMPTY_FIELDS:
        all_fields = metadata_schema["schema"]["properties"].keys()
        included_fields = enabled_fields  # AI only extracts enabled fields
        output_fields = all_fields  # Ensure all fields exist in the output
    else:
        included_fields = enabled_fields  # AI extracts only enabled fields
        output_fields = enabled_fields  # Only enabled fields appear in final output

    # Define the JSON schema for AI (only enabled fields for extraction)
    custom_metadata_schema = {
        "name": "metadata_extraction",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                key: metadata_schema["schema"]["properties"][key] for key in included_fields
            },
            "required": included_fields,  # AI is only required to extract enabled fields
            "additionalProperties": False
        }
    }

    # Ensure disabled fields appear as empty in the final output
    # Fill disabled fields with ""
    default_empty_metadata = {key: "" for key in output_fields}

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": prompt_instructions},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_schema",
                             "json_schema": custom_metadata_schema}
        )

        metadata_json = json.loads(response.choices[0].message.content)

        # Merge AI-extracted metadata with empty defaults
        final_metadata = {**default_empty_metadata, **metadata_json}

        log_message(
            f"Generated structured metadata: {json.dumps(final_metadata, indent=4)}")
        return json.dumps(final_metadata)

    except Exception as e:
        log_message(f"Error during OpenAI structured request: {e}")
        # Return empty metadata if AI call fails
        return json.dumps(default_empty_metadata)

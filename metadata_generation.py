import json

from openai import OpenAI
from config import *
from metadata_prompt import get_prompt_instructions
from metadata_schema import metadata_schema

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_metadata(text):
    """Generate structured metadata using OpenAI’s JSON Schema enforcement,
    respecting OUTPUT_EMPTY_FIELDS to include disabled fields as empty values."""

    # Get required fields from context
    required_fields = [field for field, info in METADATA_CONTEXT.items() if info.get("required", False)]

    # Define the JSON schema for AI (using only required fields)
    custom_metadata_schema = {
        "name": "metadata_extraction",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                key: metadata_schema["schema"]["properties"][key] for key in required_fields
            },
            "required": required_fields,
            "additionalProperties": False
        }
    }

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": get_prompt_instructions()},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_schema",
                             "json_schema": custom_metadata_schema}
        )

        metadata_json = json.loads(response.choices[0].message.content)

        log_message(f"Generated structured metadata: {json.dumps(metadata_json, indent=4)}")
        return json.dumps(metadata_json)


    except Exception as e:
        log_message(f"Error during OpenAI structured request: {e}")
        
        # Return empty metadata if AI call fails
        default_empty_metadata = {field: "" for field in METADATA_CONTEXT.keys()}
        return default_empty_metadata

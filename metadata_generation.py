import json
from openai import OpenAI
from config import *
from metadata_prompt import get_prompt_instructions
from metadata_schema import metadata_schema

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_metadata(text):
    """Generate structured metadata using OpenAI’s JSON Schema enforcement."""

    required_fields = [
        field for field, info in METADATA_CONTEXT.items() if info.get("required", False)
    ]

    # Define the JSON schema for OpenAI (without strict enforcement)
    custom_metadata_schema = {
        "type": "object",
        "properties": metadata_schema["schema"]["properties"],
        "required": required_fields if required_fields else [],
        "additionalProperties": False
    }

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": get_prompt_instructions()},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )

        metadata_json = json.loads(response.choices[0].message.content)

        # ✅ Ensure all required fields are included, even if OpenAI omitted them
        for field in required_fields:
            if field not in metadata_json:
                metadata_json[field] = ""  # Fill missing fields with empty string

        log_message(f"Generated structured metadata: {json.dumps(metadata_json, indent=4)}")
        return json.dumps(metadata_json)

    except Exception as e:
        log_message(f"Error during OpenAI structured request: {e}")
        return json.dumps({field: "" for field in METADATA_CONTEXT.keys()})  # Ensure output is JSON

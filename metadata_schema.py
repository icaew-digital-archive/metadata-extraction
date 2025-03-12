import json
from config import METADATA_CONTEXT

metadata_schema = {
    "name": "metadata_extraction",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
}

# Convert Dublin Core & MARC21 into schema dynamically
for field, details in METADATA_CONTEXT.items():
    if isinstance(details, dict) and "properties" in details:
        # MARC21 fields (nested structure)
        prop = {
            "type": "object",
            "properties": details["properties"],
            "required": details.get("required", []),
        }
    else:
        # Standard Dublin Core fields
        prop = details

    metadata_schema["schema"]["properties"][field] = prop

    if "required" in details and details["required"]:
        metadata_schema["schema"]["required"].append(field)

# Print metadata schema in a pretty format
print('OPENAI STRUCTURED OUTPUT:')
print(json.dumps(metadata_schema, indent=4, ensure_ascii=False))
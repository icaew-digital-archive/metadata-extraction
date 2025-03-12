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

# Convert Dublin Core context into schema dynamically
for field, details in METADATA_CONTEXT.items():
    prop = {key: value for key, value in details.items() if key not in ["custom_instructions"]}
    
    # Add property to schema
    metadata_schema["schema"]["properties"][field] = prop
    
    # Handle required fields dynamically
    if prop.pop("required", False):
        metadata_schema["schema"]["required"].append(field)

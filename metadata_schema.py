from file_metadata import VALID_MIME_TYPES

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

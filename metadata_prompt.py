from config import METADATA_PROMPT_SETTINGS
from context import load_context


def get_prompt_instructions():
    """Generate metadata extraction prompt instructions."""
    context_data = load_context()
    dublin_core_metadata = context_data.get("dublin_core", {})

    metadata_guidelines = "\n".join([
        f"- **{field.capitalize()}**: {info['definition']} ({info['comment']})"
        for field, info in dublin_core_metadata.items()
    ])

    included_fields = [
        field for field, enabled in METADATA_PROMPT_SETTINGS["include_fields"].items() if enabled
    ]
    included_fields_str = ", ".join(included_fields)

    return f"""
    Extract structured Dublin Core metadata from the document text.

    **Metadata Fields to Extract:** {included_fields_str}

    **Dublin Core Metadata Definitions:**
    {metadata_guidelines}

    **Guidelines:**
    - Metadata should be structured in JSON format.
    - Ensure descriptions are at least {METADATA_PROMPT_SETTINGS["description_length_min"]} characters long.
    - Limit descriptions to {METADATA_PROMPT_SETTINGS["description_length_max"]} characters.
    - Provide a {METADATA_PROMPT_SETTINGS["verbosity"]} metadata output.
    """

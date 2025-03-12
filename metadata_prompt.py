from config import METADATA_CONTEXT

def get_prompt_instructions():
    """Generate metadata extraction prompt instructions."""
    metadata_guidelines = "\n".join([
        f"- **{field.capitalize()}**: {info['definition']} ({info['comment']})"
        + (f" Custom rule: {info['custom_instructions']}" if "custom_instructions" in info else "")
        for field, info in METADATA_CONTEXT.items()
    ])

    required_fields = [
        field for field, info in METADATA_CONTEXT.items() if info.get("required", False)
    ]
    required_fields_str = ", ".join(required_fields)

    return f"""
    Extract structured metadata from the document text using both the **Dublin Core** and **MARC21** standards.

    **Metadata Fields to Extract:** {required_fields_str}
    
    Follow the `"definition"`, `"comment"`, and `"custom_instructions"` for each metadata element.

    {metadata_guidelines}

    ### **Rules for Compliance**
    - **MARC21 fields must follow their defined subfields and structure.**
    - **Dublin Core fields must be formatted according to their specific rules.**
    - Ensure all extracted metadata is structured in JSON format.
    - Use controlled vocabularies where required.

    The document text is here:
    """

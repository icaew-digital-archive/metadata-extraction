from config import METADATA_CONTEXT

def get_prompt_instructions():
    """Generate metadata extraction prompt instructions."""
    dublin_core_metadata = METADATA_CONTEXT
    
    metadata_guidelines = "\n".join([
        f"- **{field.capitalize()}**: {info['definition']} ({info['comment']})"
        + (f" Custom rule: {info['custom_instructions']}" if "custom_instructions" in info else "")
        for field, info in dublin_core_metadata.items()
    ])

    required_fields = [field for field, info in dublin_core_metadata.items() if info.get("required", False)]
    required_fields_str = ", ".join(required_fields)

    return f"""
    Extract structured Dublin Core metadata from the document text.

    **Metadata Fields to Extract:** {required_fields_str}
    
    What follows is a JSON object that describes the **Dublin Core Metadata Element Set**. You must clearly follow the `"definition"`, `"comment"`, and `"custom_instructions"` for each metadata element. 

    {metadata_guidelines}

    ### **Rules for Compliance**
    - You **MUST** adhere to the instructions in `"custom_instructions"` strictly.
    - Ensure that all generated metadata conforms to the required structure, format, and controlled vocabularies.
    - If input data does not match the expected format, request clarification rather than making assumptions.
    - Do not generate incorrect or non-compliant metadata.

    **General guidelines:**
    - Metadata should be structured in JSON format.
    - Ensure descriptions are at least 200 characters long.
    - Limit descriptions to 500 characters.
    - Provide a detailed metadata output.

    The document text is here:
    """

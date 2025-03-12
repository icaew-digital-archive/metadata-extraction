from config import METADATA_CONTEXT, METADATA_STANDARD


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

    # Adjust prompt based on the selected standard
    standard_label = "Dublin Core" if METADATA_STANDARD == "dublin_core" else "MARC21" if METADATA_STANDARD == "marc21" else "both Dublin Core and MARC21"

    return f"""
    Extract structured metadata from the document text using the **{standard_label}** standard.

    **Metadata Fields to Extract:** {required_fields_str}
    
    Follow the `"definition"`, `"comment"`, and `"custom_instructions"` for each metadata element.

    {metadata_guidelines}

    ### **Rules for Compliance**
    - Ensure compliance with the **{standard_label}** standard.
    - Ensure all extracted metadata is structured in JSON format.
    - Use controlled vocabularies where required.

    The document text is here:
    """

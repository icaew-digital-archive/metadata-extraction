from config import METADATA_CONTEXT, METADATA_STANDARD


def get_prompt_instructions():
    """Generate metadata extraction prompt instructions."""

    metadata_guidelines = []

    for field, info in METADATA_CONTEXT.items():
        field_guidelines = []

        # ✅ Handle flat fields (Dublin Core & MARC21 single-level fields)
        if "definition" in info:
            guideline = f"- **{field}**: {info['definition']}"
            if info.get("comment"):
                guideline += f" ({info['comment']})"
            if "custom_instructions" in info:
                guideline += f" → **{info['custom_instructions']}**"
            field_guidelines.append(guideline)

        # ✅ Handle nested MARC21 fields
        if "properties" in info:
            for sub_key, sub_value in info["properties"].items():
                if isinstance(sub_value, dict) and "definition" in sub_value:
                    guideline = f"  - **{field} ({sub_key})**: {sub_value['definition']}"
                    if sub_value.get("comment"):
                        guideline += f" ({sub_value['comment']})"
                    if "custom_instructions" in sub_value:
                        guideline += f" → **{sub_value['custom_instructions']}**"
                    field_guidelines.append(guideline)

        metadata_guidelines.extend(field_guidelines)

    metadata_guidelines_str = "\n".join(metadata_guidelines)

    # Debugging: Print output to verify correct formatting
    print("DEBUG: Metadata Guidelines\n", metadata_guidelines_str)

    # Get required fields for metadata extraction
    required_fields = [
        field for field, info in METADATA_CONTEXT.items() if info.get("required", False)
    ]
    required_fields_str = ", ".join(required_fields)

    # Adjust prompt based on the selected metadata standard
    standard_label = (
        "Dublin Core" if METADATA_STANDARD == "dublin_core"
        else "MARC21" if METADATA_STANDARD == "marc21"
        else "both Dublin Core and MARC21"
    )

    # ✅ Final structured prompt
    prompt = f"""
Extract structured metadata from the document text using the **{standard_label}** standard.

### **Metadata Fields to Extract**  
{required_fields_str}  

### **Guidelines for Extraction**  
Follow the instructions under `"definition"`, `"comment"`, and especially `"custom_instructions"` for each metadata element.  
📌 **"`custom_instructions` is the most important—you MUST follow these precisely.**  

{metadata_guidelines_str}

### **Rules for Compliance**  
✅ Ensure compliance with the **{standard_label}** standard.  
✅ Extracted metadata **must be in valid JSON format.**  
✅ Follow **controlled vocabularies** where required.  
✅ **Omit missing fields** (do not include empty keys).  

---
"""
    
    print('PROMPT:\n', prompt)  # Debugging output

    return prompt

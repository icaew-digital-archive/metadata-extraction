from config import METADATA_CONTEXT, METADATA_STANDARD


def get_prompt_instructions():
    """Generate metadata extraction prompt instructions with explicit definitions for fields."""

    metadata_guidelines = []

    for field, info in METADATA_CONTEXT.items():
        field_guidelines = []

        # ✅ Handle flat fields (Dublin Core & MARC21 single-level fields)
        if "definition" in info:
            guideline = f"- **{field}**"
            guideline += f"\n  - 🟢 **Definition:** {info['definition']}"
            if info.get("comment"):
                guideline += f"\n  - 🟡 **Comment:** {info['comment']}"
            if "custom_instructions" in info:
                guideline += f"\n  - 🔴 **Custom Instructions:** {info['custom_instructions']}"
            field_guidelines.append(guideline)

        # ✅ Handle nested MARC21 fields
        if "properties" in info:
            for sub_key, sub_value in info["properties"].items():
                if isinstance(sub_value, dict) and "definition" in sub_value:
                    guideline = f"  - **{field} ({sub_key})**"
                    guideline += f"\n    - 🟢 **Definition:** {sub_value['definition']}"
                    if sub_value.get("comment"):
                        guideline += f"\n    - 🟡 **Comment:** {sub_value['comment']}"
                    if "custom_instructions" in sub_value:
                        guideline += f"\n    - 🔴 **Custom Instructions:** {sub_value['custom_instructions']}"
                    field_guidelines.append(guideline)

        metadata_guidelines.extend(field_guidelines)

    metadata_guidelines_str = "\n".join(metadata_guidelines)

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

    # ✅ Final structured prompt with explicit section definitions
    prompt = f"""
Extract structured metadata from the document text using the **{standard_label}** standard.

### **Metadata Fields to Extract**  
{required_fields_str}  

### **Guidelines for Extraction**  
Follow the instructions under `"Definition"`, `"Comment"`, and `"Custom Instructions"` for each metadata element.  
📌 **"`Custom Instructions` is the most important—you MUST follow these precisely.**  

#### **Metadata Field Structure**
- 🟢 **Definition**: A concise explanation of what the metadata element represents.  
- 🟡 **Comment**: Additional guidance, best practices, or context for how to interpret or apply the element.  
- 🔴 **Custom Instructions**: Strict rules that MUST be followed exactly when extracting metadata.  

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

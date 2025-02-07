# metadata_generation.py
from openai import OpenAI
import json
import re
from dateutil import parser
from config import OPENAI_API_KEY, log_message
from file_metadata import VALID_MIME_TYPES


def normalize_date(date_str):
    """Convert date to ISO 8601 format."""
    try:
        parsed_date = parser.parse(date_str, fuzzy=True)
        return parsed_date.strftime("%Y-%m-%d"), True
    except (ValueError, TypeError):
        return date_str, False


client = OpenAI(api_key=OPENAI_API_KEY)


def clean_json_output(content):
    """Remove Markdown formatting from JSON."""
    json_content = re.sub(r"```json(.*?)```", r"\1",
                          content, flags=re.DOTALL).strip()
    return json_content if json_content.startswith('{') else "{}"


def validate_and_flag_metadata(metadata_json):
    """Validate metadata fields."""
    try:
        metadata = json.loads(metadata_json)
        validation_flags = {}

        # In metadata_generation.py, inside validate_and_flag_metadata()
        if "date" in metadata and metadata["date"]:
            normalized_date, was_parsed = normalize_date(metadata["date"])
            if was_parsed:
                # Remove metadata["parsed_date"] = True
                metadata["date"] = normalized_date

        if "format" in metadata and metadata["format"] not in VALID_MIME_TYPES:
            validation_flags["format"] = f"Invalid format detected: {metadata['format']}"

        if validation_flags:
            metadata["validation_warnings"] = validation_flags
            log_message(f"⚠️ Validation Warnings: {validation_flags}")

        return json.dumps(metadata, indent=4)
    except json.JSONDecodeError as e:
        log_message(f"Error decoding JSON: {e}")
        return metadata_json


def generate_metadata(text, dublin_core_definitions, ocr_text=None):
    """ Generate metadata using OpenAI and validate it """
    if not text.strip() and not ocr_text:
        log_message("Skipping metadata generation due to empty text.")
        return "{}"

    combined_text = text.strip()
    if ocr_text:
        combined_text += f"\n[OCR Extracted Content]\n{ocr_text}"

    system_message = f"""
    You are an expert in metadata extraction. Use the Dublin Core Metadata Element Set and related standards to describe documents.
    Here are the relevant metadata standards you must follow:
    - Dublin Core Elements: {dublin_core_definitions.get('Dublin Core Elements', '')}
    - Format: {dublin_core_definitions.get('Format', '')}
    - Date: {dublin_core_definitions.get('Date', '')}
    - Type: {dublin_core_definitions.get('Type', '')}
    - Language: {dublin_core_definitions.get('Language', '')}

    **STRICT RULES:**
    - **Title**: Document title must be clearly extracted from the text.
    - **Creator**: Must be an individual or organization listed explicitly.
    - **Subject**: List relevant subjects or keywords from the document.
    - **Description**: A summary of the document's content.
    - **Publisher**: If available, the entity responsible for publishing.
    - **Contributor**: Individuals or organizations that contributed to the document.
    - **Date**: Must be in ISO 8601 format (YYYY-MM-DD or YYYY-MM).
    - **Type**: Must be one of the official Dublin Core Types.
    - **Format**: Must be a valid IANA Media Type.
    - **Identifier**: If available, a unique identifier (e.g., ISBN, DOI).
    - **Source**: If available, the original source of the document.
    - **Language**: Must use an ISO 639-1 language code.
    - **Relation**: Any related documents or links.
    - **Coverage**: Geographic or temporal coverage of the document.
    - **Rights**: Copyright or usage rights information.

    **Example Correct Output:**
    ```json
    {{
    "title": "Sample Document",
    "creator": ["John Doe"],
    "subject": ["Metadata Extraction", "AI"],
    "description": "This is a sample document following Dublin Core standards.",
    "publisher": "OpenAI Press",
    "contributor": ["Jane Smith"],
    "date": "2023-05-10",
    "type": "Text",
    "format": "application/pdf",
    "identifier": "urn:uuid:123e4567-e89b-12d3-a456-426614174000",
    "source": "https://example.com/sample-document",
    "language": "en",
    "relation": ["https://example.com/related-resource"],
    "coverage": "Global",
    "rights": "© 2023 OpenAI. All rights reserved."
    }}
    ```
    """

    user_prompt = f"""
    Analyse the document and generate metadata for the following 15 elements:
    {text}
    Provide the metadata in JSON format, adhering strictly to the Dublin Core rules. Use British English spellings where possible.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_message},
                      {"role": "user", "content": user_prompt}]
        )

        if response and response.choices:
            metadata_json = clean_json_output(
                response.choices[0].message.content)
            validated_metadata = validate_and_flag_metadata(metadata_json)
            log_message(f"Generated metadata: {validated_metadata}")
            return validated_metadata

    except Exception as e:
        log_message(f"Error during OpenAI request: {e}")

    return "{}"

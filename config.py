"""
Profile-based configuration for the metadata extraction system.

Loads a YAML profile and assembles the system prompt from the generic base
plus profile-specific content. See profiles/default.yaml for the schema.
"""

import os
import yaml

# OpenAI API settings
DEFAULT_MODEL = "gpt-5"
FILE_PURPOSE = "user_data"

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Default profile (ICAEW) kept for backward compatibility
DEFAULT_PROFILE_PATH = os.path.join(_BASE_DIR, "profiles", "icaew.yaml")


def load_profile(profile_path: str = None) -> dict:
    """Load a YAML profile. Falls back to the ICAEW profile if path is None."""
    path = profile_path or DEFAULT_PROFILE_PATH
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_profiles() -> list:
    """Return a list of (display_name, file_path) tuples for all available profiles."""
    profiles_dir = os.path.join(_BASE_DIR, "profiles")
    results = []
    for fname in sorted(os.listdir(profiles_dir)):
        if fname.endswith(".yaml") or fname.endswith(".yml"):
            fpath = os.path.join(profiles_dir, fname)
            try:
                p = load_profile(fpath)
                results.append((p.get("name", fname), fpath))
            except Exception:
                pass
    return results


# ── generic base content ──────────────────────────────────────────────────────

_GENERIC_GUIDELINES = [
    'Always extract metadata from the document content, not from file metadata',
    'If a field\'s value cannot be determined with high confidence from the document content, return an empty string ("") for single-value fields or empty array ([]) for multi-value fields',
    'If a field is marked as "NOT USED" or "RESERVED", return an empty array ([]) for multi-value fields or empty string ("") for single-value fields',
    'Do not make assumptions or infer values',
    'For dates, prefer dates found within the document over any other source',
    'For titles, use the exact title as it appears in the document',
    'For creators, use the exact names/entities as credited in the document',
    'If multiple values exist for a field, ALWAYS return them as an array (e.g., ["Value 1", "Value 2", "Value 3"]) - NEVER use semicolons or other separators',
    'Do not add explanatory text or notes in the metadata values',
    'Maintain consistent formatting across all documents',
    'Use only standard ASCII characters - avoid special Unicode characters, em-dashes, en-dashes, or smart quotes',
    'Replace any em-dashes (—), en-dashes (–), or hyphens used as title separators with colons (:), with the exception when they show a date range, i.e. do not replace "2008-09" with "2008:09"',
    'Acronyms (such as common abbreviations) must ALWAYS be in all capitals, regardless of their position in the sentence or title. Do NOT use title case for acronyms',
    'When the user provides contextual background (e.g. "these are photos of Chartered Accountant\'s Hall"), use it to identify and name the subject in your description. Describe what is shown in the document but use the names, places, and events from the context rather than generic terms. Do not output a description that ignores the context and uses only generic wording.',
]

_GENERIC_TITLE = '''\
**Title (REQUIRED)**
- Single value only
- Use the title as it appears in the document
- Use sentence case (capitalise first word only), but acronyms must always be in all capitals, even at the start of the title or after a colon
- ALWAYS use colons (:) to separate title and subtitle - replace any em-dashes (—), en-dashes (–), or hyphens (-) used as separators with colons
- Do not capitalise the first letter after a colon
- Do not use "&"; use "and"
- Use question marks if applicable, but do not end with full stops
- The order and format should be: title, subtitle, issue/volume, date
- If a title does not follow this format, reorganise it accordingly. For example:
  * "UK business confidence monitor report: Q4 2012 Scotland" should become "UK business confidence monitor report: Scotland, Q4 2012"
- Use readable date formatting in titles: "15th January 2024" format (e.g., "15th January 2024" not "2024-01-15" or "January 15, 2024")
- Indicate if the content is revised or time-limited
- Use only standard ASCII characters - avoid Unicode characters, smart quotes, or special symbols'''

_GENERIC_CREATOR = '''\
**Creator (REQUIRED)**
- Multiple values allowed (return as array)
- Order of creators (from most specific to most general):
  1. Individual authors (e.g., "John Smith")
  2. Department or group (e.g., "Research Team")
  3. Institution or organisation (e.g., "Acme Corporation")
- For anonymous works, use "Anonymous" as the creator
- For corporate authors, list the organisation name
- For letters and correspondence: include sender first, then recipient if both are clearly identified (e.g., ["John Smith", "Organisation Name"])
- Use full names when available (e.g., "John Smith" not "J. Smith")
- Use consistent formatting: "First Name Last Name" or "Organisation Name"'''

_GENERIC_DESCRIPTION = '''\
**Description (REQUIRED)**
- Single value only
- Briefly summarise the content; if a summary is present in the document itself, make use of it
- Every description should describe what the document is (e.g. what type of document it is, who authored it) and what it is about
- For transcript files: describe the video or podcast content itself, not the transcript document. Write the description from the perspective of describing the original media (video/podcast), not as "a transcript of..." or "transcript of a...". The description should read as if it is describing the video or podcast directly.
- Listing of contents may be helpful - but they are of secondary importance. Each item in the list of contents should be separated by a semicolon.
- Should always finish with a full stop or question mark
- After the description append the string "(AI generated description)"'''

_GENERIC_PUBLISHER = '''\
**Publisher (REQUIRED)**
- Single value only
- Use publisher name as credited in the document
- If no publisher is explicitly credited, use the organisation name if available
- If no organisation is identified, return an empty string ("")'''

_GENERIC_CONTRIBUTOR = '''\
**Contributor (OPTIONAL)**
- Multiple values allowed (return as array)
- Used for individuals or organisations who contributed to the document but are not the primary creator
- Use full organisation names'''

_GENERIC_DATE = '''\
**Date (REQUIRED)**
- Single value only
- Use YYYY-MM-DD format with zero-padding for single digits when the full date is known
- If day is unknown, use YYYY-MM format
- If month is unknown, use YYYY format
- Use the date found within the document
- Convert any date format to YYYY-MM-DD (e.g., "10/7/2009" becomes "2009-10-07", "January 28, 2009" becomes "2009-01-28")
- Examples: "2024-03-15", "2024-03", "2024", "2009-02-05"'''

_GENERIC_TYPE = '''\
**Type (REQUIRED)**
- Single value only
- Use DCMI type values in sentence case
- Common types:
  * Text (for documents, articles, reports)
  * Moving Image (for videos, animations)
  * Still Image (for photographs, diagrams)
  * Sound (for audio recordings)
  * Dataset (for spreadsheets, databases)
  * Interactive Resource (for web pages, applications)
  * Collection (for sets of related items)
- Default to "Text" for PDF documents
- If type cannot be determined, use "Text" as default'''

_GENERIC_FORMAT = '''\
**Format (REQUIRED)**
- Single value only
- Use the lowercase file extension of the ORIGINAL source document (before conversion to PDF)
- For PDF documents that were originally PDFs, use "pdf"
- For Microsoft Word documents converted to PDF, use "docx" or "doc"
- For Microsoft Excel documents converted to PDF, use "xlsx"
- For text files converted to PDF, use "txt"
- For SRT files converted to PDF, use "srt"
- For images converted to PDF, use the appropriate extension (e.g., "jpg", "png", "tiff")
- If format cannot be determined, use "pdf" as default'''

_GENERIC_IDENTIFIER = '''\
**Identifier (OPTIONAL)**
- Multiple values allowed (return as array)
- Only include ISBNs (e.g., "ISBN 978-1-78915-123-4") and URLs
- Do not include random strings of letters and numbers
- If no clear identifiers are found, return an empty array ([])'''

_GENERIC_LANGUAGE = '''\
**Language (REQUIRED)**
- Multiple values allowed (return as array)
- Use ISO 639-1 codes
- Default to ["en"] for English documents
- Examples: ["en"] (English), ["ar"] (Arabic), ["zh"] (Chinese), ["en", "fr"] (bilingual)'''

_GENERIC_RELATION = '''\
**Relation (OPTIONAL)**
- Multiple values allowed (return as array)
- Name of the collection or series the document belongs to'''

_GENERIC_VALIDATION_RULES = [
    'REQUIRED fields must not be empty: Title, Creator, Description, Publisher, Date, Type, Format, Language',
    'Dates must be in correct format (YYYY-MM-DD, YYYY-MM, or YYYY) with zero-padding for single digits',
    'Multiple values must be arrays of strings, not semicolon-separated strings',
    'All text should be properly encoded (no special characters or emojis)',
    'No trailing or leading whitespace in any field',
    'No explanatory text or notes in the values',
    'Output must be valid JSON',
    'Field values can be strings or arrays of strings (not null, numbers, or other types)',
    'Empty values must be empty strings ("") for single-value fields or empty arrays ([]) for multi-value fields, not null',
    'Title field must follow the order: title, subtitle, issue/volume, date',
]


# ── prompt builder ────────────────────────────────────────────────────────────

def _render_output_field(field: dict, include_subjects: bool) -> str:
    """Return one line of the JSON output template for a given field spec."""
    name = field["name"]
    if field.get("reserved"):
        val = '""' if field.get("type", "string") == "string" else "[]"
        return f'    "{name}": {val},'
    t = field.get("type", "string")
    if t == "subject":
        val = '["string", "string", ...]' if include_subjects else "[]"
    elif t == "array":
        val = '["string", "string", ...]'
    else:
        val = '"string"'
    return f'    "{name}": {val},'


def build_system_prompt(profile: dict, include_subjects: bool = True) -> str:
    """Assemble the system prompt from the profile and the generic base."""
    parts = []

    # 1. Role
    role = profile.get("role", "You are a metadata archivist. Your task is to analyse uploaded documents and extract structured metadata following the Dublin Core schema.")
    parts.append(role)

    # 2. Guidelines
    parts.append("\nIMPORTANT GUIDELINES:")
    extra = profile.get("extra_guidelines") or []
    all_guidelines = _GENERIC_GUIDELINES + [g.strip() for g in extra]
    for i, g in enumerate(all_guidelines, 1):
        parts.append(f"{i}. {g}")

    # 3. XIP fields
    if profile.get("xip_fields"):
        parts.append("\n### XIP Metadata Fields\n")
        parts.append("**entity.title (REQUIRED)**")
        parts.append("- Single value only")
        parts.append("- This should be an exact copy of the Dublin Core Title field as described below")
        parts.append("")
        parts.append("**entity.description (REQUIRED)**")
        parts.append("- Single value only")
        parts.append("- This should be an exact copy of the Dublin Core Description field as described below")

    # 4. Custom fields
    custom_fields = profile.get("custom_fields") or []
    if custom_fields:
        parts.append("\n### Organisation-Specific Fields\n")
        for cf in custom_fields:
            if cf.get("reserved"):
                multiple = cf.get("multiple", False)
                empty = "[]" if multiple else '""'
                parts.append(f"**{cf['id']} (RESERVED)**")
                parts.append("- This field is reserved for future use")
                parts.append(f"- Always return an empty {('array (' + empty + ')') if multiple else ('string (' + empty + ')')} for this field")
                parts.append("- Do not attempt to extract or infer values for this field")
                parts.append("")
            else:
                pt = cf.get("prompt_text", "")
                parts.append(pt.rstrip())
                parts.append("")

    # 5. Dublin Core fields
    parts.append("### Dublin Core Metadata Fields\n")

    title_override = profile.get("title_override")
    parts.append(title_override.rstrip() if title_override else _GENERIC_TITLE)
    parts.append("")

    creator_override = profile.get("creator_override")
    parts.append(creator_override.rstrip() if creator_override else _GENERIC_CREATOR)
    parts.append("")

    # Subject
    if not include_subjects:
        parts.append("**Subject (RESERVED)**")
        parts.append("- This field is reserved for future use")
        parts.append("- Always return an empty array ([]) for this field")
        parts.append("- Do not attempt to extract or infer values for this field")
    else:
        topic_file = profile.get("subject_topic_list_file")
        subject_max = profile.get("subject_max", 10)
        if topic_file:
            parts.append("**Subject (OPTIONAL)**")
            parts.append("- Multiple values allowed (return as array)")
            parts.append("- Use hierarchical topic classification from the topic list provided below")
            parts.append("- When selecting a specific topic, you MUST include all parent topics above it in the hierarchy")
            parts.append(f"- Maximum of {subject_max} subjects total")
            parts.append("- Use exact topic names from the hierarchical list (case-sensitive)")
            parts.append('- Format: for nested topics, include both the main topic and sub-topic (e.g., ["Financial reporting and accounting standards", "Accounting topics", "Accounting for assets"])')
            parts.append("- If selecting a deep topic, always include the full path from top-level down to that topic")
            parts.append("- Prefer more specific topics over general ones when appropriate")
            parts.append("- If a document covers multiple distinct topic areas, select the most relevant ones")
            parts.append("- If no relevant topics are found, return an empty array ([])")
            parts.append("- Examples of hierarchical selection:")
            parts.append('  * For a document about IFRS implementation: ["Financial reporting and accounting standards", "IFRSs", "IFRS 15 Revenue from contracts with customers"]')
            parts.append('  * For audit guidance: ["Audit and assurance", "Audit best practice", "Audit documentation"]')
        else:
            parts.append("**Subject (OPTIONAL)**")
            parts.append("- Multiple values allowed (return as array)")
            parts.append("- Use keywords or topics that best describe the content")
            parts.append("- If no relevant topics are found, return an empty array ([])")

    parts.append("")
    parts.append("**Source, Coverage, Rights (RESERVED)**")
    parts.append('- These fields are reserved for future use')
    parts.append('- Always return an empty string ("") for these fields')
    parts.append("- Do not attempt to extract or infer values for these fields")
    parts.append("")
    description_override = profile.get("description_override")
    parts.append(description_override.rstrip() if description_override else _GENERIC_DESCRIPTION)
    parts.append("")

    publisher_override = profile.get("publisher_override")
    parts.append(publisher_override.rstrip() if publisher_override else _GENERIC_PUBLISHER)
    parts.append("")

    contributor_override = profile.get("contributor_override")
    parts.append(contributor_override.rstrip() if contributor_override else _GENERIC_CONTRIBUTOR)
    parts.append("")

    parts.append(_GENERIC_DATE)
    parts.append("")
    parts.append(_GENERIC_TYPE)
    parts.append("")
    parts.append(_GENERIC_FORMAT)
    parts.append("")

    identifier_override = profile.get("identifier_override")
    parts.append(identifier_override.rstrip() if identifier_override else _GENERIC_IDENTIFIER)
    parts.append("")

    parts.append(_GENERIC_LANGUAGE)
    parts.append("")

    relation_override = profile.get("relation_override")
    parts.append(relation_override.rstrip() if relation_override else _GENERIC_RELATION)

    # 6. Output format
    output_fields = profile.get("output_fields") or []
    if not output_fields:
        output_fields = [
            {"name": "Title", "type": "string"},
            {"name": "Creator", "type": "array"},
            {"name": "Subject", "type": "subject"},
            {"name": "Description", "type": "string"},
            {"name": "Publisher", "type": "string"},
            {"name": "Contributor", "type": "array"},
            {"name": "Date", "type": "string"},
            {"name": "Type", "type": "string"},
            {"name": "Format", "type": "string"},
            {"name": "Identifier", "type": "array"},
            {"name": "Source", "type": "string", "reserved": True},
            {"name": "Language", "type": "array"},
            {"name": "Relation", "type": "array"},
            {"name": "Coverage", "type": "string", "reserved": True},
            {"name": "Rights", "type": "string", "reserved": True},
        ]

    parts.append("\n### Output Format")
    parts.append("Return metadata as a JSON object with the following structure. Fields can be strings or arrays of strings. Empty values should be empty strings (\"\") or empty arrays ([]). Multiple values should be arrays:\n")
    parts.append("{")
    field_lines = [_render_output_field(f, include_subjects) for f in output_fields]
    # Strip trailing comma from last line
    if field_lines:
        field_lines[-1] = field_lines[-1].rstrip(",")
    parts.extend(field_lines)
    parts.append("}")

    # 7. Examples
    examples = profile.get("examples") or []
    if examples:
        parts.append("\nExample outputs:")
        for ex in examples:
            parts.append(ex.strip())

    # 8. Topic list
    if include_subjects:
        topic_file = profile.get("subject_topic_list_file")
        if topic_file:
            topic_path = os.path.join(_BASE_DIR, topic_file)
            try:
                with open(topic_path, "r", encoding="utf-8") as f:
                    topic_content = f.read().strip()
                parts.append("\n### Topic List for Subject Classification\n")
                parts.append(topic_content)
            except OSError as e:
                parts.append(f"\n[Warning: could not load topic list from {topic_path}: {e}]")

    # 9. Validation rules
    parts.append("\n### Validation Rules")
    extra_rules = profile.get("extra_validation_rules") or []
    all_rules = _GENERIC_VALIDATION_RULES + [r.strip() for r in extra_rules]
    for i, rule in enumerate(all_rules, 1):
        parts.append(f"{i}. {rule}")

    parts.append("\nIf you encounter any issues or ambiguities in the document, use an empty string (\"\") for single-value fields or empty array ([]) for multi-value fields rather than making assumptions.")

    return "\n".join(parts)


def get_system_prompt(include_subjects: bool = True, profile_path: str = None) -> str:
    """Convenience function: load profile and build system prompt."""
    profile = load_profile(profile_path)
    return build_system_prompt(profile, include_subjects)

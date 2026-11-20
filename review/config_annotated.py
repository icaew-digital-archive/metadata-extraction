# =============================================================================
# REVIEW COPY of config.py - NOT USED BY THE TOOL
#
# The generic rules here apply to EVERY profile unless the profile overrides
# them (ICAEW overrides Title, Creator, Description, Publisher, Contributor,
# Identifier and Relation - but NOT Date, Type, Format, Language, the
# guidelines or the validation rules).
#
# Suggestions are inserted directly after the line they refer to, marked:
#   # [IMPROVEMENT SUGGESTION #n]
# Suggestions about the ICAEW profile are in review/icaew_annotated.yaml.
# =============================================================================

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
    'Do not invent values. Every value must be supported by the document itself, or produced by applying the rules below (for example, reformatting a title, converting a date, or normalising an organisation name). If neither applies, return an empty string ("") for single-value fields or an empty array ([]) for multi-value fields',
    'If a field is marked as "NOT USED" or "RESERVED", return an empty array ([]) for multi-value fields or empty string ("") for single-value fields',
    'For dates, prefer dates found within the document over any other source',
    'For titles, start from the title as it appears in the document, then apply the Title rules below (capitalisation, punctuation, order and date)',
    'For creators, use the people and organisations credited in the document, written according to the Creator rules below (e.g. full names, and the standard form of ICAEW)',
    'For multi-value fields, ALWAYS return the values as an array (e.g., ["Value 1", "Value 2", "Value 3"]), never as one string joined with semicolons or other separators',
    'Do not add explanatory text or notes in the metadata values',
    'Maintain consistent formatting across all documents',
    'Use straight quotes and apostrophes (not smart quotes); £, € and accented letters in names are allowed. Do not use emojis',
    'Acronyms must ALWAYS be in all capitals wherever they appear, including at the start of a title or after a colon: {acronym_examples}. Do NOT use title case for acronyms. The exception is mixed-case brand names, which keep their own capitalisation (e.g. "eBook", "iXBRL")',
    'When the user provides contextual background (e.g. "these are photos of Chartered Accountant\'s Hall"), use it to identify and name the subject in your description. Describe what is shown in the document using the names, places and events from the context (e.g. "Photograph showing Chartered Accountant\'s Hall, with...") rather than generic terms such as "a building" or "an office block".',
]

_GENERIC_TITLE = '''\
**Title (REQUIRED)**
- Single value only
- Use the title as it appears in the document
- Use sentence case: capitalise the first word and proper nouns (names of people, organisations, places, named publications and standards) and write everything else in lower case. Acronyms always stay in capitals
- ALWAYS use colons (:) to separate title and subtitle - replace any em-dashes (—), en-dashes (–), or hyphens (-) used as separators with colons, except in date or number ranges (keep "2008-09", do not write "2008:09")
- Do not capitalise the first word after a colon, unless it is a proper noun or acronym
- Do not use "&"; use "and"
- Use question marks if applicable, but do not end with full stops
- The order and format should be: title, subtitle, issue/volume, date
- If a title does not follow this format, reorganise it accordingly. For example:
  * "UK business confidence monitor report: Q4 2012 Scotland" should become "UK business confidence monitor report: Scotland, Q4 2012"
- Use readable date formatting in titles: "15th January 2024" format (e.g., "15th January 2024" not "2024-01-15" or "January 15, 2024")
- Indicate if the content is revised or time-limited'''

_GENERIC_CREATOR = '''\
**Creator (REQUIRED)**
- Multiple values allowed (return as array)
- Order of creators (from most specific to most general):
  1. Individual authors (e.g., "John Smith")
  2. Department or group (e.g., "Research Team")
  3. Institution or organisation (e.g., "Acme Corporation")
- For anonymous works, use "Anonymous" as the creator
- For corporate authors, list the organisation name
- For letters and correspondence: include the sender(s) only; put the recipient in Contributor
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
# [IMPROVEMENT SUGGESTION #1] Fine as is. Optional: also record AI involvement at record level (e.g. a
#     fixed icaew:Notes value or a provenance field) so AI-generated Titles and
#     Subjects are traceable too, not only Descriptions.

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
- For letters and correspondence, include the recipient here
- Use full organisation names'''

_GENERIC_DATE = '''\
**Date (REQUIRED)**
- Single value only
- Always use the YYYY-MM-DD format, with zero-padding for single digits (e.g., "2009-02-05")
- Only include the parts of the date the document gives: if the day is unknown, use YYYY-MM; if the month is also unknown, use YYYY. Never add a day or month that is not in the document (e.g., do not turn "March 2021" into "2021-03-01")
- Use the date found within the document
- Always read numeric dates as day/month/year (UK convention), including in American documents: "10/7/2009" means 10 July 2009 and becomes "2009-07-10". Only when day/month is impossible (e.g. "12/25/2009", as there is no month 25) read it as month/day
- Convert written dates the same way: "28 January 2009" and "January 28, 2009" both become "2009-01-28"; "March 2021" becomes "2021-03"
- Examples: "2024-03-15", "2024-03", "2024", "2009-02-05"'''

_GENERIC_TYPE = '''\
**Type (REQUIRED)**
- Single value only
- Use DCMI type values in sentence case
# [IMPROVEMENT SUGGESTION #2] The official DCMI Type terms are written without spaces: Text,
#     StillImage, MovingImage, Sound, Dataset, InteractiveResource, Collection,
#     Event, Image, PhysicalObject, Service, Software. "Moving Image" is neither
#     official nor sentence case. Proposed: use the official terms exactly, for
#     compatibility with other systems.
- Common types:
  * Text (for documents, articles, reports)
  * Moving Image (for videos, animations)
  * Still Image (for photographs, diagrams)
  * Sound (for audio recordings)
  * Dataset (for spreadsheets, databases)
  * Interactive Resource (for web pages, applications)
  * Collection (for sets of related items)
- Default to "Text" for PDF documents
# [IMPROVEMENT SUGGESTION #3] Every file reaches the model as a PDF, so photos (jpg/png/tiff converted
#     to PDF) will be labelled "Text". Proposed: decide Type from the ORIGINAL
#     format (images -> StillImage; srt/vtt transcripts -> Text, or MovingImage/
#     Sound if you'd rather describe the media). Requires a small code change to
#     tell the model the original format, or to set Type from it directly.
- If type cannot be determined, use "Text" as default'''

_GENERIC_FORMAT = '''\
**Format (REQUIRED)**
- Single value only
- Use the lowercase file extension of the ORIGINAL source document (before conversion to PDF)
# [IMPROVEMENT SUGGESTION #4] These Format instructions have no effect: the code replaces the model's
#     Format with the detected original format when writing the CSV and the
#     Preservica metadata. Proposed: shorten to "Return \"pdf\"; this field is
#     set automatically", or mark Format reserved. This saves prompt length.
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
# [IMPROVEMENT SUGGESTION #5] Consider ISSN and DOI, and limiting URLs to the document's own
#     address - see ICAEW review #25.
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
    'REQUIRED fields (Title, Creator, Description, Publisher, Date, Type, Format, Language) should be filled whenever the document supports a value. If it does not, leave the field empty rather than guessing',
    'Dates must be in correct format (YYYY-MM-DD, YYYY-MM, or YYYY) with zero-padding for single digits',
    'Multiple values must be arrays of strings, not semicolon-separated strings',
    'No emojis or decorative symbols',
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
    acronyms = profile.get("acronym_examples") or ["UK", "VAT"]
    acronym_examples = ", ".join(f'"{a}" (not "{a.capitalize()}")' for a in acronyms)
    all_guidelines = [g.replace("{acronym_examples}", acronym_examples) for g in _GENERIC_GUIDELINES]
    all_guidelines += [g.strip() for g in extra]
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
                parts.append(f"- {cf.get('reserved_reason', 'This field is reserved for future use')}")
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
            parts.append('  * For audit guidance: ["Audit and assurance", "Audit process", "Audit documentation"]')
        else:
            parts.append("**Subject (OPTIONAL)**")
            parts.append("- Multiple values allowed (return as array)")
            parts.append("- Use keywords or topics that best describe the content")
            parts.append("- If no relevant topics are found, return an empty array ([])")

    parts.append("")
    parts.append("**Source, Coverage, Rights (RESERVED)**")
    # [IMPROVEMENT SUGGESTION #6] Worth reconsidering for an archive:
    #     - Rights: documents often print a copyright line ("© ICAEW 2014"), which
    #     could fill dc:rights reliably, e.g. "Copyright ICAEW 2014".
    #     - Coverage: geographic or time coverage is often explicit in titles
    #     ("UK business confidence monitor: Scotland, Q4 2012"), e.g. "Scotland".
    #     Leave as reserved if Preservica/catalogue practice doesn't use them.
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

    parts.append("\nIf something in the document is ambiguous and the rules above do not resolve it, leave that field empty rather than guessing.")

    return "\n".join(parts)


def get_system_prompt(include_subjects: bool = True, profile_path: str = None) -> str:
    """Convenience function: load profile and build system prompt."""
    profile = load_profile(profile_path)
    return build_system_prompt(profile, include_subjects)


# ── subject validation ────────────────────────────────────────────────────────

def load_valid_topics(topic_file_path: str) -> set:
    """Parse a topic list file and return a set of all valid topic name strings."""
    valid = set()
    try:
        with open(topic_file_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("- "):
                    valid.add(stripped[2:])
    except OSError:
        pass
    return valid


def validate_subjects(subjects: list, valid_topics: set, max_count: int) -> list:
    """Filter subjects to only those in valid_topics, then truncate to max_count."""
    result = subjects
    if valid_topics:
        result = [s for s in result if s in valid_topics]
    if max_count:
        result = result[:max_count]
    return result


def get_reserved_fields(profile_path: str = None) -> set:
    """Return the names of fields the AI must leave empty for this profile.

    Covers reserved output_fields and reserved custom_fields. Subject is not
    included: it is controlled separately by include_subjects.
    """
    profile = load_profile(profile_path)
    reserved = {f["name"] for f in profile.get("output_fields") or [] if f.get("reserved")}
    reserved |= {f["id"] for f in profile.get("custom_fields") or [] if f.get("reserved")}
    return reserved


def get_subject_constraints(profile_path: str = None) -> tuple:
    """Return (valid_topics_set, subject_max) for the given profile.

    Returns (empty set, 0) when the profile has no topic list, meaning no
    validation is applied.
    """
    profile = load_profile(profile_path)
    topic_file = profile.get("subject_topic_list_file")
    subject_max = profile.get("subject_max", 10)
    if not topic_file:
        return set(), 0
    topic_path = os.path.join(_BASE_DIR, topic_file)
    return load_valid_topics(topic_path), subject_max

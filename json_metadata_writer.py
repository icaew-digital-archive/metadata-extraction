"""
Module for writing metadata to JSON files in real-time.
"""

import json
import os
import re
import tempfile
import threading
from typing import Dict, List, Any
from datetime import datetime

from config import (get_description_suffix, get_reserved_fields, get_subject_constraints,
                    get_topic_order, validate_subjects)


class JSONMetadataWriter:
    # One lock per output file, shared by every writer in this process, so
    # documents processed in parallel never overwrite each other's records
    _file_locks: Dict[str, threading.Lock] = {}
    _file_locks_guard = threading.Lock()
    def __init__(self, json_file: str, profile_path: str = None) -> None:
        """
        Initialize the JSON metadata writer.

        Args:
            json_file (str): Path to the JSON file to write to
            profile_path (str): Path to a YAML profile file (used for subject validation)
        """
        self.json_file = json_file
        with JSONMetadataWriter._file_locks_guard:
            self._lock = JSONMetadataWriter._file_locks.setdefault(
                os.path.abspath(json_file), threading.Lock())
        self._valid_topics, self._subject_max = get_subject_constraints(profile_path)
        # Subjects are saved in topic-list order, so the same set always reads the same way
        self._topic_order = get_topic_order(profile_path)
        # Every AI-written description must carry this marker; added if the model leaves it out
        self._description_suffix = get_description_suffix(profile_path)
        # Fields the AI must never fill (e.g. user-entered icaew:Notes): forced empty
        self._reserved_fields = get_reserved_fields(profile_path)
        self._initialize_json()

    def _initialize_json(self) -> None:
        """Create the JSON file if it doesn't exist or is empty.

        An existing file that cannot be parsed is never overwritten, because it
        may hold records from earlier runs. An error is raised instead so the
        file can be inspected or restored.
        """
        if os.path.exists(self.json_file) and os.path.getsize(self.json_file) > 0:
            try:
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    json.load(f)
                return
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Existing JSON file {self.json_file} is not valid JSON ({e}). "
                    "It has not been modified. Fix or move it, or choose a different output file."
                ) from e

        now = datetime.now().isoformat()
        self._write_atomic({
            "metadata": [],
            "created_at": now,
            "last_updated": now,
            "total_records": 0
        })

    def _write_atomic(self, data: Dict[str, Any]) -> None:
        """Write data to a temporary file, then swap it in, so an interrupted
        write can never leave a half-written JSON file behind."""
        directory = os.path.dirname(os.path.abspath(self.json_file))
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix='.tmp_', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.json_file)
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    # Typographic characters -> plain equivalents. Other non-ASCII characters
    # (e.g. £, é, ü) are kept, since removing them changes the meaning of the text.
    # Order matters: mojibake sequences contain curly quotes, so they go first.
    _REPLACEMENTS = {
        '\u00e2\u20ac\u201d': '\u2014',  # mojibake (UTF-8 read as Windows-1252) of em dash
        '\u00e2\u20ac\u201c': '\u2013',  # mojibake of en dash
        '\u00e2\u20ac\u2122': "'",       # mojibake of apostrophe
        '\u2018': "'",    # left single quote
        '\u2019': "'",    # right single quote / apostrophe
        '\u201a': "'",    # single low-9 quote
        '\u201c': '"',    # left double quote
        '\u201d': '"',    # right double quote
        '\u201e': '"',    # double low-9 quote
        '\u2026': '...',  # ellipsis
        '\u00a0': ' ',    # non-breaking space
        '\u2009': ' ',    # thin space
        '\u200b': '',     # zero-width space
    }

    # Fields that follow the title formatting rules (dashes used as separators -> colons)
    _TITLE_FIELDS = {'Title', 'entity.title'}

    def _clean_text(self, text: str, title: bool = False) -> str:
        """
        Normalise typographic characters to plain ones and trim whitespace.

        For titles only, en dashes between digits become hyphens
        ("2008\u201309" -> "2008-09") and other en and em dashes become colons,
        matching the title rules. Dashes in other fields are left as they are.

        Args:
            text (str): The text to clean
            title (bool): Apply the title dash rules

        Returns:
            str: Cleaned text
        """
        if not text:
            return ""

        cleaned = text
        for old, new in self._REPLACEMENTS.items():
            cleaned = cleaned.replace(old, new)
        if title:
            cleaned = re.sub(r'(?<=\d)\s*\u2013\s*(?=\d)', '-', cleaned)
            cleaned = re.sub(r'\s*[\u2013\u2014]\s*', ': ', cleaned)
            # Tidy spacing around colons ("A : B" / "A:  B" -> "A: B")
            cleaned = re.sub(r'\s+:', ':', cleaned)
            cleaned = re.sub(r':\s{2,}', ': ', cleaned)

        return cleaned.strip()

    def _clean_value(self, value: Any, title: bool = False) -> Any:
        """Clean a string, or each string in a list; leave other types unchanged."""
        if isinstance(value, str):
            return self._clean_text(value, title)
        if isinstance(value, list):
            return [self._clean_text(v, title) if isinstance(v, str) else v for v in value]
        return value

    def _parse_metadata(self, metadata_str: str) -> Dict[str, Any]:
        """
        Parse the metadata JSON string into a dictionary.

        Args:
            metadata_str (str): The metadata JSON string from OpenAI

        Returns:
            Dict[str, Any]: Dictionary of metadata fields and values

        Raises:
            ValueError: If the JSON is invalid
        """
        try:
            # Parse JSON string into dictionary
            metadata_dict = json.loads(metadata_str)
            
            # Clean all text values and validate subjects
            cleaned_dict = {}
            for key, value in metadata_dict.items():
                if key in self._reserved_fields:
                    empty = [] if isinstance(value, list) else ""
                    if value not in ("", [], None):
                        print(f"  {key} is a reserved field; discarded the AI's value")
                    cleaned_dict[key] = empty
                elif key == 'Subject' and isinstance(value, list):
                    validated = validate_subjects(value, self._valid_topics, self._subject_max)
                    if len(validated) < len(value):
                        print(f"  Subject validation: reduced from {len(value)} to {len(validated)} item(s)")
                    if self._topic_order:
                        validated = sorted(validated, key=lambda t: self._topic_order.get(t, len(self._topic_order)))
                    cleaned_dict[key] = validated
                else:
                    cleaned_dict[key] = self._clean_value(value, title=key in self._TITLE_FIELDS)

            # Guarantee the AI marker on descriptions
            for key in ('Description', 'entity.description'):
                text = cleaned_dict.get(key)
                if isinstance(text, str) and text and self._description_suffix \
                        and not text.endswith(self._description_suffix):
                    if text[-1] not in '.?!':
                        text += '.'
                    cleaned_dict[key] = f"{text} {self._description_suffix}"
                    print(f"  {key}: added missing '{self._description_suffix}'")
            
            return cleaned_dict

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing metadata: {str(e)}")

    def write_metadata(self, metadata_str: str, pdf_path: str, original_format: str = None,
                       model: str = None, overrides: Dict[str, Any] = None,
                       source_format: str = None) -> None:
        """
        Write metadata to JSON file, appending a new record.

        Args:
            metadata_str (str): The metadata JSON string from OpenAI
            pdf_path (str): Path to the source PDF file
            original_format (str): Original file format if the file was converted (e.g., 'docx', 'txt')
            model (str): The model that produced the metadata, recorded for provenance
            overrides (dict): Fields set by the code whatever the model returned
                (e.g. {"Type": "Moving Image", "Format": "mp4"} for a video described from its subtitles)
            source_format (str): Format of the file actually read, when it differs from
                original_format (e.g. "srt" subtitles for an "mp4" video), recorded for provenance

        Raises:
            ValueError: If the metadata cannot be parsed or is invalid
        """
        try:
            # Parse the metadata
            metadata_dict = self._parse_metadata(metadata_str)
            # Format is the original file's format (e.g. docx, htm), never the model's guess
            if original_format:
                metadata_dict['Format'] = original_format.lower()
            if overrides:
                metadata_dict.update(overrides)

            # Create a complete record with additional metadata
            record = {
                "asset_id": os.path.basename(pdf_path),
                "file_path": pdf_path,
                "original_format": original_format or "pdf",
                "extracted_at": datetime.now().isoformat(),
                **({"model": model} if model else {}),
                **({"source_format": source_format} if source_format else {}),
                "metadata": metadata_dict
            }

            with self._lock:
                # Read existing data
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Add new record
                data["metadata"].append(record)
                data["last_updated"] = datetime.now().isoformat()
                data["total_records"] = len(data["metadata"])

                # Write back to file
                self._write_atomic(data)

            print(f"Metadata written to JSON for: {pdf_path}")

        except Exception as e:
            print(f"Error writing metadata for {pdf_path}: {str(e)}")
            raise

    def get_records(self) -> List[Dict[str, Any]]:
        """
        Get all metadata records from the JSON file.

        Returns:
            List[Dict[str, Any]]: List of all metadata records
        """
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("metadata", [])
        except Exception as e:
            print(f"Error reading JSON file: {str(e)}")
            return []

    def get_record_count(self) -> int:
        """
        Get the total number of records in the JSON file.

        Returns:
            int: Number of records
        """
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("total_records", 0)
        except Exception as e:
            print(f"Error reading JSON file: {str(e)}")
            return 0

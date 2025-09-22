"""
Module for writing metadata to JSON files in real-time.
"""

import json
import os
from typing import Dict, List, Any
from datetime import datetime


class JSONMetadataWriter:
    def __init__(self, json_file: str) -> None:
        """
        Initialize the JSON metadata writer.

        Args:
            json_file (str): Path to the JSON file to write to
        """
        self.json_file = json_file
        self._initialize_json()

    def _initialize_json(self) -> None:
        """Create JSON file with initial structure if it doesn't exist."""
        if not os.path.exists(self.json_file):
            initial_data = {
                "metadata": [],
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_records": 0
            }
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)

    def _clean_text(self, text: str) -> str:
        """
        Clean text to remove problematic characters and ensure consistent formatting.
        
        Args:
            text (str): The text to clean
            
        Returns:
            str: Cleaned text
        """
        if not text:
            return ""
        
        # Replace problematic Unicode characters with ASCII equivalents
        replacements = {
            '—': ':',  # em-dash to colon
            '–': ':',  # en-dash to colon
            '"': '"',  # smart quotes to straight quotes
            '"': '"',
            ''': "'",  # smart apostrophes to straight apostrophes
            ''': "'",
            '…': '...',  # ellipsis to three dots
            'â€"': ':',  # common encoding issue
            'â€"': ':',  # common encoding issue
        }
        
        cleaned = text
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        
        # Remove any other non-ASCII characters that might cause issues
        cleaned = ''.join(char for char in cleaned if ord(char) < 128 or char in ';:,.-()')
        
        return cleaned.strip()

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
            
            # Clean all text values
            cleaned_dict = {}
            for key, value in metadata_dict.items():
                if isinstance(value, str):
                    cleaned_dict[key] = self._clean_text(value)
                else:
                    cleaned_dict[key] = value
            
            return cleaned_dict

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing metadata: {str(e)}")

    def write_metadata(self, metadata_str: str, pdf_path: str, original_format: str = None) -> None:
        """
        Write metadata to JSON file, appending a new record.

        Args:
            metadata_str (str): The metadata JSON string from OpenAI
            pdf_path (str): Path to the source PDF file
            original_format (str): Original file format if the file was converted (e.g., 'docx', 'txt')

        Raises:
            ValueError: If the metadata cannot be parsed or is invalid
        """
        try:
            # Parse the metadata
            metadata_dict = self._parse_metadata(metadata_str)

            # Create a complete record with additional metadata
            record = {
                "asset_id": os.path.basename(pdf_path),
                "file_path": pdf_path,
                "original_format": original_format or "pdf",
                "extracted_at": datetime.now().isoformat(),
                "metadata": metadata_dict
            }

            # Read existing data
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Add new record
            data["metadata"].append(record)
            data["last_updated"] = datetime.now().isoformat()
            data["total_records"] = len(data["metadata"])

            # Write back to file
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

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

"""
Module for writing metadata to CSV files.
"""

import csv
import json
import os
from typing import Dict, List


class MetadataWriter:
    def __init__(self, csv_file: str) -> None:
        """
        Initialize the metadata writer.

        Args:
            csv_file (str): Path to the CSV file to write to
        """
        # Define the expected metadata fields in order, with filename first
        self.fields: List[str] = [
            'filename/reference',  # Changed from 'filename'
            'entity.title',
            'entity.description',
            'icaew:ContentType',
            'icaew:InternalReference',
            'icaew:Notes',
            'Title',
            'Creator',
            'Subject',
            'Description',
            'Publisher',
            'Contributor',
            'Date',
            'Type',
            'Format',
            'Identifier',
            'Source',
            'Language',
            'Relation',
            'Coverage',
            'Rights'
        ]
        self.csv_file = csv_file
        self._initialize_csv()

    def _initialize_csv(self) -> None:
        """Create CSV file with headers if it doesn't exist."""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.fields)
                writer.writeheader()

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

    def _parse_metadata(self, metadata_str: str) -> Dict[str, str]:
        """
        Parse the metadata JSON string into a dictionary.

        Args:
            metadata_str (str): The metadata JSON string from OpenAI

        Returns:
            Dict[str, str]: Dictionary of metadata fields and values

        Raises:
            ValueError: If the JSON is invalid
        """
        try:
            # Parse JSON string into dictionary
            metadata_dict = json.loads(metadata_str)
            
            # Initialize all fields with empty values
            result = {field: '' for field in self.fields}
            
            # Map JSON data to our expected fields
            for field, value in metadata_dict.items():
                if field in self.fields:
                    # Convert any non-string values to strings and clean them
                    result[field] = self._clean_text(str(value) if value is not None else '')
            
            # Apply the mapping rules:
            # 1. entity.title should be a copy of Title
            result['entity.title'] = result.get('Title', '')
            
            # 2. entity.description should be a copy of Description
            result['entity.description'] = result.get('Description', '')
            
            # 3. icaew:InternalReference should use the AI-generated value
            # (no special mapping needed - it should already be properly formatted)
            
            return result

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing metadata: {str(e)}")

    def write_metadata(self, metadata_str: str, pdf_path: str, original_format: str = None) -> None:
        """
        Write metadata to CSV file, appending a new row.

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

            # Add filename/reference as first column
            metadata_dict['filename/reference'] = os.path.basename(pdf_path)

            # Override the Format field with the original format if available
            if original_format:
                metadata_dict['Format'] = original_format.lower()

            # Append to CSV
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.fields)
                writer.writerow(metadata_dict)

            print(f"Metadata written to CSV for: {pdf_path}")

        except Exception as e:
            print(f"Error writing metadata for {pdf_path}: {str(e)}")
            raise

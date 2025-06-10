"""
Module for writing metadata to CSV files.
"""

import csv
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
            'filename',  # Added filename as first field
            'entity.title',
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

    def _parse_metadata(self, metadata_str: str) -> Dict[str, str]:
        """
        Parse the metadata string into a dictionary.

        Args:
            metadata_str (str): The metadata string from OpenAI

        Returns:
            Dict[str, str]: Dictionary of metadata fields and values
        """
        metadata_dict = {
            field: '' for field in self.fields}  # Initialize with empty values

        # Split the input string into lines and process each line
        for line in metadata_str.strip().split('\n'):
            line = line.strip()
            if not line or not line.startswith('- '):
                continue

            # Remove the leading dash and space
            line = line[2:].strip()

            # Split on the first colon
            if ':' in line:
                field, value = line.split(':', 1)
                field = field.strip()
                value = value.strip()

                # Store in dictionary if it's a known field
                if field in self.fields:
                    metadata_dict[field] = value

        return metadata_dict

    def write_metadata(self, metadata_str: str, pdf_path: str) -> None:
        """
        Write metadata to CSV file, appending a new row.

        Args:
            metadata_str (str): The metadata string from OpenAI
            pdf_path (str): Path to the source PDF file
        """
        # Parse the metadata
        metadata_dict = self._parse_metadata(metadata_str)

        # Add filename as first column
        metadata_dict['filename'] = os.path.basename(pdf_path)

        # Append to CSV
        with open(self.csv_file, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fields)
            writer.writerow(metadata_dict)

        print(f"Metadata written to CSV for: {pdf_path}")

"""
Utility module for converting JSON metadata files to CSV format.
"""

import csv
import json
import os
from typing import Dict, List, Any, Optional


class JSONToCSVConverter:
    def __init__(self) -> None:
        """Initialize the JSON to CSV converter."""
        # Define the base metadata fields (without numbered suffixes)
        self.base_fields: List[str] = [
            'assetId',
            'entity.title',
            'entity.description',
            'icaew:ContentType',
            'icaew:InternalReference',
            'icaew:Notes',
            'dc:title',
            'dc:creator',
            'dc:subject',
            'dc:description',
            'dc:publisher',
            'dc:contributor',
            'dc:date',
            'dc:type',
            'dc:format',
            'dc:identifier',
            'dc:source',
            'dc:language',
            'dc:relation',
            'dc:coverage',
            'dc:rights'
        ]
        
        # This will be populated dynamically based on the data
        self.dynamic_fields: List[str] = []
        self.field_max_counts: Dict[str, int] = {}

    def _analyze_json_data(self, records: List[Dict[str, Any]]) -> None:
        """
        Analyze JSON records to determine the maximum number of values for each field.
        
        Args:
            records: List of metadata records from JSON
        """
        self.field_max_counts = {}
        
        # Initialize all base fields with count 1
        for field in self.base_fields:
            self.field_max_counts[field] = 1
        
        # Analyze each record to find maximum array sizes
        for record in records:
            metadata = record.get("metadata", {})
            
            # Map old field names to new dc: field names
            field_map = {
                'Title': 'dc:title',
                'Creator': 'dc:creator',
                'Subject': 'dc:subject',
                'Description': 'dc:description',
                'Publisher': 'dc:publisher',
                'Contributor': 'dc:contributor',
                'Date': 'dc:date',
                'Type': 'dc:type',
                'Format': 'dc:format',
                'Identifier': 'dc:identifier',
                'Source': 'dc:source',
                'Language': 'dc:language',
                'Relation': 'dc:relation',
                'Coverage': 'dc:coverage',
                'Rights': 'dc:rights'
            }
            
            for field, value in metadata.items():
                mapped_field = field_map.get(field, field)
                if mapped_field in self.base_fields:
                    if isinstance(value, list):
                        # Update max count for this field
                        current_max = self.field_max_counts.get(mapped_field, 1)
                        self.field_max_counts[mapped_field] = max(current_max, len(value))
                    else:
                        # Ensure at least 1 column for non-array fields
                        self.field_max_counts[mapped_field] = max(self.field_max_counts.get(mapped_field, 1), 1)
        
        # Create dynamic field list
        self.dynamic_fields = []
        for field in self.base_fields:
            max_count = self.field_max_counts.get(field, 1)
            if max_count == 1:
                # Single column
                self.dynamic_fields.append(field)
            else:
                # Multiple columns with clean repetition (no numbers)
                for i in range(max_count):
                    self.dynamic_fields.append(field)
    
    def _get_field_value(self, metadata_dict: Dict[str, Any], field_name: str, index: int = 0) -> str:
        """
        Get a specific value from a field, handling both arrays and single values.
        
        Args:
            metadata_dict: The metadata dictionary
            field_name: The field name (e.g., 'dc:creator')
            index: The index for array fields (0-based)
            
        Returns:
            str: The value at the specified index, or empty string if not found
        """
        # Map old field names to new dc: field names
        field_map = {
            'Title': 'dc:title',
            'Creator': 'dc:creator',
            'Subject': 'dc:subject',
            'Description': 'dc:description',
            'Publisher': 'dc:publisher',
            'Contributor': 'dc:contributor',
            'Date': 'dc:date',
            'Type': 'dc:type',
            'Format': 'dc:format',
            'Identifier': 'dc:identifier',
            'Source': 'dc:source',
            'Language': 'dc:language',
            'Relation': 'dc:relation',
            'Coverage': 'dc:coverage',
            'Rights': 'dc:rights'
        }
        
        # Find the original field name
        original_field = None
        for orig, mapped in field_map.items():
            if mapped == field_name:
                original_field = orig
                break
        
        if not original_field:
            # If not found in field_map, try the field_name directly
            # This handles fields like icaew:ContentType that already have correct names
            original_field = field_name
        
        value = metadata_dict.get(original_field)
        if value is None:
            return ''
        
        if isinstance(value, list):
            if index < len(value):
                return str(value[index])
            else:
                return ''
        else:
            if index == 0:
                return str(value)
            else:
                return ''

    def _map_metadata_fields(self, metadata_dict: Dict[str, Any]) -> Dict[str, str]:
        """
        Map metadata fields from JSON to CSV format using dynamic columns.

        Args:
            metadata_dict (Dict[str, Any]): The metadata dictionary from JSON

        Returns:
            Dict[str, str]: Mapped fields for CSV output with dynamic columns
        """
        # Initialize all dynamic fields with empty values
        result = {field: '' for field in self.dynamic_fields}

        # Set assetId (this will be set separately)
        result['assetId'] = ''

        # Map each dynamic field
        for i, field in enumerate(self.dynamic_fields):
            if field == 'assetId':
                continue  # Skip assetId, it's set separately
            
            # For clean column names, we need to determine the index based on position
            # Count how many times this field appears before the current position
            field_index = 0
            for j in range(i):
                if self.dynamic_fields[j] == field:
                    field_index += 1
            
            # Get the value for this field/index
            result[field] = self._get_field_value(metadata_dict, field, field_index)

        # Apply special mapping rules for entity fields
        # 1. entity.title should be a copy of dc:title (from Title)
        if 'entity.title' in result:
            result['entity.title'] = result.get('dc:title', '')
        
        # 2. entity.description should be a copy of dc:description (from Description)
        if 'entity.description' in result:
            result['entity.description'] = result.get('dc:description', '')

        return result

    def _write_csv_with_duplicate_headers(self, csv_file: str, records: List[Dict[str, Any]], 
                                        original_format_override: Optional[str] = None) -> None:
        """
        Write CSV file with duplicate column headers (clean repetition without numbers).
        
        Args:
            csv_file: Path to the output CSV file
            records: List of metadata records
            original_format_override: Override format for all records
        """
        with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            # Write header row manually
            csvfile.write(','.join(self.dynamic_fields) + '\n')
            
            # Process each record
            for record in records:
                try:
                    # Get metadata dictionary
                    metadata_dict = record.get("metadata", {})
                    
                    # Map fields for CSV using dynamic columns
                    csv_row = self._map_metadata_fields(metadata_dict)
                    
                    # Set assetId
                    csv_row['assetId'] = record.get("asset_id", "")
                    
                    # Override format if specified
                    if original_format_override:
                        # Find all format columns and set them
                        for field in self.dynamic_fields:
                            if field.startswith('dc:format'):
                                csv_row[field] = original_format_override.lower()
                    else:
                        # Use the original format from the record
                        original_format = record.get("original_format", "pdf")
                        for field in self.dynamic_fields:
                            if field.startswith('dc:format'):
                                csv_row[field] = original_format.lower()

                    # Write row manually with position-based data
                    row_values = []
                    for i, field in enumerate(self.dynamic_fields):
                        # Handle assetId specially since it's not in metadata_dict
                        if field == 'assetId':
                            value = csv_row.get('assetId', '')
                        else:
                            # Calculate the field index based on position
                            field_index = 0
                            for j in range(i):
                                if self.dynamic_fields[j] == field:
                                    field_index += 1
                            
                            # Get the value for this field/index
                            value = self._get_field_value(metadata_dict, field, field_index)
                        
                        # Escape CSV values
                        if ',' in str(value) or '"' in str(value) or '\n' in str(value):
                            escaped_value = str(value).replace('"', '""')
                            value = f'"{escaped_value}"'
                        row_values.append(str(value))
                    
                    csvfile.write(','.join(row_values) + '\n')

                except Exception as e:
                    print(f"Error processing record {record.get('asset_id', 'unknown')}: {str(e)}")
                    continue

    def convert_json_to_csv(self, json_file: str, csv_file: str, 
                          original_format_override: Optional[str] = None) -> None:
        """
        Convert JSON metadata file to CSV format with dynamic columns.

        Args:
            json_file (str): Path to the JSON metadata file
            csv_file (str): Path to the output CSV file
            original_format_override (str, optional): Override format for all records
        """
        try:
            # Read JSON data
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            records = data.get("metadata", [])
            if not records:
                print("No metadata records found in JSON file")
                return

            print(f"Converting {len(records)} records from JSON to CSV")

            # Analyze the data to determine dynamic columns
            print("Analyzing data to determine column structure...")
            self._analyze_json_data(records)
            
            print(f"Dynamic columns created: {len(self.dynamic_fields)}")
            print(f"Field max counts: {self.field_max_counts}")

            # Use custom CSV writer to handle duplicate headers
            self._write_csv_with_duplicate_headers(csv_file, records, original_format_override)

            print(f"Successfully converted JSON to CSV with dynamic columns: {csv_file}")

        except Exception as e:
            print(f"Error converting JSON to CSV: {str(e)}")
            raise

    def get_json_summary(self, json_file: str) -> Dict[str, Any]:
        """
        Get a summary of the JSON metadata file.

        Args:
            json_file (str): Path to the JSON metadata file

        Returns:
            Dict[str, Any]: Summary information
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            records = data.get("metadata", [])
            
            # Count formats
            format_counts = {}
            for record in records:
                fmt = record.get("original_format", "unknown")
                format_counts[fmt] = format_counts.get(fmt, 0) + 1

            summary = {
                "total_records": len(records),
                "created_at": data.get("created_at"),
                "last_updated": data.get("last_updated"),
                "format_counts": format_counts,
                "file_size": os.path.getsize(json_file)
            }

            return summary

        except Exception as e:
            print(f"Error reading JSON file: {str(e)}")
            return {}


def main():
    """Command line interface for JSON to CSV conversion."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert JSON metadata file to CSV format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Convert JSON to CSV:
  python json_to_csv_converter.py metadata.json output.csv
  
  # Convert with format override:
  python json_to_csv_converter.py metadata.json output.csv --format docx
  
  # Get JSON file summary:
  python json_to_csv_converter.py metadata.json --summary
        '''
    )

    parser.add_argument('json_file', help='Path to the JSON metadata file')
    parser.add_argument('csv_file', nargs='?', help='Path to the output CSV file')
    parser.add_argument('--format', help='Override format for all records')
    parser.add_argument('--summary', action='store_true', help='Show JSON file summary only')

    args = parser.parse_args()

    converter = JSONToCSVConverter()

    if args.summary:
        summary = converter.get_json_summary(args.json_file)
        print("JSON File Summary:")
        print(f"  Total records: {summary.get('total_records', 0)}")
        print(f"  Created at: {summary.get('created_at', 'Unknown')}")
        print(f"  Last updated: {summary.get('last_updated', 'Unknown')}")
        print(f"  File size: {summary.get('file_size', 0)} bytes")
        
        format_counts = summary.get('format_counts', {})
        if format_counts:
            print("  Format distribution:")
            for fmt, count in format_counts.items():
                print(f"    {fmt}: {count}")
    else:
        if not args.csv_file:
            print("Error: CSV output file is required when not using --summary")
            return

        converter.convert_json_to_csv(args.json_file, args.csv_file, args.format)


if __name__ == '__main__':
    main()

"""
Metadata extraction tool for PDF files using OpenAI's API.
Extracts metadata following configurable conventions defined in config.py.
"""

import argparse
import sys
import os
from typing import List, Optional, Set, Tuple
from metadata_extractor import MetadataExtractor
from json_metadata_writer import JSONMetadataWriter


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description='Extract metadata from PDF files using ICAEW conventions.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Process a single PDF file:
  python main.py --file path/to/document.pdf -j output.json
  # or
  python main.py -f path/to/document.pdf -j output.json

  # Process all PDFs in a directory:
  python main.py --folder path/to/pdf/directory -j output.json
  # or
  python main.py -d path/to/pdf/directory -j output.json

  # Process first 3 pages of all PDFs in a directory:
  python main.py --folder path/to/pdf/directory --first 3 -j output.json
  # or
  python main.py -d path/to/pdf/directory -f 3 -j output.json

  # Process last 2 pages of all PDFs in a directory:
  python main.py --folder path/to/pdf/directory --last 2 -j output.json
  # or
  python main.py -d path/to/pdf/directory -l 2 -j output.json

  # Convert JSON to CSV after processing:
  python json_to_csv_converter.py output.json output.csv
'''
    )

    # Create a mutually exclusive group for file/folder arguments
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--file', '-f',
                             help='Path to a single PDF file to process')
    input_group.add_argument('--folder', '-d',
                             help='Path to a directory containing PDF files to process')

    parser.add_argument('--first', '-p',
                        type=int,
                        default=0,
                        help='Number of pages to include from the start (default: 0, meaning no limit)')
    parser.add_argument('--last', '-l',
                        type=int,
                        default=0,
                        help='Number of pages to include from the end (default: 0, meaning no limit)')
    parser.add_argument('--json-file', '-j',
                        required=True,
                        help='JSON file to write metadata to')

    return parser


def get_pdf_files(file_path: Optional[str] = None, folder_path: Optional[str] = None) -> List[str]:
    """
    Get a list of PDF files from a file path or directory path.

    Args:
        file_path (str, optional): Path to a PDF file
        folder_path (str, optional): Path to a directory

    Returns:
        list: List of paths to PDF files
    """
    if file_path:
        if not file_path.lower().endswith('.pdf'):
            print(f"Warning: {file_path} is not a PDF file")
            return []
        if not os.path.isfile(file_path):
            print(f"Error: {file_path} is not a valid file")
            return []
        return [file_path]

    if folder_path:
        if not os.path.isdir(folder_path):
            print(f"Error: {folder_path} is not a valid directory")
            return []

        pdf_files = []
        for file in os.listdir(folder_path):
            if file.lower().endswith('.pdf'):
                full_path = os.path.join(folder_path, file)
                pdf_files.append(full_path)
                print(f"Found PDF: {file}")  # Debug log
        print(f"\nTotal PDFs found in directory: {len(pdf_files)}")  # Debug log
        return pdf_files

    return []


def main() -> None:
    """Main entry point for the metadata extraction tool."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Get list of PDF files to process
        pdf_files = get_pdf_files(args.file, args.folder)
        if not pdf_files:
            print("No PDF files found to process")
            sys.exit(1)

        total_files = len(pdf_files)
        print(f"\nStarting to process {total_files} PDF file(s)")

        # Initialize metadata extractor and writer
        extractor = MetadataExtractor()
        writer = JSONMetadataWriter(args.json_file)

        # Track processed and failed files
        processed_files: Set[str] = set()
        failed_files: List[Tuple[str, str]] = []  # List of (file_path, error_message) tuples

        # Process each PDF file
        for index, pdf_path in enumerate(pdf_files, 1):
            try:
                # Skip if already processed
                if pdf_path in processed_files:
                    print(f"\n[{index}/{total_files}] Skipping already processed file: {pdf_path}")
                    continue

                print(f"\n[{index}/{total_files}] Processing: {pdf_path}")
                
                # Determine original format by checking if this was a converted file
                original_format = None
                
                # First, try to read from format mapping file (created by convert_documents.py)
                mapping_file = os.path.join(os.path.dirname(pdf_path), "format_mapping.json")
                if os.path.exists(mapping_file):
                    try:
                        import json
                        with open(mapping_file, 'r') as f:
                            format_mapping = json.load(f)
                        if pdf_path in format_mapping:
                            original_format = format_mapping[pdf_path]
                            print(f"Detected original format from mapping: {original_format}")
                    except Exception as e:
                        print(f"Warning: Could not read format mapping: {e}")
                
                # Fallback: Check for common original formats that might have been converted
                if not original_format:
                    base_name = os.path.splitext(pdf_path)[0]
                    supported_formats = ['.docx', '.doc', '.xlsx', '.pptx', '.ppt', '.txt', '.srt', '.vtt', '.jpg', '.jpeg', '.png', '.tiff', '.tif']
                    for ext in supported_formats:
                        original_file = base_name + ext
                        if os.path.exists(original_file):
                            original_format = ext[1:]  # Remove the dot
                            print(f"Detected original format: {original_format}")
                            break
                
                # If no original format found, assume it's a native PDF
                if not original_format:
                    original_format = 'pdf'
                
                metadata, original_path, detected_format = extractor.extract_metadata(
                    pdf_path, args.first, args.last, original_format)

                # Print metadata to console
                print(f"\n[{index}/{total_files}] Extracted Metadata:")
                print(metadata)

                # Write to JSON using the original path and format
                writer.write_metadata(metadata, original_path, detected_format)
                processed_files.add(pdf_path)
                print(f"[{index}/{total_files}] Successfully processed and added to JSON: {original_path}")

            except Exception as e:
                error_msg = str(e)
                print(f"[{index}/{total_files}] Error processing {pdf_path}: {error_msg}")
                failed_files.append((pdf_path, error_msg))
                continue  # Continue with next file even if one fails

        # Print detailed summary
        print(f"\nProcessing complete:")
        print(f"- Total files found: {total_files}")
        print(f"- Successfully processed: {len(processed_files)}")
        print(f"- Failed to process: {len(failed_files)}")
        print(f"- Metadata written to: {args.json_file}")
        
        if failed_files:
            print("\nFailed files:")
            for file_path, error in failed_files:
                print(f"  - {os.path.basename(file_path)}: {error}")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

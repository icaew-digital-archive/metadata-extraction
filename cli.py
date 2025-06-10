"""
Command-line interface for the metadata extraction tool.
"""

import argparse
import sys
import os
from typing import List, Optional, Set, Tuple
from metadata_extractor import MetadataExtractor
from metadata_writer import MetadataWriter


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description='Extract metadata from PDF files using ICAEW conventions.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Process a single PDF file:
  python main.py --file path/to/document.pdf -c output.csv
  # or
  python main.py -f path/to/document.pdf -c output.csv

  # Process all PDFs in a directory:
  python main.py --folder path/to/pdf/directory -c output.csv
  # or
  python main.py -d path/to/pdf/directory -c output.csv

  # Process first 3 pages of all PDFs in a directory:
  python main.py --folder path/to/pdf/directory --first 3 -c output.csv
  # or
  python main.py -d path/to/pdf/directory -f 3 -c output.csv

  # Process last 2 pages of all PDFs in a directory:
  python main.py --folder path/to/pdf/directory --last 2 -c output.csv
  # or
  python main.py -d path/to/pdf/directory -l 2 -c output.csv
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
    parser.add_argument('--csv-file', '-c',
                        required=True,
                        help='CSV file to write metadata to')

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
    """Main entry point for the CLI."""
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
        writer = MetadataWriter(args.csv_file)

        # Track processed files to avoid duplicates
        processed_files: Set[str] = set()

        # Process each PDF file
        for index, pdf_path in enumerate(pdf_files, 1):
            try:
                # Skip if already processed
                if pdf_path in processed_files:
                    print(f"\n[{index}/{total_files}] Skipping already processed file: {pdf_path}")
                    continue

                print(f"\n[{index}/{total_files}] Processing: {pdf_path}")
                metadata, original_path = extractor.extract_metadata(
                    pdf_path, args.first, args.last)

                # Print metadata to console
                print(f"\n[{index}/{total_files}] Extracted Metadata:")
                print(metadata)

                # Write to CSV using the original path
                writer.write_metadata(metadata, original_path)
                processed_files.add(pdf_path)
                print(f"[{index}/{total_files}] Successfully processed and added to CSV: {original_path}")

            except Exception as e:
                print(f"[{index}/{total_files}] Error processing {pdf_path}: {str(e)}")
                continue  # Continue with next file even if one fails

        print(f"\nProcessing complete:")
        print(f"- Total files found: {total_files}")
        print(f"- Successfully processed: {len(processed_files)}")
        print(f"- Failed to process: {total_files - len(processed_files)}")
        print(f"- Metadata written to: {args.csv_file}")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Metadata extraction wrapper script that downloads assets from Preservica and then extracts metadata from the downloaded files.

This wrapper script:
1. Downloads assets from Preservica using download_preservica_assets.py
2. Converts any DOCX/DOC/XLSX/PPTX/PPT/TXT/SRT/VTT/image files to PDF using convert_documents.py
3. Extracts metadata from the PDF files using main.py
4. Handles the workflow between the scripts

To use this script, edit the configuration variables at the top of the file or use CLI arguments.
Script paths can be configured via environment variables or .env file.
"""

from pathlib import Path
import argparse
import sys
import subprocess
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# ===== CONFIGURATION FROM ENVIRONMENT VARIABLES =====
# Script paths - read from environment variables with fallbacks
#
# To configure script paths, add these to your .env file:
# PYPRESERVICA_DOWNLOAD_SCRIPT="/path/to/download_preservica_assets.py"
# METADATA_EXTRACTION_SCRIPT="/path/to/main.py"
# CONVERT_DOCUMENTS_SCRIPT="/path/to/convert_documents.py"
#
# Or set them as environment variables:
# export PYPRESERVICA_DOWNLOAD_SCRIPT="/path/to/download_preservica_assets.py"
# export METADATA_EXTRACTION_SCRIPT="/path/to/main.py"
# export CONVERT_DOCUMENTS_SCRIPT="/path/to/convert_documents.py"

# Download script path
DOWNLOAD_SCRIPT = os.getenv(
    'PYPRESERVICA_DOWNLOAD_SCRIPT',
    "fallback_path_here"
)

# Convert script path (relative to current directory by default)
CONVERT_SCRIPT = os.getenv(
    'CONVERT_DOCUMENTS_SCRIPT',
    "fallback_path_here"
)

# Metadata extraction script path
EXTRACTION_SCRIPT = os.getenv(
    'METADATA_EXTRACTION_SCRIPT',
    "fallback_path_here"
)

# ===== HARDCODED CONFIGURATION =====
# Change these variables as needed

# Download configuration
FOLDER_ID = ""  # Change this to your folder ID (can be overridden via CLI)
# FOLDERS_FILE = "folders.txt"  # Uncomment to use multiple folders
# ASSET_ID = "cc56e888-8d18-5582-0d41-65c168d611ee"  # Uncomment to use single asset
# ASSETS_FILE = "assets.txt"  # Uncomment to use multiple assets

# Output configuration
WORKING_DIR = "./downloads"  # Directory where assets are downloaded and processed
JSON_OUTPUT = "ai.json"  # JSON file to write extracted metadata to
CSV_OUTPUT = "ai.csv"  # CSV file to write extracted metadata to (converted from JSON)

# Optional settings
USE_ASSET_REF = True  # Set to True to use asset reference numbers in filenames
# Set to True to download only original (first generation) files
ORIGINAL_ONLY = True
FIRST_PAGES = 6  # Number of pages to include from the start (0 = no limit)
LAST_PAGES = 4   # Number of pages to include from the end (0 = no limit)
# ===================================


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Metadata extraction wrapper script for Preservica assets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full workflow with Preservica download (folder):
  python metadata_extraction_wrapper.py
  python metadata_extraction_wrapper.py --preservica-folder-ref 12345678-1234-1234-1234-123456789abc
  python metadata_extraction_wrapper.py --preservica-folder-ref 0a5d69bc-d85b-4482-a45c-8b20c40ef1ba --output-dir ./my-downloads --json-file my_metadata.json --csv-file my_metadata.csv
  python metadata_extraction_wrapper.py --preservica-folder-ref 0a5d69bc-d85b-4482-a45c-8b20c40ef1ba --exclude-extensions mp4 avi mov --output-dir ./my-downloads

  # Download a single asset by ID:
  python metadata_extraction_wrapper.py --preservica-asset-ref cc56e888-8d18-5582-0d41-65c168d611ee --output-dir ./my-downloads

  # Download multiple specific assets from a text file (one UUID per line):
  python metadata_extraction_wrapper.py --preservica-assets-file assets.txt --output-dir ./my-downloads

  # Work with existing files (skip download):
  python metadata_extraction_wrapper.py --skip-download --output-dir ./existing-files
  python metadata_extraction_wrapper.py --skip-download --output-dir ./existing-files --json-file my_metadata.json --csv-file my_metadata.csv

  # With custom context for the extraction prompt:
  python metadata_extraction_wrapper.py --skip-download --output-dir ./my-downloads --context-prompt "What follows is a series of photos showing Chartered Accountant's Hall"

  # Disable subject classification (Subject field will be empty):
  python metadata_extraction_wrapper.py --skip-download --output-dir ./my-downloads --no-subjects
        """
    )

    parser.add_argument(
        '--preservica-folder-ref',
        type=str,
        help='Preservica folder UUID to download (overrides hardcoded FOLDER_ID)'
    )

    parser.add_argument(
        '--preservica-asset-ref',
        type=str,
        help='Single Preservica asset UUID to download'
    )

    parser.add_argument(
        '--preservica-assets-file',
        type=str,
        help='Path to a text file containing Preservica asset UUIDs, one per line'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        help='Working directory for downloads and processing (overrides hardcoded WORKING_DIR)'
    )

    parser.add_argument(
        '--json-file',
        type=str,
        help='JSON output filename (overrides hardcoded JSON_OUTPUT)'
    )

    parser.add_argument(
        '--csv-file',
        type=str,
        help='CSV output filename (overrides hardcoded CSV_OUTPUT)'
    )

    parser.add_argument(
        '--skip-download',
        action='store_true',
        help='Skip Preservica download step and work with existing files in output directory'
    )

    parser.add_argument(
        '--exclude-extensions',
        nargs='+',
        default=None,
        help='File extensions to exclude from download (passed through to download_preservica_assets.py). Example: --exclude-extensions mp4 avi mov'
    )

    parser.add_argument(
        '--context-prompt',
        type=str,
        default=None,
        help='Custom context to prepend to the extraction prompt (e.g. "What follows is a series of photos showing Chartered Accountant\'s Hall")'
    )

    parser.add_argument(
        '--no-subjects',
        action='store_true',
        help='Disable subject classification (Subject field will always be empty)'
    )

    return parser.parse_args()


def run_command(cmd, description):
    """Run a command and return True if successful, False otherwise."""
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True)
        print(f"Successfully completed: {description}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to run: {description}")
        print(f"Return code: {e.returncode}")
        return False
    except Exception as e:
        print(f"Unexpected error running {description}: {e}")
        return False


def check_downloaded_files(download_dir):
    """Check if there are any files in the download directory."""
    if not download_dir.exists():
        print(f"Download directory does not exist: {download_dir}")
        return False

    files = list(download_dir.glob('*'))
    if not files:
        print(f"No files found in download directory: {download_dir}")
        return False

    print(f"Found {len(files)} files in download directory")
    return True


def display_configuration():
    """Display the current configuration being used."""
    print("=== Configuration ===")
    print(f"Download script: {DOWNLOAD_SCRIPT}")
    print(f"Convert script: {CONVERT_SCRIPT}")
    print(f"Extraction script: {EXTRACTION_SCRIPT}")
    print(
        f"Folder ID: {FOLDER_ID if FOLDER_ID else 'Not set (use --preservica-folder-ref)'}")
    print(f"Output directory: {WORKING_DIR}")
    print(f"JSON output: {JSON_OUTPUT}")
    print(f"CSV output: {CSV_OUTPUT}")
    print(f"Use asset ref: {USE_ASSET_REF}")
    print(f"Original only: {ORIGINAL_ONLY}")
    print(f"First pages: {FIRST_PAGES}")
    print(f"Last pages: {LAST_PAGES}")
    print("==================\n")


def main():
    """Main orchestration function."""

    # Parse command line arguments
    args = parse_arguments()

    print("Starting orchestration process")

    # Display current configuration
    display_configuration()

    # Use CLI arguments if provided, otherwise fall back to hardcoded values
    folder_id = args.preservica_folder_ref if args.preservica_folder_ref else FOLDER_ID
    asset_ref = args.preservica_asset_ref if args.preservica_asset_ref else None
    assets_file = args.preservica_assets_file if args.preservica_assets_file else None
    output_dir = Path(args.output_dir) if args.output_dir else Path(WORKING_DIR)
    json_output = Path(args.json_file) if args.json_file else Path(JSON_OUTPUT)
    csv_output = Path(args.csv_file) if args.csv_file else Path(CSV_OUTPUT)
    skip_download = args.skip_download
    exclude_extensions = args.exclude_extensions

    if folder_id:
        print(f"Using folder ID: {folder_id}")
    elif asset_ref:
        print(f"Using asset ref: {asset_ref}")
    elif assets_file:
        print(f"Using assets file: {assets_file}")
    print(f"Output directory: {output_dir}")
    print(f"JSON output: {json_output}")
    print(f"CSV output: {csv_output}")
    print(f"Skip download: {skip_download}")
    if exclude_extensions:
        print(f"Exclude extensions: {', '.join(exclude_extensions)}")
    context_prompt = args.context_prompt if args.context_prompt else None
    if context_prompt:
        print(f"Context prompt: {context_prompt[:60]}..." if len(context_prompt) > 60 else f"Context prompt: {context_prompt}")
    no_subjects = args.no_subjects
    print(f"Subject classification: {'disabled' if no_subjects else 'enabled'}")

    # Step 1: Run the download script (unless skipped)
    if not skip_download:
        print("\nStep 1: Downloading assets from Preservica")

        download_cmd = [sys.executable, DOWNLOAD_SCRIPT]

        # Add the appropriate download source argument
        if folder_id:
            download_cmd.extend(['--folder', folder_id])
        elif asset_ref:
            download_cmd.extend(['--asset', asset_ref])
        elif assets_file:
            download_cmd.extend(['--assets-file', assets_file])
        elif 'FOLDERS_FILE' in globals() and FOLDERS_FILE:
            download_cmd.extend(['--folders-file', FOLDERS_FILE])
        elif 'ASSET_ID' in globals() and ASSET_ID:
            download_cmd.extend(['--asset', ASSET_ID])
        elif 'ASSETS_FILE' in globals() and ASSETS_FILE:
            download_cmd.extend(['--assets-file', ASSETS_FILE])
        else:
            print("Error: No download source specified. Provide --preservica-folder-ref, --preservica-asset-ref, or --preservica-assets-file.")
            sys.exit(1)

        if exclude_extensions:
            download_cmd.extend(['--exclude-extensions', *exclude_extensions])

        # Add optional arguments
        if USE_ASSET_REF:
            download_cmd.append('--use-asset-ref')

        if ORIGINAL_ONLY:
            download_cmd.append('--original-only')

        # Add output directory (positional) last
        if exclude_extensions:
            # download_preservica_assets.py uses nargs='+', so without '--' it will
            # consume the positional download_folder as another extension value.
            download_cmd.append('--')
        download_cmd.append(str(output_dir))

        if not run_command(download_cmd, "Preservica asset download"):
            print("Download step failed. Stopping orchestration.")
            sys.exit(1)
    else:
        print("\nStep 1: Skipping Preservica download (using existing files)")

    # Step 2: Check if files are available for processing
    print("\nStep 2: Verifying files are available for processing")
    if not check_downloaded_files(output_dir):
        print("No files found in working directory. Stopping orchestration.")
        sys.exit(1)

    # Step 3: Convert any DOCX/DOC files to PDF
    print("\nStep 3: Converting documents to PDF format")

    convert_cmd = [sys.executable, CONVERT_SCRIPT, str(output_dir)]

    if not run_command(convert_cmd, "Document conversion"):
        print("Document conversion step failed.")
        sys.exit(1)

    # Step 4: Run the metadata extraction script (main.py now writes to JSON)
    print("\nStep 4: Extracting metadata from PDF files")

    extract_cmd = [sys.executable, EXTRACTION_SCRIPT, '--folder',
                   str(output_dir), '--json-file', str(json_output)]

    # Add optional page limit arguments
    if FIRST_PAGES > 0:
        extract_cmd.extend(['--first', str(FIRST_PAGES)])
    if LAST_PAGES > 0:
        extract_cmd.extend(['--last', str(LAST_PAGES)])

    # Add optional context prompt
    if context_prompt:
        extract_cmd.extend(['--context-prompt', context_prompt])

    if no_subjects:
        extract_cmd.append('--no-subjects')

    if not run_command(extract_cmd, "Metadata extraction"):
        print("Metadata extraction step failed.")
        sys.exit(1)

    # Step 5: Convert JSON to CSV
    print("\nStep 5: Converting JSON metadata to CSV format")

    convert_json_cmd = [sys.executable, 'json_to_csv_converter.py', str(json_output), str(csv_output)]

    if not run_command(convert_json_cmd, "JSON to CSV conversion"):
        print("JSON to CSV conversion step failed.")
        sys.exit(1)

    # Success
    print(f"\nOrchestration completed successfully!")
    print(f"Downloaded files: {output_dir}")
    print(f"JSON metadata: {json_output}")
    print(f"CSV metadata: {csv_output}")


if __name__ == "__main__":
    main()

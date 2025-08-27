#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Metadata extraction wrapper script that downloads assets from Preservica and then extracts metadata from the downloaded files.

This wrapper script:
1. Downloads assets from Preservica using download_preservica_assets.py
2. Converts any DOCX/DOC files to PDF using convert_documents.py
3. Extracts metadata from the PDF files using main.py
4. Handles the workflow between the scripts

To use this script, edit the configuration variables at the top of the file or use CLI arguments.
"""

# ===== HARDCODED CONFIGURATION =====
# Change these variables as needed

# Script paths
DOWNLOAD_SCRIPT = "/home/digital-archivist/Documents/custom scripts/digital-archiving-scripts/pypreservica scripts/download_preservica_assets.py"  # Path to the Preservica download script
CONVERT_SCRIPT = "convert_documents.py"  # Path to the document conversion script
EXTRACTION_SCRIPT = "/home/digital-archivist/Documents/custom scripts/metadata-extraction/main.py"  # Path to the metadata extraction script

# Download configuration
FOLDER_ID = ""  # Change this to your folder ID (can be overridden via CLI)
# FOLDERS_FILE = "folders.txt"  # Uncomment to use multiple folders
# ASSET_ID = "cc56e888-8d18-5582-0d41-65c168d611ee"  # Uncomment to use single asset
# ASSETS_FILE = "assets.txt"  # Uncomment to use multiple assets

# Output configuration
OUTPUT_DIR = "./downloads"  # Directory where downloaded assets will be saved
CSV_OUTPUT = "ai.csv"  # CSV file to write extracted metadata to

# Optional settings
USE_ASSET_REF = True  # Set to True to use asset reference numbers in filenames
ORIGINAL_ONLY = True  # Set to True to download only original (first generation) files
FIRST_PAGES = 6  # Number of pages to include from the start (0 = no limit)
LAST_PAGES = 4   # Number of pages to include from the end (0 = no limit)
# ===================================

import subprocess
import sys
import argparse
from pathlib import Path


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Metadata extraction wrapper script for Preservica assets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full workflow with Preservica download:
  python metadata_extraction_wrapper.py
  python metadata_extraction_wrapper.py --preservica-folder-ref 12345678-1234-1234-1234-123456789abc
  python metadata_extraction_wrapper.py --preservica-folder-ref 12345678-1234-1234-1234-123456789abc --output-dir ./my-downloads
  
  # Work with existing files (skip download):
  python metadata_extraction_wrapper.py --skip-download --output-dir ./srts-test
  python metadata_extraction_wrapper.py --skip-download --output-dir ./srts-test --csv-file my_metadata.csv
        """
    )
    
    parser.add_argument(
        '--preservica-folder-ref',
        type=str,
        help='Preservica folder ID to download (overrides hardcoded FOLDER_ID)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory for downloaded files (overrides hardcoded OUTPUT_DIR)'
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


def main():
    """Main orchestration function."""
    
    # Parse command line arguments
    args = parse_arguments()
    
    print("Starting orchestration process")
    
    # Use CLI arguments if provided, otherwise fall back to hardcoded values
    folder_id = args.preservica_folder_ref if args.preservica_folder_ref else FOLDER_ID
    output_dir = Path(args.output_dir) if args.output_dir else Path(OUTPUT_DIR)
    csv_output = Path(args.csv_file) if args.csv_file else Path(CSV_OUTPUT)
    skip_download = args.skip_download
    
    print(f"Using folder ID: {folder_id}")
    print(f"Output directory: {output_dir}")
    print(f"CSV output: {csv_output}")
    print(f"Skip download: {skip_download}")
    
    # Step 1: Run the download script (unless skipped)
    if not skip_download:
        print("\nStep 1: Downloading assets from Preservica")
        
        download_cmd = ['python', DOWNLOAD_SCRIPT]
        
        # Add the appropriate download source argument
        if folder_id:
            download_cmd.extend(['--folder', folder_id])
        elif 'FOLDERS_FILE' in globals() and FOLDERS_FILE:
            download_cmd.extend(['--folders-file', FOLDERS_FILE])
        elif 'ASSET_ID' in globals() and ASSET_ID:
            download_cmd.extend(['--asset', ASSET_ID])
        elif 'ASSETS_FILE' in globals() and ASSETS_FILE:
            download_cmd.extend(['--assets-file', ASSETS_FILE])
        else:
            print("Error: No download source specified. Please set one of FOLDER_ID, FOLDERS_FILE, ASSET_ID, or ASSETS_FILE.")
            sys.exit(1)
        
        # Add output directory
        download_cmd.append(str(output_dir))
        
        # Add optional arguments
        if USE_ASSET_REF:
            download_cmd.append('--use-asset-ref')

        if ORIGINAL_ONLY:
            download_cmd.append('--original-only')

        if not run_command(download_cmd, "Preservica asset download"):
            print("Download step failed. Stopping orchestration.")
            sys.exit(1)
    else:
        print("\nStep 1: Skipping Preservica download (using existing files)")

    # Step 2: Check if files were downloaded
    print("\nStep 2: Verifying downloaded files")
    if not check_downloaded_files(output_dir):
        print("No files found after download. Stopping orchestration.")
        sys.exit(1)

    # Step 3: Convert any DOCX/DOC files to PDF
    print("\nStep 3: Converting documents to PDF format")
    
    convert_cmd = ['python', CONVERT_SCRIPT, str(output_dir)]

    if not run_command(convert_cmd, "Document conversion"):
        print("Document conversion step failed.")
        sys.exit(1)

    # Step 4: Run the metadata extraction script (main.py remains unchanged, PDF-focused)
    print("\nStep 4: Extracting metadata from PDF files")
    
    extract_cmd = ['python', EXTRACTION_SCRIPT, '--folder', str(output_dir), '--csv-file', str(csv_output)]
    
    # Add optional page limit arguments
    if FIRST_PAGES > 0:
        extract_cmd.extend(['--first', str(FIRST_PAGES)])
    if LAST_PAGES > 0:
        extract_cmd.extend(['--last', str(LAST_PAGES)])

    if not run_command(extract_cmd, "Metadata extraction"):
        print("Metadata extraction step failed.")
        sys.exit(1)

    # Success
    print(f"\nOrchestration completed successfully!")
    print(f"Downloaded files: {output_dir}")
    print(f"Metadata output: {csv_output}")


if __name__ == "__main__":
    main() 
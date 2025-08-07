#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Metadata extraction wrapper script that downloads assets from Preservica and then extracts metadata from the downloaded files.

This wrapper script:
1. Downloads assets from Preservica using download_preservica_assets.py
2. Converts any DOCX/DOC files to PDF using convert_documents.py
3. Extracts metadata from the PDF files using main.py
4. Handles the workflow between the scripts

To use this script, edit the configuration variables at the top of the file.
"""

# ===== HARDCODED CONFIGURATION =====
# Change these variables as needed

# Script paths
DOWNLOAD_SCRIPT = "/home/digital-archivist/Documents/custom scripts/digital-archiving-scripts/pypreservica scripts/download_preservica_assets.py"  # Path to the Preservica download script
CONVERT_SCRIPT = "convert_documents.py"  # Path to the document conversion script
EXTRACTION_SCRIPT = "/home/digital-archivist/Documents/custom scripts/metadata-extraction/main.py"  # Path to the metadata extraction script

# Download configuration
FOLDER_ID = "2ba40ba8-554c-49a7-ae0e-1f60fae4d05d"  # Change this to your folder ID
# FOLDERS_FILE = "folders.txt"  # Uncomment to use multiple folders
# ASSET_ID = "cc56e888-8d18-5582-0d41-65c168d611ee"  # Uncomment to use single asset
# ASSETS_FILE = "assets.txt"  # Uncomment to use multiple assets

# Output configuration
OUTPUT_DIR = "./downloads"  # Directory where downloaded assets will be saved
CSV_OUTPUT = "metadata.csv"  # CSV file to write extracted metadata to

# Optional settings
USE_ASSET_REF = True  # Set to True to use asset reference numbers in filenames
ORIGINAL_ONLY = True  # Set to True to download only original (first generation) files
FIRST_PAGES = 6  # Number of pages to include from the start (0 = no limit)
LAST_PAGES = 4   # Number of pages to include from the end (0 = no limit)
# ===================================

import subprocess
import sys
from pathlib import Path


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
    
    print("Starting orchestration process")
    
    # Convert paths to Path objects
    output_dir = Path(OUTPUT_DIR)
    csv_output = Path(CSV_OUTPUT)
    
    # Step 1: Run the download script
    print("\nStep 1: Downloading assets from Preservica")
    
    download_cmd = ['python', DOWNLOAD_SCRIPT]
    
    # Add the appropriate download source argument
    if 'FOLDER_ID' in globals() and FOLDER_ID:
        download_cmd.extend(['--folder', FOLDER_ID])
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
import os
import csv
import json
from tqdm import tqdm
from multiprocessing import Pool
from config import DOCUMENTS_FOLDER, OUTPUT_CSV, log_message
from fetch_dublin_core import fetch_dublin_core_definitions
from pdf_processing import extract_text_from_pdf
from doc_processing import extract_text_from_doc
from metadata_generation import generate_metadata, validate_and_flag_metadata
from file_metadata import get_file_metadata


def process_document(document_file):
    """Process a single document, extracting metadata and file properties."""
    try:
        text = ""
        if document_file.endswith(".pdf"):
            text = extract_text_from_pdf(document_file)
        elif document_file.endswith((".docx", ".doc")):
            text = extract_text_from_doc(document_file)

        if not text.strip():
            log_message(
                f"No text extracted from {document_file}, skipping metadata generation.")
            return None

        dublin_core_metadata = json.loads(
            generate_metadata(text, dublin_core_definitions))
        file_properties = get_file_metadata(document_file)

        structured_metadata = {
            "Dublin Core": dublin_core_metadata,
            "File Properties": file_properties
        }

        validated_metadata = validate_and_flag_metadata(
            json.dumps(structured_metadata, indent=4))

        return {"filename": os.path.basename(document_file), "metadata": validated_metadata}
    except Exception as e:
        log_message(f"Error processing {document_file}: {e}")
        return None


def main():
    """Main execution function."""
    global dublin_core_definitions
    dublin_core_definitions = fetch_dublin_core_definitions()
    
    document_files = [
        os.path.join(root, file)
        for root, _, files in os.walk(DOCUMENTS_FOLDER)
        for file in files if file.endswith((".pdf", ".docx", ".doc"))
    ]

    log_message(f"Found {len(document_files)} documents")

    with Pool(processes=4) as pool:
        metadata_list = list(filter(None, pool.map(process_document, document_files)))

    fieldnames = ["filename", "metadata"]
    with open(OUTPUT_CSV, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for entry in metadata_list:
            writer.writerow(
                {"filename": entry["filename"], "metadata": entry["metadata"]})

    log_message(f"Metadata saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()

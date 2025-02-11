import os
import csv
import json
from multiprocessing import Pool
from config import *
from context import load_context
from pdf_processing import extract_text_from_pdf
from doc_processing import extract_text_from_doc
from metadata_generation import generate_metadata
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
                f"No text extracted from {document_file} after OCR, skipping metadata generation.")
            return None

        dublin_core_metadata = json.loads(
            generate_metadata(text, load_context()))
        file_properties = get_file_metadata(document_file)

        # Run classification if enabled
        topics = custom_classification(
            document_file) if USE_CUSTOM_CLASSIFICATION else []

        structured_metadata = {
            "Dublin Core": dublin_core_metadata,
            "Topics": topics,
            "File Properties": file_properties
        }

        # Ensure format is set correctly based on preference
        if PREFER_FILE_METADATA_FORMAT:
            structured_metadata["Dublin Core"]["format"] = file_properties.get("format", "Unknown")

        return {
            "filename": os.path.basename(document_file),
            "metadata": structured_metadata,
            "topics": topics
        }
    except Exception as e:
        log_message(f"Error processing {document_file}: {e}")
        return None


def main():
    """Main execution function."""
    global load_context
    context_data = load_context()

    document_files = [
        os.path.join(root, file)
        for root, _, files in os.walk(DOCUMENTS_FOLDER)
        for file in files if file.endswith((".pdf", ".docx", ".doc"))
    ]

    log_message(f"Found {len(document_files)} documents")

    with Pool(processes=4) as pool:
        metadata_list = list(
            filter(None, pool.map(process_document, document_files)))

    fieldnames = ["filename", "metadata"]
    with open(OUTPUT_CSV, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for entry in metadata_list:
            formatted_metadata = json.dumps(
                entry["metadata"], indent=4, ensure_ascii=False)
            writer.writerow({
                "filename": entry["filename"],
                "metadata": formatted_metadata,
            })

    log_message(f"Metadata saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()

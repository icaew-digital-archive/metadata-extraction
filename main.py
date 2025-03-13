import csv
import json
import os
from multiprocessing import Pool

from config import *
from doc_processing import *
from file_metadata import get_file_metadata
from metadata_generation import generate_metadata
from pdf_processing import extract_text_from_pdf


def process_document(document_file):
    """Process a single document, extracting metadata and file properties."""
    try:
        file_properties = get_file_metadata(
            document_file)  # Extract file properties first
        text = ""

        if document_file.endswith((".pdf", ".docx")):
            text = extract_text_from_pdf(document_file)

        if document_file.endswith((".doc")):
            docx_file = convert_doc_to_docx(document_file)
            text = extract_text_from_pdf(docx_file)
            if os.path.exists(docx_file):
                os.remove(docx_file)
            else:
                print("The file does not exist")

        if not text.strip():
            log_message(
                f"No text extracted from {document_file}, returning only file properties.")
            return {
                "filename": os.path.basename(document_file),
                "metadata": {"File Properties": file_properties},
                "topics": []
            }

        dublin_core_metadata = json.loads(
            generate_metadata(text))

        topics = custom_classification(
            document_file) if USE_CUSTOM_CLASSIFICATION else []

        structured_metadata = {
            "OpenAI Response": dublin_core_metadata,
            "Topics": topics,
            "File Properties": file_properties
        }

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
    document_files = [
        os.path.join(root, file)
        for root, _, files in os.walk(DOCUMENTS_FOLDER)
        for file in files if file.endswith((".pdf", ".docx", ".jpg", ".png", ".doc"))
    ]

    log_message(f"Found {len(document_files)} documents")

    with Pool(processes=1) as pool:
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

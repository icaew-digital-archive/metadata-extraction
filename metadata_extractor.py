"""
Core metadata extraction functionality.
"""

import os
from typing import Optional
from pdf_utils import create_partial_pdf, validate_pdf_path
from openai_client import OpenAIClient


class MetadataExtractor:
    def __init__(self) -> None:
        """Initialize the metadata extractor with an OpenAI client."""
        self.client = OpenAIClient()

    def extract_metadata(self, pdf_path: str, first_pages: int = 0, last_pages: int = 0) -> str:
        """
        Extract metadata from a PDF file using OpenAI's API.

        Args:
            pdf_path (str): Path to the PDF file
            first_pages (int): Number of pages to include from the start
            last_pages (int): Number of pages to include from the end

        Returns:
            str: The extracted metadata
        """
        try:
            # Validate the PDF path
            validate_pdf_path(pdf_path)

            # Create partial PDF if page limits are specified
            temp_pdf_path = None
            try:
                if first_pages > 0 or last_pages > 0:
                    pdf_path = create_partial_pdf(
                        pdf_path, first_pages, last_pages)
                    temp_pdf_path = pdf_path  # Store the temp path for cleanup

                # Upload the file and extract metadata
                file_id = self.client.upload_file(pdf_path)
                metadata = self.client.extract_metadata(file_id)

                return metadata

            finally:
                # Clean up temporary file if it was created
                if temp_pdf_path and os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
                    print("Cleaned up temporary PDF file")

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            raise

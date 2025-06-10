"""
PDF utility functions for handling PDF files.
"""

import os
import tempfile
from typing import Optional
from PyPDF2 import PdfReader, PdfWriter


def create_partial_pdf(pdf_path: str, first_pages: int = 0, last_pages: int = 0) -> str:
    """
    Create a new PDF containing only the specified number of pages from the start and end.

    Args:
        pdf_path (str): Path to the original PDF file
        first_pages (int): Number of pages to include from the start
        last_pages (int): Number of pages to include from the end

    Returns:
        str: Path to the temporary PDF file containing selected pages
    """
    try:
        # Read the original PDF
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        if first_pages + last_pages >= total_pages:
            print(f"Warning: Requested {first_pages} first pages and {last_pages} last pages, "
                  f"but PDF only has {total_pages} pages. Using full PDF.")
            return pdf_path

        # Create a new PDF writer
        writer = PdfWriter()

        # Add first pages
        for i in range(min(first_pages, total_pages)):
            writer.add_page(reader.pages[i])

        # Add last pages (if any)
        if last_pages > 0:
            for i in range(max(first_pages, total_pages - last_pages), total_pages):
                writer.add_page(reader.pages[i])

        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_path = temp_file.name
        temp_file.close()

        # Write the selected pages to the temporary file
        with open(temp_path, 'wb') as output_file:
            writer.write(output_file)

        print(f"Created partial PDF with {first_pages} first pages and {last_pages} last pages "
              f"(total {first_pages + last_pages} pages from original {total_pages} pages)")
        return temp_path

    except Exception as e:
        print(f"Error creating partial PDF: {str(e)}")
        raise


def validate_pdf_path(pdf_path: str) -> None:
    """
    Validate that the PDF file exists and is accessible.

    Args:
        pdf_path (str): Path to the PDF file

    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

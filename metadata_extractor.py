"""
Core metadata extraction functionality.

Extraction is split into two stages so large batches can be pipelined
(see pipeline.py):
  1. prepare()  - local work: check the file and cut it to the requested pages
  2. extract()  - OpenAI work: upload, wait for the model, delete the upload
extract_metadata() runs both stages for a single document.
"""

import os
from dataclasses import dataclass
from typing import Optional, Tuple
from pdf_utils import create_partial_pdf, validate_pdf_path
from openai_client import OpenAIClient


@dataclass
class PreparedDocument:
    """A document that is ready to send to OpenAI."""
    source_path: str             # the PDF the metadata belongs to
    upload_path: str             # the file to upload (the source, or a page-limited copy)
    temp_path: Optional[str] = None  # page-limited copy to delete afterwards, if one was made

    def cleanup(self) -> None:
        """Delete the page-limited temporary copy, if any."""
        if self.temp_path and os.path.exists(self.temp_path):
            os.unlink(self.temp_path)
            self.temp_path = None


class MetadataExtractor:
    def __init__(self, include_subjects: bool = True, profile_path: str = None,
                 model: Optional[str] = None) -> None:
        """Initialize the metadata extractor with an OpenAI client.

        Args:
            include_subjects: Whether to include subject classification. Defaults to True.
            profile_path: Path to a YAML profile file. Defaults to the ICAEW profile.
            model: OpenAI model ID. Defaults to config.DEFAULT_MODEL.
        """
        self.client = OpenAIClient(include_subjects=include_subjects, profile_path=profile_path, model=model)
        self.model = self.client.model

    def prepare(self, pdf_path: str, first_pages: int = 0, last_pages: int = 0) -> PreparedDocument:
        """
        Stage 1 (local, CPU/disk): check the PDF and, if page limits are set,
        create a temporary copy containing only those pages.

        Raises:
            FileNotFoundError: If the PDF does not exist
        """
        validate_pdf_path(pdf_path)
        prepared = PreparedDocument(source_path=pdf_path, upload_path=pdf_path)
        if first_pages > 0 or last_pages > 0:
            partial = create_partial_pdf(pdf_path, first_pages, last_pages)
            if partial != pdf_path:
                prepared.upload_path = partial
                prepared.temp_path = partial
        return prepared

    def extract(self, prepared: PreparedDocument, context_prompt: Optional[str] = None,
                source_note: Optional[str] = None) -> str:
        """
        Stage 2 (network): upload a prepared document, get the metadata JSON from
        the model, and delete the upload from OpenAI. The temporary page-limited
        copy is always deleted afterwards.
        """
        try:
            file_id = self.client.upload_file(prepared.upload_path)
            try:
                return self.client.extract_metadata(file_id, context_prompt=context_prompt,
                                                    source_note=source_note)
            finally:
                # Don't leave copies of documents in OpenAI file storage
                self.client.delete_file(file_id)
        finally:
            prepared.cleanup()

    def extract_metadata(self, pdf_path: str, first_pages: int = 0, last_pages: int = 0, original_format: str = None, context_prompt: Optional[str] = None) -> Tuple[str, str, str]:
        """
        Extract metadata from a PDF file using OpenAI's API (both stages).

        Args:
            pdf_path (str): Path to the PDF file
            first_pages (int): Number of pages to include from the start
            last_pages (int): Number of pages to include from the end
            original_format (str): Original file format (e.g., 'docx', 'txt') if the file was converted
            context_prompt (str, optional): Custom context to include in the prompt (e.g. "What follows is a series of photos showing Chartered Accountant's Hall")

        Returns:
            Tuple[str, str, str]: A tuple containing (metadata, original_file_path, original_format)
        """
        try:
            prepared = self.prepare(pdf_path, first_pages, last_pages)
            return self.extract(prepared, context_prompt=context_prompt), pdf_path, original_format
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            raise

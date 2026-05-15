"""
OpenAI API client for metadata extraction.
"""

import os
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
from config import SYSTEM_PROMPT, DEFAULT_MODEL, FILE_PURPOSE


class OpenAIClient:
    def __init__(self) -> None:
        """Initialize the OpenAI client with API key from environment variables."""
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY environment variable not set")

    def upload_file(self, file_path: str) -> str:
        """
        Upload a file to OpenAI.

        Args:
            file_path (str): Path to the file to upload

        Returns:
            str: The file ID assigned by OpenAI
        """
        print(f"Uploading file: {file_path}")
        with open(file_path, "rb") as file:
            uploaded_file = self.client.files.create(
                file=file,
                purpose=FILE_PURPOSE
            )
        print(f"File uploaded successfully. File ID: {uploaded_file.id}")
        return uploaded_file.id

    def extract_metadata(self, file_id: str, context_prompt: Optional[str] = None) -> str:
        """
        Extract metadata from an uploaded file using OpenAI's API.

        Args:
            file_id (str): The ID of the uploaded file
            context_prompt (str, optional): Custom context to prepend to the user message
                (e.g. "What follows is a series of photos showing Chartered Accountant's Hall")

        Returns:
            str: The extracted metadata
        """
        print("Extracting metadata...")
        user_text = "Please analyze this document and extract metadata according to the ICAEW conventions. Return the metadata in the specified format."
        if context_prompt:
            user_text = (
                "The following is background context that identifies the subject, place, or event. "
                "Use it to name what is shown in the document: e.g. if the context says these are photos of Chartered Accountant's Hall, "
                "your description must identify the building as 'Chartered Accountant's Hall' (or similar), not as a generic 'building'. "
                "Describe what is shown in the image/page using the names and identifications from the context below.\n\n"
                f"Context: {context_prompt.strip()}\n\n"
                "---\n\n"
                f"{user_text}"
            )
        response = self.client.responses.create(
            model=DEFAULT_MODEL,
            input=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "file_id": file_id,
                        },
                        {
                            "type": "input_text",
                            "text": user_text,
                        },
                    ]
                }
            ]
        )
        return response.output_text

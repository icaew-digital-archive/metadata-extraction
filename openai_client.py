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

    def extract_metadata(self, file_id: str) -> str:
        """
        Extract metadata from an uploaded file using OpenAI's API.

        Args:
            file_id (str): The ID of the uploaded file

        Returns:
            str: The extracted metadata
        """
        print("Extracting metadata...")
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
                            "text": "Please analyze this document and extract metadata according to the ICAEW conventions. Return the metadata in the specified format.",
                        },
                    ]
                }
            ]
        )
        return response.output_text

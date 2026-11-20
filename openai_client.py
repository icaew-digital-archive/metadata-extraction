"""
OpenAI API client for metadata extraction.
"""

import json
import os
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
from config import get_system_prompt, DEFAULT_MODEL, FILE_PURPOSE

# Network errors, rate limits and 5xx responses are retried by the SDK itself
API_MAX_RETRIES = 3
API_TIMEOUT_SECONDS = 600
# Extra attempts when the model returns something that is not a JSON object
JSON_RETRIES = 1


def strip_code_fences(text: str) -> str:
    """Remove a surrounding markdown code fence (```json ... ```) if present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


class OpenAIClient:
    def __init__(self, include_subjects: bool = True, profile_path: str = None,
                 model: Optional[str] = None) -> None:
        """Initialize the OpenAI client with API key from environment variables.

        Args:
            include_subjects: Whether to include subject classification in the prompt.
                When False, the Subject field is treated as reserved and the topic
                list is omitted. Defaults to True.
            profile_path: Path to a YAML profile file. Defaults to the ICAEW profile.
            model: OpenAI model ID. Defaults to config.DEFAULT_MODEL.
        """
        self.model = model or DEFAULT_MODEL
        load_dotenv()
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'),
                             max_retries=API_MAX_RETRIES, timeout=API_TIMEOUT_SECONDS)
        self.system_prompt = get_system_prompt(include_subjects, profile_path)

    def upload_file(self, file_path: str) -> str:
        """
        Upload a file to OpenAI.

        Args:
            file_path (str): Path to the file to upload

        Returns:
            str: The file ID assigned by OpenAI
        """
        print(f"Uploading file: {file_path}")
        # OpenAI only accepts lower-case extensions (".PDF" is rejected), so the
        # name sent with the upload always uses a lower-case extension
        stem, ext = os.path.splitext(os.path.basename(file_path))
        upload_name = stem + ext.lower()
        with open(file_path, "rb") as file:
            uploaded_file = self.client.files.create(
                file=(upload_name, file),
                purpose=FILE_PURPOSE
            )
        print(f"File uploaded successfully. File ID: {uploaded_file.id}")
        return uploaded_file.id

    def delete_file(self, file_id: str) -> None:
        """Delete an uploaded file from OpenAI storage. Failures are reported, not raised."""
        try:
            self.client.files.delete(file_id)
            print(f"Deleted uploaded file from OpenAI: {file_id}")
        except Exception as e:
            print(f"Warning: could not delete uploaded file {file_id} from OpenAI: {e}")

    def extract_metadata(self, file_id: str, context_prompt: Optional[str] = None,
                         source_note: Optional[str] = None) -> str:
        """
        Extract metadata from an uploaded file using OpenAI's API.

        Args:
            file_id (str): The ID of the uploaded file
            context_prompt (str, optional): Custom context to prepend to the user message
                (e.g. "What follows is a series of photos showing Chartered Accountant's Hall")

        Returns:
            str: The extracted metadata
        """
        print(f"Extracting metadata with {self.model}...")
        user_text = "Please analyse this document and extract metadata according to the conventions specified. Return the metadata in the specified JSON format."
        if source_note:
            # e.g. the document is the subtitle track of a video
            user_text = f"{source_note.strip()}\n\n{user_text}"
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
        last_error = None
        for attempt in range(1 + JSON_RETRIES):
            if attempt:
                print(f"Model did not return valid JSON ({last_error}); retrying...")
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": self.system_prompt
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
                ],
                # Constrain the reply to a single JSON object
                text={"format": {"type": "json_object"}},
            )
            text = strip_code_fences(response.output_text or "")
            if not text:
                last_error = "empty response"
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as e:
                last_error = str(e)
                continue
            if not isinstance(parsed, dict):
                last_error = "response is not a JSON object"
                continue
            return text

        raise ValueError(f"Model did not return valid JSON metadata: {last_error}")

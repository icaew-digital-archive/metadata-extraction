# config.py
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API Key. Please set it in the .env file.")

# Paths
DOCUMENTS_FOLDER = "/home/digital-archivist/Downloads/pdfs"
OUTPUT_CSV = "metadata_output.csv"
LOG_FILE = "metadata_extraction.log"

# Logging configuration
log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


def log_message(message):
    logger.info(message)
    print(message)

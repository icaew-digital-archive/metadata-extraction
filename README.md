# **AI Dublin Core Metadata Extraction [EXPERIMENTAL]**  
_Automated metadata extraction and classification for document processing_

## **Overview**

This project automates **document metadata extraction, classification, and structuring** using **OpenAI’s GPT-4** and the **Dublin Core Metadata Standard**. It processes **PDFs and Word documents**, extracts metadata, and optionally classifies topics using **Semaphore**.

> **⚠ Experimental:** This system is under development and not yet production-ready.

---

## **Features**
✅ **Multi-format Support** – Processes PDFs (`.pdf`), Word documents (`.docx`, `.doc`), and images (`.jpg`, `.png`).  
✅ **AI-Driven Metadata Extraction** – Uses **GPT-4** to generate **Dublin Core** metadata.  
✅ **File Metadata Extraction** – Captures file properties (size, format, hash, timestamps).  
✅ **Optional Topic Classification** – Integrates with **Semaphore** for topic-based classification.  
✅ **Parallel Processing** – Uses multiprocessing for efficient document handling.  
✅ **Structured Output** – Saves metadata in **JSON and CSV** formats.  
✅ **Logging** – Tracks processing steps and errors.  

_(MARC21 support is experimental and disabled by default.)_

---

## **Example Metadata Output (JSON)**

```json
{
    "filename": "example.pdf",
    "metadata": {
        "title": "Understanding AI Ethics",
        "creator": ["John Doe"],
        "subject": ["Artificial Intelligence", "Ethics"],
        "description": "A discussion on AI ethics...",
        "publisher": "AI Research Institute",
        "date": "2023-04-15",
        "format": "application/pdf",
        "language": "en",
        "identifier": "doi:10.1234/ai-ethics",
        "rights": "© 2023 AI Research Institute"
    },
    "topics": ["Machine Learning", "AI Governance"]
}
```
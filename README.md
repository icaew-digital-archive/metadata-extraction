# **Dublin Core Metadata Extraction [EXPERIMENTAL]**  

## **Overview**  
**Dublin Core Metadata Extraction** is an **AI-powered system** that automates **document metadata extraction, validation, and structuring** based on **Dublin Core standards**. It intelligently **analyzes PDFs and Word documents**, extracting key attributes while ensuring metadata is **accurate, normalized, and integration-ready**.  

---

## **Key Features**  
✅ **Hybrid Extraction** – Combines **OCR for scanned documents** and **direct text parsing** for digital files.  
✅ **AI-Driven Metadata Mapping** – Uses **OpenAI** to identify and structure metadata into **Dublin Core fields**.  
✅ **Smart Validation & Normalization** – **Auto-corrects dates**, verifies **MIME types**, and flags inconsistencies.  
✅ **Structured Output** – Saves metadata as **JSON and CSV**, ready for **archives, databases, or APIs**.  
✅ **Optimized Processing** – Uses **batch multiprocessing** for high-speed document analysis.  

---

## **Workflow Overview**

![Data Flow Diagram](flow.png)  

---

## **Requirements**  
To run this project, ensure you have **Python 3.8+** installed.

The system relies on the following key libraries:  
- **`pdfplumber`** – Extracts text from PDFs.  
- **`pytesseract`** – Performs OCR for scanned documents.  
- **`docx2txt` & `textract`** – Extracts text from Word documents.  
- **`requests` & `beautifulsoup4`** – Fetches metadata standards from external sources.  
- **`openai`** – AI-powered metadata generation.  
- **`python-dotenv`** – Manages API keys securely.  

---

## **Current Status**  
🔬 **Experimental** – Ongoing improvements include **structured AI responses, enhanced validation, and expanded format support**.  

## **Planned Enhancements**  
🚀 **Structured JSON API Responses** – Enforces schema-compliant AI-generated metadata.  
🚀 **External System Integration** – Automates metadata export.
# **AI Dublin Core Metadata Extraction [EXPERIMENTAL]**

## **Project Overview**
This project explores the automation of **document metadata extraction, classification, validation, and structuring** based on the [Dublin Core Metadata Standard](https://www.dublincore.org/specifications/dublin-core/dces/). It processes **PDFs and Word documents** using IBM's **Docling** for text extraction and **OpenAI’s GPT-4** for AI-driven metadata generation.

This is an **experimental system**, aimed at evaluating different techniques for metadata extraction and enrichment, and is not yet intended for production use.

---

## **Current Capabilities**

✅ **Text Extraction** – Uses **IBM Docling** for PDFs and Word documents.
✅ **AI-Powered Metadata Generation** – Leverages **OpenAI’s GPT-4** to extract and structure metadata into Dublin Core fields.  
✅ **Context-Based Metadata Mapping** – Loads metadata definitions dynamically from a structured **JSON file** (`context.json`).  
✅ **Structured Output Formats** – Outputs metadata in **JSON and CSV**, making it compatible with archives and databases.  
✅ **Parallel Processing Support** – Uses **multiprocessing** for processing large numbers of documents efficiently.  
✅ **External Processing** – Currently integrating with **Semaphore** for topic classification.  

---

## **Workflow Overview**

![Data Flow Diagram](flow.png)


## **How It Works**

1️⃣ **Extract text** from PDFs and DOCX files using IBM Docling.  
2️⃣ **Generate metadata** using OpenAI’s GPT-4 with structured Dublin Core mappings.  
3️⃣ **Perform optional topic classification** using Semaphore’s API (if enabled).  
4️⃣ **Store results** in structured JSON/CSV formats for further evaluation.  

---

## **Current Development Focus**
- Improving **accuracy and consistency** of metadata extraction.
- Evaluating the effectiveness of **AI-driven metadata structuring**.
- Testing **performance optimizations** for handling large-scale document processing.
- Exploring additional **classification methods** beyond Semaphore.

---
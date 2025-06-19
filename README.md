# Metadata Extraction Tool

A command-line tool for extracting metadata from PDF, DOCX, DOC, TXT, and SRT files using OpenAI's API. The metadata extraction follows ICAEW-specific conventions and includes a wrapper script for downloading assets from Preservica.

## System Architecture

```mermaid
graph TD
    %% Main Components
    Wrapper[metadata_extraction_wrapper.py] --> Download[download_preservica_assets.py]
    Wrapper --> Main[main.py]
    Wrapper --> Converter[convert_documents.py]
    Main --> Extractor[metadata_extractor.py]
    Main --> Writer[metadata_writer.py]
    
    %% Metadata Extractor Dependencies
    Extractor --> OpenAIClient[openai_client.py]
    Extractor --> PDFUtils[pdf_utils.py]
    
    %% Configuration and Environment
    Config[config.py] --> OpenAIClient
    Config --> Writer
    Env[.env] -->|API Key| OpenAIClient
    
    %% Data Flow
    Preservica[Preservica Assets] --> Download
    Download -->|Downloaded Files| Wrapper
    Wrapper -->|Convert if needed| Converter
    Converter -->|PDF Files| Main
    Main -->|Process| Extractor
    Extractor -->|JSON Metadata| Writer
    Writer -->|Append| CSV[CSV Output]
    
    %% External Services
    OpenAIClient -->|API Calls| OpenAI[OpenAI API]
    Download -->|API Calls| PreservicaAPI[Preservica API]
    Converter -->|Conversion| LibreOffice[LibreOffice/Pandoc]
    Converter -->|Text Conversion| ReportLab[ReportLab]
    
    %% Component Details
    subgraph "Orchestration"
        Wrapper
    end
    
    subgraph "Core Components"
        Main
        Extractor
        Writer
        Download
        Converter
    end
    
    subgraph "External Services"
        OpenAIClient
        OpenAI
        PreservicaAPI
        LibreOffice
        ReportLab
    end
    
    subgraph "Utilities"
        PDFUtils
        Config
        Env
    end
    
    %% Styling
    classDef primary fill:#f9f,stroke:#333,stroke-width:2px
    classDef secondary fill:#bbf,stroke:#333,stroke-width:1px
    classDef utility fill:#dfd,stroke:#333,stroke-width:1px
    classDef wrapper fill:#ff9,stroke:#333,stroke-width:2px
    
    class Wrapper wrapper
    class Main,Extractor,Writer,Download,Converter primary
    class OpenAIClient,OpenAI,PreservicaAPI,LibreOffice,ReportLab secondary
    class PDFUtils,Config,Env utility
```

The system follows a modular architecture where:
- `metadata_extraction_wrapper.py` orchestrates the complete workflow (download + convert + extract)
- `download_preservica_assets.py` downloads assets from Preservica
- `convert_documents.py` converts various file formats to PDF for processing
- `main.py` handles CLI interaction and orchestrates the extraction process (PDF-focused)
- `metadata_extractor.py` manages the core extraction logic
- `metadata_writer.py` handles CSV output formatting
- `openai_client.py` provides the OpenAI API integration
- `pdf_utils.py` handles PDF file operations
- `config.py` centralizes configuration settings

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install document conversion tools (for DOCX/DOC support):
```bash
# Option 1: LibreOffice (recommended)
sudo apt-get install libreoffice  # Ubuntu/Debian
brew install libreoffice          # macOS
# Download from https://www.libreoffice.org/ for Windows

# Option 2: Pandoc (alternative)
sudo apt-get install pandoc       # Ubuntu/Debian
brew install pandoc               # macOS
# Download from https://pandoc.org/ for Windows
```

4. Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your-api-key-here
```

5. Configure the wrapper script by editing the variables at the top of `metadata_extraction_wrapper.py`

## Supported File Formats

The tool supports the following file formats:
- **PDF** (.pdf) - Processed directly
- **DOCX** (.docx) - Converted to PDF using LibreOffice/Pandoc
- **DOC** (.doc) - Converted to PDF using LibreOffice/Pandoc
- **TXT** (.txt) - Converted to PDF using ReportLab (NEW)
- **SRT** (.srt) - Converted to PDF using ReportLab with subtitle cleaning (NEW)

### Document Conversion Methods:
- **Office Documents** (DOCX/DOC): LibreOffice (preferred) or Pandoc
- **Text Files** (TXT/SRT): Python ReportLab library
- **PDF Files**: Passed through unchanged

### SRT File Processing:
Subtitle files (.srt) are automatically cleaned during conversion:
- Removes subtitle numbers and timestamps
- Extracts only the actual subtitle text content
- Preserves paragraph structure for better metadata extraction

## Usage

### Option 1: Complete Workflow (Recommended)

Use the wrapper script to download from Preservica and extract metadata in one step:

```bash
python metadata_extraction_wrapper.py
```

Edit the configuration variables at the top of `metadata_extraction_wrapper.py`:
```python
# Download configuration
FOLDER_ID = "your-folder-id-here"  # Change this to your folder ID
OUTPUT_DIR = "./downloads"  # Directory where downloaded assets will be saved
CSV_OUTPUT = "metadata.csv"  # CSV file to write extracted metadata to

# Optional settings
USE_ASSET_REF = True  # Use asset reference numbers in filenames
FIRST_PAGES = 5  # Number of pages to include from the start (0 = no limit)
LAST_PAGES = 3   # Number of pages to include from the end (0 = no limit)
```

### Option 2: Individual Scripts

#### Document Conversion (Standalone)
Convert files in a directory to PDF:
```bash
python convert_documents.py <directory_path>
```

#### Metadata Extraction (PDF Only)
Process PDF files:
```bash
python main.py --file document.pdf -c output.csv
python main.py --folder pdf_directory -c output.csv
```

Process specific pages:
```bash
# First 3 pages
python main.py --file document.pdf --first 3 -c output.csv

# Last 2 pages
python main.py --file document.pdf --last 2 -c output.csv

# Both first and last pages
python main.py --file document.pdf --first 3 --last 2 -c output.csv
```

## Arguments

### Wrapper Script
The wrapper script uses hardcoded configuration variables (no command line arguments).

### Document Converter
- `<directory_path>`: Path to directory containing files to convert

### Main Script (PDF Only)
- `--file`, `-f`: Path to a single PDF file to process
- `--folder`, `-d`: Path to a directory containing PDF files to process
- `--first`, `-p`: Number of pages to include from the start
- `--last`, `-l`: Number of pages to include from the end
- `--csv-file`, `-c`: CSV file to write metadata to (required)

## Output

The tool generates a CSV file with the following metadata fields following ICAEW conventions:

### Core Fields
- `filename/reference`: The filename of the processed file
- `entity.title`: Copy of the Title field
- `entity.description`: Copy of the Description field

### ICAEW-Specific Fields
- `icaew:ContentType`: Content type using controlled vocabulary (e.g., "Technical release", "Annual report", "Article")
- `icaew:InternalReference`: Formatted reference (YYYYMMDD-Document-Name format)
- `icaew:Notes`: Additional notes or comments

### Dublin Core Fields
- `Title`: Document title as it appears in the document
- `Creator`: Authors, faculties, and organizations
- `Subject`: Reserved for future use
- `Description`: Document summary or description
- `Publisher`: Publisher name as credited
- `Contributor`: External institutions involved
- `Date`: Document date in YYYY-MM-DD format
- `Type`: DCMI type values (e.g., "Text", "Moving image")
- `Format`: File format (e.g., "pdf", "docx", "txt")
- `Identifier`: ISBNs, URLs, issue numbers, reference codes
- `Source`: Reserved for future use
- `Language`: ISO 639-1 language codes (e.g., "en")
- `Relation`: Parent folder or collection names
- `Coverage`: Reserved for future use
- `Rights`: Reserved for future use

## Configuration

### Content Type Controlled Vocabulary
The `icaew:ContentType` field uses a controlled vocabulary with the following options:
- Annual report, Article, Biographical profile, Company profile, Course, Database
- eBook, eBook chapter, eLearning module, Event, Form, Helpsheets and support
- Hub page, ICAEW consultation and response, Internal ICAEW policy, Journal
- Learning material, Legal precedent, Library book, Library journal, Listing
- Member reward, Minutes and board papers, Newsletter, No content type, Podcast
- Press release, Promotional material, Regional news, Regulations, Report
- Representation, Research guide, Speech or presentation, Synopsis, Technical release
- Thought leadership report, Transcript, Video, Webinar, Website

### Customization
- Edit `config.py` to modify metadata extraction rules and prompts
- Edit the configuration variables in `metadata_extraction_wrapper.py` to change script paths and settings
- The system uses OpenAI's GPT-4 model by default (configurable in `config.py`)

## Dependencies

### Python Packages
- `openai>=1.0.0` - OpenAI API integration
- `python-dotenv>=1.0.0` - Environment variable management
- `PyPDF2>=3.0.0` - PDF file operations
- `reportlab>=4.0.0` - Text-to-PDF conversion (NEW)

### System Tools
- **LibreOffice** (recommended) - Office document conversion
- **Pandoc** (alternative) - Office document conversion

## File Structure

```
metadata-extraction/
├── metadata_extraction_wrapper.py  # Main orchestration script
├── main.py                         # Metadata extraction CLI (PDF only)
├── convert_documents.py            # Multi-format to PDF conversion
├── download_preservica_assets.py   # Preservica download script
├── metadata_extractor.py           # Core extraction logic
├── metadata_writer.py              # CSV output handling
├── openai_client.py                # OpenAI API integration
├── pdf_utils.py                    # PDF file operations
├── config.py                       # Configuration and prompts
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (API keys)
└── README.md                      # This file
```

## Workflow

1. **Download**: Assets downloaded from Preservica (PDF, DOCX, DOC, TXT, SRT, etc.)
2. **Convert**: `convert_documents.py` converts all non-PDF files to PDF
3. **Extract**: `main.py` processes only PDF files (original + converted)
4. **Output**: CSV with metadata from all documents

The wrapper script orchestrates all steps seamlessly while keeping each component focused on its specific task.
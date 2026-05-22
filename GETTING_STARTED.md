# Getting Started

This guide walks you through installing the tool, running it for the first time, and customising it for your own organisation. No programming experience is required.

---

## What does this tool do?

You give it a folder of documents — PDFs, Word files, images, spreadsheets, and more — and it uses AI (OpenAI's GPT) to read each one and produce structured metadata: title, creator, date, description, subject tags, and so on. The results are saved as a JSON file and a CSV file that you can open in Excel.

If you use Preservica as your digital preservation system, the tool can also download documents directly from Preservica and link the extracted metadata back to the correct asset records.

---

## Before you start

You will need:

- **A computer running Windows, macOS, or Linux**
- **Python 3.10 or newer** — [download from python.org](https://www.python.org/downloads/)
  - To check if you already have it, open a terminal and type `python3 --version`
- **An OpenAI account and API key** — [create one at platform.openai.com](https://platform.openai.com/)
  - An API key looks like `sk-proj-...`
  - You will need credit on your account; small test runs typically cost a few cents
- **Git** (optional but recommended) — [download from git-scm.com](https://git-scm.com/)
- **LibreOffice** (optional) — needed if you want to convert Word or PowerPoint files to PDF
  - [Download from libreoffice.org](https://www.libreoffice.org/)

---

## Step 1 — Get the project files

**Using git:**
```bash
git clone https://github.com/icaew-digital-archive/metadata-extraction.git
cd metadata-extraction
```

**Or download a ZIP** from GitHub and unzip it, then open a terminal inside the folder.

---

## Step 2 — Create a virtual environment

A virtual environment keeps the project's dependencies separate from the rest of your system. You only need to do this once.

```bash
python3 -m venv venv
```

Then activate it:

| Platform | Command |
|----------|---------|
| macOS / Linux | `source venv/bin/activate` |
| Windows (Command Prompt) | `venv\Scripts\activate.bat` |
| Windows (PowerShell) | `venv\Scripts\Activate.ps1` |

Your terminal prompt will change to show `(venv)` when it is active. You need to activate the environment each time you open a new terminal.

---

## Step 3 — Install dependencies

With the virtual environment active:

```bash
pip install -r requirements.txt
```

This installs all the required Python packages. It may take a minute or two.

**Linux/Ubuntu only** — the Browse button in the UI needs `tkinter`, which is not a pip package:

```bash
sudo apt install python3-tk
```

---

## Step 4 — Create your `.env` file

The tool reads your credentials from a file called `.env` in the project folder. This file is never shared or committed to git — it stays on your computer only.

Create a file named `.env` in the project root and add the following:

```
OPENAI_API_KEY=sk-proj-your-key-here
```

If you use Preservica, add your credentials too:

```
USERNAME=your.email@organisation.org
PASSWORD=your-preservica-password
TENANT=your-tenant-name
SERVER=eu.preservica.com
```

> **Important:** Never share this file or commit it to git. It contains sensitive credentials.

---

## Step 5 — Run the tool

Start the web UI:

```bash
streamlit run app.py
```

Your browser will open automatically at `http://localhost:8501`. If it does not, open that address manually.

---

## Step 6 — Your first extraction

1. In the **Input source** bar at the top, select **Select files**
2. Click **Browse files** and choose one or more PDFs, Word documents, or images
3. In the sidebar on the left, make sure a **Profile** is selected (start with **Default** or **ICAEW**)
4. Click the **Extract Metadata** button
5. The tool uploads each file to OpenAI, extracts the metadata, and shows the results on screen
6. Use the **Download JSON** and **Download CSV** buttons to save the output

---

## Understanding profiles

A **profile** is a YAML file (a simple text file) that tells the AI:
- What role it is playing ("you are a metadata archivist for...")
- What fields to extract and what rules to follow for each
- What vocabulary to use for things like content type
- What subject classification scheme to use, if any
- What example outputs look like

Two profiles are included:

| Profile | File | When to use |
|---------|------|-------------|
| **Default** | `profiles/default.yaml` | Any organisation — a clean starting point |
| **ICAEW** | `profiles/icaew.yaml` | The ICAEW digital archive specifically |

You select the profile from the **Profile** dropdown in the sidebar. If there is only one profile, no dropdown is shown.

---

## Creating your own profile

The easiest way is to copy `profiles/default.yaml` to a new file, then edit it.

```bash
cp profiles/default.yaml profiles/myorg.yaml
```

Open `profiles/myorg.yaml` in a plain text editor (Notepad, TextEdit, VS Code, etc.) and work through the fields below. The profile will appear automatically in the UI the next time you start it.

> **YAML formatting note:** Indentation matters in YAML. Use spaces, not tabs. Keep the structure of the file consistent with the original.

---

### Field-by-field guide

#### `name` and `description`

```yaml
name: "My Organisation"
description: "Metadata extraction profile for My Organisation's digital archive"
```

`name` is what appears in the Profile dropdown in the UI. `description` is for your own reference.

---

#### `role`

```yaml
role: "You are a metadata archivist for My Organisation's digital archive. Your task is to analyse uploaded documents and extract structured metadata following the Dublin Core schema."
```

This is the opening instruction sent to the AI. Tell it who it is and what it is doing. Be specific about your organisation if that helps — for example, mentioning the type of archive, the subject area, or the country can improve accuracy.

---

#### `extra_guidelines`

```yaml
extra_guidelines:
  - "Always use Australian English spelling throughout all metadata fields."
  - "For the creator field, always normalise 'Department of Finance' to 'DoF'."
```

A list of additional rules for the AI, added after the standard set. Use this for anything specific to your organisation — spelling conventions, term normalisation, date format quirks in your documents, etc.

Each guideline is a plain sentence. You can have as many or as few as you like. Delete the section entirely (or leave it as `extra_guidelines: []`) if you have nothing to add.

---

#### `xip_fields`

```yaml
xip_fields: false
```

Set to `true` if your system uses Preservica's XIP schema and you want `entity.title` and `entity.description` fields in the output (these are just mirrors of the Dublin Core Title and Description). Leave as `false` otherwise.

---

#### `custom_fields`

```yaml
custom_fields: []
```

A list of extra metadata fields specific to your system, added before the Dublin Core fields in the output. This is an advanced option — most organisations will leave it empty.

If you do need custom fields, each entry looks like this:

```yaml
custom_fields:
  - id: "myorg:ContentType"
    reserved: false
    multiple: false
    prompt_text: |
      **myorg:ContentType (OPTIONAL)**
      - Single value only
      - Must be one of: Report, Article, Policy, Guidance
      - If the type cannot be determined, leave empty ("")
```

- `id` — the field name that appears in the JSON output
- `reserved: true` — the field always outputs empty (used as a placeholder for future use)
- `multiple: false` — the field holds a single value (use `true` for arrays)
- `prompt_text` — the instruction sent to the AI for this field

---

#### `subject_topic_list_file`

```yaml
subject_topic_list_file: "topic_list.txt"
```

Path (relative to the project root) to a plain text file containing your subject classification scheme. The AI will use this list when filling in the Subject field.

The file should use indentation to show hierarchy, like this:

```
- Sciences
  - Biology
    - Botany
    - Zoology
  - Chemistry
- History
  - Ancient history
  - Modern history
```

If you do not have a subject scheme, set this to `null`:

```yaml
subject_topic_list_file: null
```

The Subject field will then accept free-text keywords instead.

---

#### `subject_max`

```yaml
subject_max: 10
```

The maximum number of subject terms the AI will assign to a single document. 10 is the default. Reduce it if you want tighter classification.

---

#### Field overrides: `publisher_override`, `contributor_override`, `identifier_override`, `title_override`, `creator_override`, `description_override`, `relation_override`

These let you replace the default instructions for individual Dublin Core fields with your own version. This is useful when you have specific rules — for example, a default publisher name, or a rule about what counts as a valid identifier in your archive.

```yaml
publisher_override: |
  **Publisher (REQUIRED)**
  - Single value only
  - Use the publisher name as credited in the document
  - If no publisher is explicitly credited and the document is from My Organisation, use "My Organisation"
  - Otherwise, return an empty string ("")
```

The `|` character starts a multi-line block in YAML. Everything indented below it is treated as a single piece of text.

If you do not need to override a field, leave the key out of your profile entirely (or set it to `null`).

---

#### `output_fields`

```yaml
output_fields:
  - {name: "Title",       type: "string"}
  - {name: "Creator",     type: "array"}
  - {name: "Subject",     type: "subject"}
  - {name: "Description", type: "string"}
  - {name: "Publisher",   type: "string"}
  - {name: "Contributor", type: "array"}
  - {name: "Date",        type: "string"}
  - {name: "Type",        type: "string"}
  - {name: "Format",      type: "string"}
  - {name: "Identifier",  type: "array"}
  - {name: "Source",      type: "string", reserved: true}
  - {name: "Language",    type: "array"}
  - {name: "Relation",    type: "array"}
  - {name: "Coverage",    type: "string", reserved: true}
  - {name: "Rights",      type: "string", reserved: true}
```

This defines which fields appear in the JSON output and in what order. The types are:

| Type | Meaning | Example in JSON |
|------|---------|-----------------|
| `string` | A single text value | `"Title": "Annual report 2023"` |
| `array` | A list of text values | `"Creator": ["Jane Smith", "ACME Corp"]` |
| `subject` | Like array, but disabled when Subject classification is turned off | `"Subject": ["History", "Modern history"]` |
| `reserved: true` | Always outputs empty — a placeholder | `"Source": ""` |

For most organisations, the default list in `default.yaml` is fine. Only change it if you need to add, remove, or reorder fields.

---

#### `examples`

```yaml
examples:
  - |
    {
        "Title": "Annual report 2023",
        "Creator": ["My Organisation"],
        "Subject": [],
        "Description": "Annual report for My Organisation covering the financial year 2023. (AI generated description)",
        "Publisher": "My Organisation",
        "Contributor": [],
        "Date": "2023",
        "Type": "Text",
        "Format": "pdf",
        "Identifier": [],
        "Source": "",
        "Language": ["en"],
        "Relation": [],
        "Coverage": "",
        "Rights": ""
    }
```

One or more examples of filled-in JSON output. These are shown to the AI alongside the field instructions and are the single most effective thing you can add to improve accuracy.

Provide examples that are representative of your actual documents. You can include as many as you like (two or three is usually enough). The `|` character and indentation tell YAML to treat the block as a literal multi-line string — keep that structure exactly.

---

#### `extra_validation_rules`

```yaml
extra_validation_rules:
  - "All text must use Australian English spelling"
  - "Content type must be one of: Report, Article, Policy, Guidance"
```

Additional validation rules appended after the standard ones. These are instructions to the AI to double-check its own output before returning it. Most organisations can leave this as `extra_validation_rules: []`.

---

## A minimal example profile

Here is what a finished profile might look like for a small archive:

```yaml
name: "City Archive"
description: "Metadata extraction profile for the City of Exampletown digital archive"

role: "You are a metadata archivist for the City of Exampletown digital archive. Your task is to analyse uploaded documents and extract structured metadata following the Dublin Core schema."

extra_guidelines:
  - "Always use British English spelling throughout all metadata fields."
  - "For the creator field, normalise 'City of Exampletown' to 'Exampletown City Council'."

xip_fields: false
custom_fields: []

subject_topic_list_file: "profiles/exampletown_topics.txt"
subject_max: 5

publisher_override: |
  **Publisher (REQUIRED)**
  - Single value only
  - Use the publisher name as credited in the document
  - If no publisher is credited and the document originates from the City of Exampletown, use "Exampletown City Council"
  - Otherwise return an empty string ("")

output_fields:
  - {name: "Title",       type: "string"}
  - {name: "Creator",     type: "array"}
  - {name: "Subject",     type: "subject"}
  - {name: "Description", type: "string"}
  - {name: "Publisher",   type: "string"}
  - {name: "Contributor", type: "array"}
  - {name: "Date",        type: "string"}
  - {name: "Type",        type: "string"}
  - {name: "Format",      type: "string"}
  - {name: "Identifier",  type: "array"}
  - {name: "Source",      type: "string", reserved: true}
  - {name: "Language",    type: "array"}
  - {name: "Relation",    type: "array"}
  - {name: "Coverage",    type: "string", reserved: true}
  - {name: "Rights",      type: "string", reserved: true}

examples:
  - |
    {
        "Title": "Exampletown City Council minutes, 14th March 2023",
        "Creator": ["Exampletown City Council"],
        "Subject": ["Local government", "Council minutes"],
        "Description": "Minutes of the Exampletown City Council meeting held on 14 March 2023. Items discussed include the draft budget, planning applications, and community grant allocations. (AI generated description)",
        "Publisher": "Exampletown City Council",
        "Contributor": [],
        "Date": "2023-03-14",
        "Type": "Text",
        "Format": "pdf",
        "Identifier": [],
        "Source": "",
        "Language": ["en"],
        "Relation": ["Council minutes"],
        "Coverage": "",
        "Rights": ""
    }

extra_validation_rules: []
```

---

## Using the command line instead of the UI

If you prefer the command line, the main script is `main.py`:

```bash
# Process all PDFs in a folder, using the default profile
python main.py --folder ./my-documents -j output.json

# Use a specific profile
python main.py --folder ./my-documents --profile default -j output.json
python main.py --folder ./my-documents --profile profiles/myorg.yaml -j output.json

# Limit to the first 5 pages and last 3 pages of each document
python main.py --folder ./my-documents --first 5 --last 3 -j output.json

# Disable subject classification
python main.py --folder ./my-documents --no-subjects -j output.json

# Convert the JSON output to CSV
python json_to_csv_converter.py output.json output.csv
```

For Preservica downloads, use the wrapper script:

```bash
python metadata_extraction_wrapper.py --preservica-folder-ref <uuid> --output-dir ./downloads --profile myorg
```

Run any script with `--help` to see all available options.

---

## Tips

- **Start with one or two documents** to check the output looks right before processing a large batch.
- **The examples in your profile are the most powerful tuning tool.** If the AI keeps getting something wrong, add an example showing the correct output.
- **Turn off subject classification** (sidebar toggle or `--no-subjects`) if you do not have a subject scheme yet — it saves time and cost.
- **Use the Context prompt** when processing a thematically consistent batch. For example: *"These are photographs from the 1987 opening of the new town hall"* helps the AI write better descriptions.
- **Page limits** (Pages from start / end) are useful for large documents where only the cover and closing pages carry the metadata you care about. Setting "Pages from start: 5, Pages from end: 3" typically captures title pages, forewords, and colophons while keeping costs down.

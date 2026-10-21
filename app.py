"""
Streamlit front-end for the ICAEW Metadata Extraction tool.

Run with:
    streamlit run app.py
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'), override=True)

# Make the tool's modules importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from metadata_extractor import MetadataExtractor
from json_metadata_writer import JSONMetadataWriter
from json_to_csv_converter import JSONToCSVConverter
from convert_documents import convert_directory, get_supported_formats, is_supported_format
from config import list_profiles
from preservica_writer import apply_record, create_client

UPLOAD_TYPES = [ext.lstrip('.') for ext in get_supported_formats()]
from metadata_extraction_wrapper import (
    FIRST_PAGES as DEFAULT_FIRST_PAGES,
    LAST_PAGES as DEFAULT_LAST_PAGES,
    WORKING_DIR as DEFAULT_WORKING_DIR,
    JSON_OUTPUT as DEFAULT_JSON_OUTPUT,
    CSV_OUTPUT as DEFAULT_CSV_OUTPUT,
    USE_ASSET_REF as DEFAULT_USE_ASSET_REF,
    ORIGINAL_ONLY as DEFAULT_ORIGINAL_ONLY,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def strip_code_fences(text: str) -> str:
    """Remove markdown code fences from an OpenAI response if present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        stripped = "\n".join(lines[1:-1])
    return stripped


def get_pdfs_from_folder(folder_path: str) -> List[str]:
    """Return sorted list of PDF paths in a directory."""
    folder = Path(folder_path)
    return sorted(str(p) for p in folder.iterdir() if p.suffix.lower() == ".pdf")


def get_supported_files_from_folder(folder_path: str) -> List[str]:
    """Return sorted list of all supported source files in a directory."""
    folder = Path(folder_path)
    return sorted(str(p) for p in folder.iterdir() if is_supported_format(str(p)))


def generate_csv_from_json(json_path: str) -> str:
    """Convert a JSON output file to a CSV string."""
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = os.path.join(tmp, "metadata.csv")
        JSONToCSVConverter().convert_json_to_csv(json_path, csv_path)
        with open(csv_path, "r", encoding="utf-8") as f:
            return f.read()


def browse_for_folder() -> str:
    """Open a native OS folder picker and return the selected path."""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    folder = filedialog.askdirectory(master=root)
    root.destroy()
    return folder or ""


def apply_to_preservica(json_path: str, descriptive: bool, xip: bool, overwrite: bool) -> None:
    """Apply every record in the JSON output to its Preservica asset, storing results in session state."""
    records = JSONMetadataWriter(json_path).get_records()
    outcomes = []
    with st.status("Applying metadata to Preservica…", expanded=True) as apply_status:
        try:
            client = create_client()
        except Exception as e:
            apply_status.update(label=f"Could not connect to Preservica: {e}", state="error")
            return
        icons = {"applied": ":white_check_mark:", "skipped": ":fast_forward:", "error": ":x:"}
        for record in records:
            outcome = apply_record(client, record, descriptive=descriptive, xip=xip, overwrite=overwrite)
            outcomes.append(outcome)
            st.write(f"{icons[outcome['status']]} **{outcome['filename']}** — {outcome['message']}")
        counts = {s: sum(o["status"] == s for o in outcomes) for s in icons}
        label = f"Preservica update — {counts['applied']} applied"
        if counts["skipped"]:
            label += f", {counts['skipped']} skipped"
        if counts["error"]:
            label += f", {counts['error']} failed"
        apply_status.update(label=label, state="error" if counts["error"] else "complete")
    st.session_state.apply_results = outcomes


def preservica_update_options(key_prefix: str, when: str) -> Tuple[bool, bool, bool]:
    """Render the Preservica update checkboxes; returns (descriptive, xip, overwrite)."""
    col1, col2, col3 = st.columns(3)
    with col1:
        descriptive = st.checkbox(
            f"Apply metadata to Preservica{when}",
            value=False,
            key=f"{key_prefix}_descriptive",
            help="Add the extracted Dublin Core and ICAEW metadata to each asset it was extracted from.",
        )
    with col2:
        xip = st.checkbox(
            f"Update XIP in Preservica{when}",
            value=False,
            key=f"{key_prefix}_xip",
            help="Set each asset's Preservica title and description from the extracted Title and Description.",
        )
    with col3:
        overwrite = st.checkbox(
            "Overwrite existing metadata",
            value=False,
            key=f"{key_prefix}_overwrite",
            disabled=not descriptive,
            help="Replace existing DC/ICAEW metadata. When unticked, assets that already have it are left unchanged.",
        )
    return descriptive, xip, overwrite


def run_subprocess(cmd: List[str]) -> Tuple[bool, str]:
    """Run a subprocess, returning (success, combined output)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        return result.returncode == 0, output.strip()
    except Exception as e:
        return False, str(e)


# ── page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Metadata Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Settings")

    # Profile selector
    _available_profiles = list_profiles()
    _profile_names = [name for name, _ in _available_profiles]
    _profile_paths = {name: path for name, path in _available_profiles}

    if len(_available_profiles) > 1:
        _non_default = [n for n in _profile_names if n.lower() != "default"]
        _default_index = _profile_names.index(_non_default[0]) if _non_default else 0
        selected_profile_name = st.selectbox(
            "Profile",
            options=_profile_names,
            index=_default_index,
            help="Select the metadata extraction profile that matches your organisation or archive.",
        )
    else:
        selected_profile_name = _profile_names[0] if _profile_names else None

    selected_profile_path = _profile_paths.get(selected_profile_name) if selected_profile_name else None

    st.divider()

    # Subject classification  (--no-subjects)
    include_subjects = st.toggle(
        "Subject classification",
        value=True,
        help=(
            "Classify documents against the topic hierarchy defined in the profile. "
            "Disable to leave the Subject field empty."
        ),
    )

    st.divider()

    # Page limits  (--first / --last)
    st.subheader("Page limits")
    st.caption(
        "Restrict extraction to a page range — useful for large documents "
        "where only the cover and final pages are needed. "
        "Set both to 0 to use the full document."
    )
    first_pages = st.number_input("Pages from start", min_value=0, value=DEFAULT_FIRST_PAGES, step=1)
    last_pages = st.number_input("Pages from end", min_value=0, value=DEFAULT_LAST_PAGES, step=1)

    st.divider()

    # Context prompt  (--context-prompt)
    st.subheader("Context prompt")
    st.caption(
        "Optional background that helps the model identify subjects — "
        "for example, the location, event, or collection the documents belong to."
    )
    context_prompt = st.text_area(
        "Context",
        value="",
        placeholder='e.g. "These are photographs of Chartered Accountant\'s Hall taken in 1987"',
        label_visibility="collapsed",
    )

    st.divider()

    # Output file paths  (--json-file / --csv-file)
    st.subheader("Output files")
    st.caption(
        "Optionally save outputs directly to disk. "
        "Leave blank to use the download buttons only."
    )
    json_output_path = st.text_input(
        "JSON save path",
        value="",
        placeholder=f"e.g. {DEFAULT_JSON_OUTPUT}",
    )
    csv_output_path = st.text_input(
        "CSV save path",
        value="",
        placeholder=f"e.g. {DEFAULT_CSV_OUTPUT}",
    )


# ── main area ─────────────────────────────────────────────────────────────────

st.title("Metadata Extractor")
st.caption("Extract structured metadata from documents and images using AI.")

input_mode = st.radio(
    "Input source",
    ["Select files", "Local folder", "Preservica"],
    horizontal=True,
    help=(
        "**Select files** — choose PDFs, Office documents, or images from your computer.  \n"
        "**Local folder** — point to a directory on this machine; non-PDF files are converted automatically.  \n"
        "**Preservica** — download and process assets from a Preservica repository."
    ),
)

# Defaults for variables only set inside the Preservica block
preservica_mode = input_mode == "Preservica"
preservica_download_by = "Folder"
preservica_folder_refs: List[str] = []
preservica_asset_ids: List[str] = []
auto_descriptive = False
auto_xip = False
overwrite_existing = False
original_formats: dict = {}
effective_output_dir = ""
exclude_extensions: List[str] = []
use_asset_ref = True
original_only = True

source_dir: str = ""
pdf_paths: List[str] = []
file_labels: List[str] = []
file_sizes: List[int] = []

# ── input: select files ───────────────────────────────────────────────────────

if input_mode == "Select files":
    uploaded_files = st.file_uploader(
        "Select files",
        type=UPLOAD_TYPES,
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if not uploaded_files:
        st.info("Select one or more files above to get started.")
        st.stop()

    # Stage uploads to a persistent temp directory held in session state so
    # paths remain valid across the button-click re-render.
    if "upload_tmp" not in st.session_state:
        st.session_state.upload_tmp = tempfile.mkdtemp()

    tmp_dir = st.session_state.upload_tmp
    current_names = {uf.name for uf in uploaded_files}

    # Remove any previously staged files that the user has since deselected
    for existing in Path(tmp_dir).iterdir():
        if existing.name not in current_names:
            existing.unlink()

    for uf in uploaded_files:
        dest = os.path.join(tmp_dir, uf.name)
        with open(dest, "wb") as fh:
            fh.write(uf.getbuffer())

    source_dir   = tmp_dir
    file_labels  = [uf.name for uf in uploaded_files]
    file_sizes   = [uf.size for uf in uploaded_files]

# ── input: local folder ───────────────────────────────────────────────────────

elif input_mode == "Local folder":
    col_path, col_btn = st.columns([5, 1])
    with col_path:
        folder_input = st.text_input(
            "Folder path",
            value=st.session_state.get("local_folder", ""),
            placeholder="/home/user/documents/files",
            label_visibility="collapsed",
        )
    with col_btn:
        st.write("")  # vertical-alignment spacer
        if st.button("Browse…", use_container_width=True):
            picked = browse_for_folder()
            if picked:
                st.session_state.local_folder = picked
                st.rerun()

    # Keep session state in sync with whatever is in the text box
    st.session_state.local_folder = folder_input

    if not folder_input:
        st.info("Enter the path to a folder containing documents or images, or click Browse.")
        st.stop()

    if not os.path.isdir(folder_input):
        st.error(f"Not a valid directory: `{folder_input}`")
        st.stop()

    source_files = get_supported_files_from_folder(folder_input)

    if not source_files:
        st.warning(f"No supported files found in `{folder_input}`.")
        st.stop()

    source_dir  = folder_input
    file_labels = [os.path.basename(p) for p in source_files]
    file_sizes  = [os.path.getsize(p) for p in source_files]

# ── input: preservica ─────────────────────────────────────────────────────────

else:
    preservica_download_by = st.radio(
        "Download by",
        ["Folder", "Asset IDs"],
        horizontal=True,
        help=(
            "**Folder** — download all assets in one or more Preservica folders using their UUIDs.  \n"
            "**Asset IDs** — supply one or more specific asset UUIDs."
        ),
    )

    if preservica_download_by == "Folder":
        folder_refs_raw = st.text_area(
            "Preservica folder references (one per line)",
            placeholder="e.g.\n0a5d69bc-d85b-4482-a45c-8b20c40ef1ba\nbb45f999-7c07-4471-9c30-54b057c500ff",
            height=100,
        )
        preservica_folder_refs = [
            line.strip() for line in folder_refs_raw.splitlines() if line.strip()
        ]
    else:
        asset_ids_raw = st.text_area(
            "Asset IDs (one per line)",
            placeholder="e.g.\ncc56e888-8d18-5582-0d41-65c168d611ee\n0a5d69bc-d85b-4482-a45c-8b20c40ef1ba",
            height=150,
        )
        preservica_asset_ids = [
            line.strip() for line in asset_ids_raw.splitlines() if line.strip()
        ]

    col_out, col_btn2 = st.columns([5, 1])
    with col_out:
        output_dir_input = st.text_input(
            "Output directory",
            value=st.session_state.get("preservica_dir", DEFAULT_WORKING_DIR),
            placeholder=DEFAULT_WORKING_DIR,
            help="Directory where assets are downloaded and processed.",
        )
    with col_btn2:
        st.write("")
        if st.button("Browse…", key="browse_out", use_container_width=True):
            picked = browse_for_folder()
            if picked:
                st.session_state.preservica_dir = picked
                st.rerun()

    st.session_state.preservica_dir = output_dir_input
    effective_output_dir = output_dir_input

    exclude_ext_input = st.text_input(
        "Exclude file extensions",
        value="",
        placeholder="e.g. mp4 avi mov  (space-separated)",
        help="File types to skip during the Preservica download.",
    )
    exclude_extensions = exclude_ext_input.split() if exclude_ext_input.strip() else []

    st.caption("Optionally write results back to Preservica once extraction finishes — or leave unticked to review first.")
    auto_descriptive, auto_xip, overwrite_existing = preservica_update_options("auto", " after extraction")

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        use_asset_ref = st.checkbox(
            "Use asset reference in filenames",
            value=DEFAULT_USE_ASSET_REF,
            help=(
                "Name downloaded files by their Preservica asset reference. "
                "Required to apply metadata back to Preservica."
            ),
        )
    with col_opt2:
        original_only = st.checkbox(
            "Original files only",
            value=DEFAULT_ORIGINAL_ONLY,
            help="Download only the original (first generation) file for each asset.",
        )

    if not effective_output_dir:
        st.info("Enter an output directory, or click Browse.")
        st.stop()

    if (auto_descriptive or auto_xip) and not use_asset_ref:
        st.error("Updating Preservica requires **Use asset reference in filenames**.")
        st.stop()


# ── file list preview (non-Preservica only) ───────────────────────────────────

if not preservica_mode and file_labels:
    file_word = "file" if len(pdf_paths) == 1 else "files"
    st.write(f"**{len(pdf_paths)} {file_word} ready**")
    with st.expander("Files to process"):
        for name, size in zip(file_labels, file_sizes):
            st.write(f"- **{name}** ({size / 1024:.1f} KB)")


# ── extract button ────────────────────────────────────────────────────────────

btn_label = "Download and Extract Metadata" if preservica_mode else "Extract Metadata"

if preservica_mode:
    preservica_ready = (
        (preservica_download_by == "Folder" and bool(preservica_folder_refs)) or
        (preservica_download_by == "Asset IDs" and bool(preservica_asset_ids))
    )
else:
    preservica_ready = True

if st.button(btn_label, type="primary", use_container_width=True, disabled=not preservica_ready):

    # Validate output paths
    if json_output_path:
        out_dir = os.path.dirname(os.path.abspath(json_output_path))
        if not os.path.isdir(out_dir):
            st.error(f"Output directory does not exist: `{out_dir}`")
            st.stop()

    if csv_output_path:
        csv_dir = os.path.dirname(os.path.abspath(csv_output_path))
        if not os.path.isdir(csv_dir):
            st.error(f"CSV output directory does not exist: `{csv_dir}`")
            st.stop()

    # ── Preservica pipeline ───────────────────────────────────────────────────

    if preservica_mode:

        # Step 1: Download from Preservica
        download_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'download_preservica_assets.py')
        if not os.path.isfile(download_script):
            st.error(f"Download script not found: `{download_script}`")
            st.stop()

        os.makedirs(effective_output_dir, exist_ok=True)

        with st.status("Downloading assets from Preservica…", expanded=True) as dl_status:
            if preservica_download_by == "Asset IDs":
                if len(preservica_asset_ids) == 1:
                    download_cmd = [sys.executable, download_script, '--asset', preservica_asset_ids[0]]
                else:
                    tmp_assets = tempfile.NamedTemporaryFile(
                        mode='w', suffix='.txt', delete=False, prefix='preservica_assets_'
                    )
                    tmp_assets.write('\n'.join(preservica_asset_ids))
                    tmp_assets.close()
                    st.session_state['_assets_tmp'] = tmp_assets.name
                    download_cmd = [sys.executable, download_script, '--assets-file', tmp_assets.name]
            elif len(preservica_folder_refs) == 1:
                download_cmd = [sys.executable, download_script, '--folder', preservica_folder_refs[0]]
            else:
                tmp_folders = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.txt', delete=False, prefix='preservica_folders_'
                )
                tmp_folders.write('\n'.join(preservica_folder_refs))
                tmp_folders.close()
                st.session_state['_assets_tmp'] = tmp_folders.name
                download_cmd = [sys.executable, download_script, '--folders-file', tmp_folders.name]
            if use_asset_ref:
                download_cmd.append('--use-asset-ref')
            if original_only:
                download_cmd.append('--original-only')
            if exclude_extensions:
                download_cmd.extend(['--exclude-extensions', *exclude_extensions, '--'])
            download_cmd.append(effective_output_dir)

            success, output = run_subprocess(download_cmd)
            if output:
                st.code(output, language=None)
            # Clean up temp assets file if one was created
            tmp_assets_path = st.session_state.pop('_assets_tmp', None)
            if tmp_assets_path and os.path.exists(tmp_assets_path):
                try:
                    os.unlink(tmp_assets_path)
                except OSError:
                    pass

            if not success:
                dl_status.update(label="Download failed", state="error")
                st.stop()
            dl_status.update(label="Download complete", state="complete")

        # Record each asset's downloaded format before conversion replaces it with a PDF
        original_formats = {
            p.stem: p.suffix.lstrip('.').lower()
            for p in Path(effective_output_dir).iterdir()
            if p.is_file() and is_supported_format(str(p))
        }

        # Step 2: Convert documents to PDF
        with st.status("Converting documents to PDF…", expanded=True) as conv_status:
            try:
                converted = convert_directory(effective_output_dir)
                if converted:
                    for p in converted:
                        st.write(f"Converted: `{os.path.basename(p)}`")
                else:
                    st.write("No conversion needed — all files already PDF.")
                conv_status.update(
                    label=f"Conversion complete — {len(converted)} file(s) converted",
                    state="complete",
                )
            except Exception as e:
                conv_status.update(label=f"Conversion warning: {e}", state="error")

        # Step 3: Resolve PDFs for extraction
        pdf_paths = get_pdfs_from_folder(effective_output_dir)
        if not pdf_paths:
            st.error(f"No PDF files found in `{effective_output_dir}` after conversion.")
            st.stop()

        file_word = "file" if len(pdf_paths) == 1 else "files"
        st.write(f"**{len(pdf_paths)} {file_word} ready for extraction**")

    # ── Select files / Local folder pipeline (convert + find PDFs) ───────────

    if not preservica_mode:
        with st.status("Preparing files…", expanded=True) as prep_status:
            try:
                converted = convert_directory(source_dir)
                count = len(converted)
                if converted:
                    for p in converted:
                        st.write(f"Converted: `{os.path.basename(p)}`")
                else:
                    st.write("No conversion needed — all files already PDF.")
                label = f"Converted {count} file(s) to PDF" if count else "No conversion needed"
                prep_status.update(label=label, state="complete")
            except Exception as e:
                prep_status.update(label=f"Conversion warning: {e}", state="error")

        pdf_paths = get_pdfs_from_folder(source_dir)
        if not pdf_paths:
            st.error("No PDF files found for extraction.")
            st.stop()

    # ── Extraction (shared across all modes) ──────────────────────────────────

    try:
        extractor = MetadataExtractor(include_subjects=include_subjects, profile_path=selected_profile_path)
    except ValueError as e:
        st.error(f"Could not initialise extractor: {e}")
        st.stop()

    if json_output_path:
        active_json_path = json_output_path
    else:
        # Clean up the previous run's temp file
        old_temp = st.session_state.get("temp_json")
        if old_temp and os.path.exists(old_temp):
            try:
                os.unlink(old_temp)
            except OSError:
                pass
        tmp_fh = tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, prefix="metadata_"
        )
        tmp_fh.close()
        st.session_state.temp_json = tmp_fh.name
        active_json_path = st.session_state.temp_json

    writer = JSONMetadataWriter(active_json_path, profile_path=selected_profile_path)

    st.session_state.results   = []
    st.session_state.errors    = []
    st.session_state.json_path = active_json_path
    st.session_state.apply_results = None
    st.session_state.can_apply = preservica_mode and use_asset_ref

    total          = len(pdf_paths)
    progress_slot  = st.empty()
    progress       = progress_slot.progress(0, text="Starting…")

    with st.status("Extracting metadata…", expanded=True) as ext_status:
        for i, pdf_path in enumerate(pdf_paths, 1):
            filename = os.path.basename(pdf_path)
            progress.progress((i - 1) / total, text=f"Processing {i}/{total}: {filename}…")

            try:
                raw, original_path, detected_format = extractor.extract_metadata(
                    pdf_path,
                    first_pages,
                    last_pages,
                    "pdf",
                    context_prompt=context_prompt.strip() or None,
                )
                metadata = json.loads(strip_code_fences(raw))
                fmt = original_formats.get(Path(pdf_path).stem, "pdf") if preservica_mode else "pdf"
                writer.write_metadata(raw, pdf_path, fmt)

                title = metadata.get("Title") or "—"
                content_type = metadata.get("icaew:ContentType") or ""
                detail = f"{content_type} — {title}" if content_type else title
                st.write(f":white_check_mark: **{filename}** — {detail}")

                st.session_state.results.append(
                    {
                        "filename": filename,
                        "metadata": metadata,
                        "extracted_at": datetime.now().isoformat(),
                    }
                )
            except Exception as e:
                st.write(f":x: **{filename}** — {e}")
                st.session_state.errors.append({"filename": filename, "error": str(e)})

            progress.progress(i / total, text=f"Processed {i}/{total}: {filename}")

        n_ok  = len(st.session_state.results)
        n_err = len(st.session_state.errors)
        summary = f"Extraction complete — {n_ok} succeeded"
        if n_err:
            summary += f", {n_err} failed"
        ext_status.update(label=summary, state="complete" if n_ok else "error")

    progress_slot.empty()

    # Clean up working files after the run
    def _delete_dir_contents(folder: str) -> None:
        for p in Path(folder).iterdir():
            try:
                p.unlink() if p.is_file() else None
            except OSError:
                pass

    if preservica_mode:
        _delete_dir_contents(effective_output_dir)
    elif input_mode == "Select files":
        _delete_dir_contents(st.session_state.get("upload_tmp", ""))

    # Save CSV to disk if a path was provided
    if csv_output_path and os.path.exists(active_json_path):
        try:
            JSONToCSVConverter().convert_json_to_csv(active_json_path, csv_output_path)
            st.info(f"CSV saved to `{csv_output_path}`")
        except Exception as e:
            st.warning(f"Could not save CSV: {e}")

    if (auto_descriptive or auto_xip) and st.session_state.results:
        apply_to_preservica(active_json_path, auto_descriptive, auto_xip, overwrite_existing)


# ── results ───────────────────────────────────────────────────────────────────

results   = st.session_state.get("results", [])
errors    = st.session_state.get("errors",  [])
json_path = st.session_state.get("json_path")

if not results and not errors:
    st.stop()

for err in errors:
    st.error(f"**{err['filename']}** — {err['error']}")

if not results:
    st.stop()

result_word = "file" if len(results) == 1 else "files"
st.success(f"Extracted metadata for {len(results)} {result_word}")

if json_output_path and json_path == json_output_path:
    st.info(f"JSON saved to `{json_output_path}`")

st.divider()

for result in results:
    meta = result["metadata"]
    with st.expander(f"📄 {result['filename']}", expanded=True):

        # Top row: title + key fields
        st.markdown("**Title**")
        st.write(meta.get("Title") or "—")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Content type**")
            st.write(meta.get("icaew:ContentType") or "—")
        with col2:
            st.markdown("**Date**")
            st.write(meta.get("Date") or "—")
        with col3:
            st.markdown("**Format**")
            st.write(meta.get("Format") or "—")

        # Creator / Publisher
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Creator**")
            creators = meta.get("Creator", [])
            st.write(" · ".join(creators) if isinstance(creators, list) else creators or "—")
        with col_b:
            st.markdown("**Publisher**")
            st.write(meta.get("Publisher") or "—")

        # Description
        desc = meta.get("Description", "")
        if desc:
            st.markdown("**Description**")
            st.write(desc)

        # Subjects
        subjects = meta.get("Subject") or []
        if subjects:
            st.markdown("**Subjects**")
            st.markdown("  ›  ".join(f"`{s}`" for s in subjects))

        # Identifiers / Relation
        identifiers = meta.get("Identifier") or []
        relation    = meta.get("Relation")    or []
        if identifiers or relation:
            col_c, col_d = st.columns(2)
            with col_c:
                if identifiers:
                    st.markdown("**Identifiers**")
                    st.write(
                        " · ".join(identifiers)
                        if isinstance(identifiers, list)
                        else identifiers
                    )
            with col_d:
                if relation:
                    st.markdown("**Relation / Series**")
                    st.write(
                        " · ".join(relation)
                        if isinstance(relation, list)
                        else relation
                    )

        # Notes
        notes = meta.get("icaew:Notes", "")
        if notes:
            st.markdown("**Notes**")
            st.write(notes)

        # Full JSON
        with st.expander("Full JSON"):
            st.json(meta)


# ── downloads ─────────────────────────────────────────────────────────────────

st.divider()
st.subheader("Download")

download_filename = (
    os.path.basename(json_output_path)
    if json_output_path
    else "metadata.json"
)
csv_filename = Path(download_filename).stem + ".csv"

col1, col2 = st.columns(2)

with col1:
    if json_path and os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            json_bytes = f.read()
    else:
        json_bytes = "{}"

    st.download_button(
        "⬇ Download JSON",
        data=json_bytes,
        file_name=download_filename,
        mime="application/json",
        use_container_width=True,
    )

with col2:
    if json_path and os.path.exists(json_path):
        try:
            csv_data = generate_csv_from_json(json_path)
            st.download_button(
                "⬇ Download CSV",
                data=csv_data,
                file_name=csv_filename,
                mime="text/csv",
                use_container_width=True,
            )
        except Exception as e:
            st.warning(f"CSV generation failed: {e}")


# ── apply to Preservica ───────────────────────────────────────────────────────

if st.session_state.get("can_apply") and json_path and os.path.exists(json_path):
    st.divider()
    st.subheader("Apply to Preservica")

    apply_results = st.session_state.get("apply_results")
    if apply_results is None:
        st.caption("Write the extracted metadata back to the assets it was extracted from.")
        m_descriptive, m_xip, m_overwrite = preservica_update_options("manual", "")
        if st.button(
            "Update Preservica",
            type="primary",
            use_container_width=True,
            disabled=not (m_descriptive or m_xip),
        ):
            apply_to_preservica(json_path, m_descriptive, m_xip, m_overwrite)
            st.rerun()
    else:
        applied = [r for r in apply_results if r["status"] == "applied"]
        skipped = [r for r in apply_results if r["status"] == "skipped"]
        failed  = [r for r in apply_results if r["status"] == "error"]
        if applied:
            st.success(f"Updated {len(applied)} asset(s) in Preservica")
        for r in applied + skipped:
            if "skipped" in r["message"]:
                st.warning(f"`{r['asset_ref']}` — {r['message']}")
        for r in failed:
            st.error(f"**{r['filename']}** — {r['message']}")

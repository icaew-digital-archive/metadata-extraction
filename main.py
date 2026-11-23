"""
Metadata extraction tool for PDF files using OpenAI's API.
Extracts metadata following conventions defined in a YAML profile (see profiles/).
"""

import argparse
import json
import sys
import os
from typing import Dict, List, Optional, Tuple
from metadata_extractor import MetadataExtractor, PreparedDocument
from pipeline import run_pipeline
from convert_documents import CONVERTIBLE_FORMATS
from media import find_video_for_subtitles, load_media_mapping, video_overrides, video_source_note
from json_metadata_writer import JSONMetadataWriter
from config import DEFAULT_MODEL, DEFAULT_WORKERS, MAX_WORKERS, get_video_source_note


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description='Extract metadata from PDF files using a configurable profile.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Process a single PDF file:
  python main.py --file path/to/document.pdf -j output.json
  # or
  python main.py -f path/to/document.pdf -j output.json

  # Process all PDFs in a directory:
  python main.py --folder path/to/pdf/directory -j output.json
  # or
  python main.py -d path/to/pdf/directory -j output.json

  # Process first 3 pages of all PDFs in a directory:
  python main.py --folder path/to/pdf/directory --first 3 -j output.json
  # or
  python main.py -d path/to/pdf/directory -p 3 -j output.json

  # Process last 2 pages of all PDFs in a directory:
  python main.py --folder path/to/pdf/directory --last 2 -j output.json
  # or
  python main.py -d path/to/pdf/directory -l 2 -j output.json

  # With custom context for the extraction prompt:
  python main.py --folder path/to/pdf/directory -j output.json --context-prompt "What follows is a series of photos showing Chartered Accountant's Hall"

  # Use a different model:
  python main.py --folder path/to/pdf/directory -j output.json --model gpt-6.2-astra

  # Process one document at a time (shows the full metadata for each):
  python main.py --folder path/to/pdf/directory -j output.json --workers 1

  # Process 64 documents at a time (default is 32):
  python main.py --folder path/to/pdf/directory -j output.json --workers 64

  # Resume an interrupted run (skip files already in output.json):
  python main.py --folder path/to/pdf/directory -j output.json --skip-existing

  # Disable subject classification (Subject field will be empty):
  python main.py --folder path/to/pdf/directory -j output.json --no-subjects

  # Convert JSON to CSV after processing:
  python json_to_csv_converter.py output.json output.csv
'''
    )

    # Create a mutually exclusive group for file/folder arguments
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--file', '-f',
                             help='Path to a single PDF file to process')
    input_group.add_argument('--folder', '-d',
                             help='Path to a directory containing PDF files to process')

    parser.add_argument('--first', '-p',
                        type=int,
                        default=0,
                        help='Number of pages to include from the start (default: 0, meaning no limit)')
    parser.add_argument('--last', '-l',
                        type=int,
                        default=0,
                        help='Number of pages to include from the end (default: 0, meaning no limit)')
    parser.add_argument('--json-file', '-j',
                        required=True,
                        help='JSON file to write metadata to')

    parser.add_argument('--context-prompt',
                        type=str,
                        default=None,
                        help='Custom context to prepend to the extraction prompt (e.g. "What follows is a series of photos showing Chartered Accountant\'s Hall")')

    parser.add_argument('--no-subjects',
                        action='store_true',
                        help='Disable subject classification (Subject field will always be empty)')

    parser.add_argument('--profile',
                        type=str,
                        default=None,
                        help='Path to a YAML profile file (default: profiles/icaew.yaml). '
                             'Can be a filename inside profiles/ (e.g., "default") or a full path.')

    parser.add_argument('--model',
                        type=str,
                        default=None,
                        help=f'OpenAI model to use (default: {DEFAULT_MODEL}). '
                             'Options include gpt-6.2-sol, gpt-6.2-astra, gpt-6-luna, gpt-5.')

    parser.add_argument('--workers', '-w',
                        type=int,
                        default=DEFAULT_WORKERS,
                        help=f'Number of documents to process at the same time '
                             f'(default: {DEFAULT_WORKERS}, maximum: {MAX_WORKERS}). '
                             f'Use 1 to process one at a time and see the full metadata for each.')

    parser.add_argument('--skip-existing',
                        action='store_true',
                        help='Skip files that already have a record in the JSON file '
                             '(useful for resuming an interrupted run)')

    return parser


def load_format_mapping(folder: str) -> Dict[str, str]:
    """Read format_mapping.json (written by convert_documents.py) from a folder.

    Keys are normalised to absolute paths so lookups work however the folder
    path was written (e.g. "./downloads" vs "downloads").
    """
    mapping_file = os.path.join(folder, "format_mapping.json")
    if not os.path.exists(mapping_file):
        return {}
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            raw = json.load(f)
    except Exception as e:
        print(f"Warning: Could not read format mapping: {e}")
        return {}
    mapping = {}
    for key, fmt in raw.items():
        # Keys may be bare filenames (current) or paths (older mapping files)
        path = key if os.path.dirname(key) else os.path.join(folder, key)
        mapping[os.path.abspath(path)] = fmt
    return mapping


# Formats a PDF may have been converted from (see convert_documents.py)
ORIGINAL_FORMATS = CONVERTIBLE_FORMATS


def detect_original_format(pdf_path: str, format_mapping: Dict[str, str]) -> str:
    """Return the format of the file a PDF was converted from, or 'pdf'."""
    fmt = format_mapping.get(os.path.abspath(pdf_path))
    if fmt:
        print(f"Detected original format from mapping: {fmt}")
        return fmt
    # Fallback: look for a source file with the same name next to the PDF
    base_name = os.path.splitext(pdf_path)[0]
    for ext in ORIGINAL_FORMATS:
        if os.path.exists(base_name + ext):
            print(f"Detected original format: {ext[1:]}")
            return ext[1:]
    return 'pdf'


def get_pdf_files(file_path: Optional[str] = None, folder_path: Optional[str] = None) -> List[str]:
    """
    Get a list of PDF files from a file path or directory path.

    Args:
        file_path (str, optional): Path to a PDF file
        folder_path (str, optional): Path to a directory

    Returns:
        list: List of paths to PDF files
    """
    if file_path:
        if not file_path.lower().endswith('.pdf'):
            print(f"Warning: {file_path} is not a PDF file")
            return []
        if not os.path.isfile(file_path):
            print(f"Error: {file_path} is not a valid file")
            return []
        return [file_path]

    if folder_path:
        if not os.path.isdir(folder_path):
            print(f"Error: {folder_path} is not a valid directory")
            return []

        pdf_files = []
        for file in sorted(os.listdir(folder_path)):
            if file.lower().endswith('.pdf'):
                full_path = os.path.join(folder_path, file)
                pdf_files.append(full_path)
                print(f"Found PDF: {file}")  # Debug log
        print(f"\nTotal PDFs found in directory: {len(pdf_files)}")  # Debug log
        return pdf_files

    return []


def main() -> None:
    """Main entry point for the metadata extraction tool."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Get list of PDF files to process
        pdf_files = get_pdf_files(args.file, args.folder)
        if not pdf_files:
            print("No PDF files found to process")
            sys.exit(1)

        total_files = len(pdf_files)
        print(f"\nStarting to process {total_files} PDF file(s)")

        # Resolve profile path
        profile_path = None
        if args.profile:
            p = args.profile
            if not os.path.isabs(p) and not os.path.exists(p):
                # Try as a name inside profiles/
                candidate = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles", p if p.endswith((".yaml", ".yml")) else p + ".yaml")
                if os.path.exists(candidate):
                    p = candidate
            profile_path = p

        # Initialize metadata extractor and writer
        extractor = MetadataExtractor(include_subjects=not args.no_subjects, profile_path=profile_path,
                                      model=args.model)
        print(f"Model: {extractor.model}")
        writer = JSONMetadataWriter(args.json_file, profile_path=profile_path)

        already_done = set()
        if args.skip_existing:
            already_done = {os.path.abspath(r.get('file_path', '')) for r in writer.get_records()}

        # Work out what to do before any requests are sent
        format_mappings: Dict[str, Dict[str, str]] = {}
        jobs = []  # (index, pdf_path, original_format, video or None)
        media_mappings: Dict[str, dict] = {}
        video_note_template = get_video_source_note(profile_path)
        skipped_count = 0
        for index, pdf_path in enumerate(pdf_files, 1):
            if os.path.abspath(pdf_path) in already_done:
                print(f"[{index}/{total_files}] Skipping (already in JSON): {pdf_path}")
                skipped_count += 1
                continue
            folder = os.path.dirname(pdf_path)
            if folder not in format_mappings:
                format_mappings[folder] = load_format_mapping(folder)
            original_format = detect_original_format(pdf_path, format_mappings[folder])
            if folder not in media_mappings:
                media_mappings[folder] = load_media_mapping(folder)
            # Subtitles that belong to a video: the record describes the video
            video = find_video_for_subtitles(pdf_path, original_format, media_mappings[folder])
            if video:
                print(f"[{index}/{total_files}] Subtitles of a video ({video.get('video_filename') or video['video_format']}): "
                      f"will be described as the video")
            jobs.append((index, pdf_path, original_format, video))

        workers = max(1, min(args.workers, MAX_WORKERS, len(jobs)))
        if args.workers > MAX_WORKERS:
            print(f"Note: --workers is capped at {MAX_WORKERS}")
        print(f"Workers: {workers}")

        def prepare(job) -> PreparedDocument:
            """Local stage, one document at a time: check the PDF and cut it to the page range."""
            index, pdf_path, _original_format, video = job
            print(f"[{index}/{total_files}] Preparing: {pdf_path}")
            if video:
                # Subtitles are small: always use the whole transcript, ignoring page limits
                return extractor.prepare(pdf_path, 0, 0)
            return extractor.prepare(pdf_path, args.first, args.last)

        def process(job, prepared: PreparedDocument) -> str:
            """OpenAI stage, several at a time: extract and save one document; returns its title."""
            index, pdf_path, original_format, video = job
            note = video_source_note(video, video_note_template) if video else None
            metadata = extractor.extract(prepared, context_prompt=args.context_prompt, source_note=note)
            if workers == 1:
                # Full output is only readable when documents run one at a time
                print(f"\n[{index}/{total_files}] Extracted Metadata:")
                print(metadata)
            if video:
                # Described as the video: its format and DC type, whatever the model returned
                writer.write_metadata(metadata, pdf_path, video['video_format'], model=extractor.model,
                                      overrides=video_overrides(video),
                                      source_format=original_format)
            else:
                writer.write_metadata(metadata, pdf_path, original_format, model=extractor.model)
            try:
                return json.loads(metadata).get('Title') or ''
            except (ValueError, AttributeError):
                return ''

        processed_count = 0
        failed_files: List[Tuple[str, str]] = []  # List of (file_path, error_message) tuples
        interrupted = False

        def on_result(job, title, error) -> None:
            """Count and print the outcome of one finished document."""
            nonlocal processed_count
            index, pdf_path, _, _ = job
            if error is None:
                processed_count += 1
                done = processed_count + len(failed_files)
                print(f"[{index}/{total_files}] Done ({done}/{len(jobs)}): "
                      f"{os.path.basename(pdf_path)}" + (f" - {title}" if title else ""))
            else:
                failed_files.append((pdf_path, str(error)))
                print(f"[{index}/{total_files}] Error processing {pdf_path}: {error}")

        def on_interrupt() -> None:
            nonlocal interrupted
            interrupted = True
            print("\nInterrupted: not starting any more documents. Waiting for those already "
                  "in progress to finish (press Ctrl+C again to stop immediately)...")

        try:
            run_pipeline(jobs, prepare, process, on_result, workers,
                         cleanup=lambda prepared: prepared.cleanup(), on_interrupt=on_interrupt)
        except KeyboardInterrupt:
            pass  # summary below reports what was and wasn't done

        # Print detailed summary
        print(f"\nProcessing {'stopped early' if interrupted else 'complete'}:")
        print(f"- Total files found: {total_files}")
        print(f"- Successfully processed: {processed_count}")
        if args.skip_existing:
            print(f"- Skipped (already in JSON): {skipped_count}")
        print(f"- Failed to process: {len(failed_files)}")
        if interrupted:
            print(f"- Not started: {len(jobs) - processed_count - len(failed_files)} "
                  "(re-run with --skip-existing to continue)")
        print(f"- Metadata written to: {args.json_file}")

        if failed_files:
            print("\nFailed files:")
            for file_path, error in failed_files:
                print(f"  - {os.path.basename(file_path)}: {error}")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

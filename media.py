"""
Videos described from their subtitles.

Preservica video assets can hold the video and its subtitle file (.srt/.vtt)
side by side. The subtitles are converted to PDF and used as the source for
metadata extraction, but the record describes the video: its Format is the
video's file format and its Type is "Moving Image".

How a subtitle file is linked to its video:
  1. media_mapping.json, written by download_preservica_assets.py next to the
     downloaded files (works even when the video itself was not downloaded)
  2. otherwise, a video file with the same name in the same folder
     (e.g. talk.srt and talk.mp4)
"""

import json
import os
from typing import Dict, Optional

VIDEO_EXTENSIONS = {'.mp4', '.m4v', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.mpg', '.mpeg', '.mxf'}
SUBTITLE_EXTENSIONS = {'.srt', '.vtt'}
MEDIA_MAPPING_FILE = 'media_mapping.json'

# Dublin Core Type for videos (the term used by the profiles' Type rules)
VIDEO_TYPE = 'Moving Image'


def video_overrides(video: dict) -> dict:
    """Fields set by the code for a video described from its subtitles, whatever the model returned.

    Relation is always empty: subtitles carry no series information.
    """
    return {'Type': VIDEO_TYPE, 'Format': video['video_format'], 'Relation': []}


def load_media_mapping(folder: str) -> Dict[str, dict]:
    """Read media_mapping.json from a folder: {subtitle file stem: {"video_format", "video_filename"}}."""
    path = os.path.join(folder, MEDIA_MAPPING_FILE)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not read {MEDIA_MAPPING_FILE}: {e}")
        return {}


def save_media_mapping(folder: str, entries: Dict[str, dict]) -> None:
    """Merge entries into media_mapping.json in a folder."""
    if not entries:
        return
    mapping = load_media_mapping(folder)
    mapping.update(entries)
    with open(os.path.join(folder, MEDIA_MAPPING_FILE), 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2)


def find_video_for_subtitles(pdf_path: str, original_format: Optional[str],
                             media_mapping: Optional[Dict[str, dict]] = None) -> Optional[dict]:
    """
    If pdf_path was converted from a subtitle file that belongs to a video, return
    {"video_format": "mp4", "video_filename": "..."}; otherwise None.
    """
    if not original_format or '.' + original_format.lower() not in SUBTITLE_EXTENSIONS:
        return None
    folder, name = os.path.split(pdf_path)
    stem = os.path.splitext(name)[0]
    mapping = load_media_mapping(folder) if media_mapping is None else media_mapping
    if stem in mapping and mapping[stem].get('video_format'):
        return mapping[stem]
    for entry in os.listdir(folder or '.'):
        entry_stem, ext = os.path.splitext(entry)
        if entry_stem == stem and ext.lower() in VIDEO_EXTENSIONS:
            return {'video_format': ext.lower().lstrip('.'), 'video_filename': entry}
    return None


def video_source_note(video: dict, template: str) -> str:
    """Fill the profile's video note template with this video's details."""
    return template.format(video_format=video.get('video_format', ''),
                           video_filename=video.get('video_filename', '') or 'unknown')

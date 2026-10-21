"""
Module for applying extracted metadata back to Preservica assets.

Builds OAI-DC and ICAEW XML fragments from the records written by
JSONMetadataWriter and attaches them to the asset each file was downloaded
from. The asset reference is taken from the filename, so assets must be
downloaded with --use-asset-ref.

Mirrors the behaviour of c_add_metadata_from_csv.py (descriptive metadata)
and d_update_xip_from_csv.py (entity title and description).
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

from pyPreservica import EntityAPI

OAI_DC = 'http://www.openarchives.org/OAI/2.0/oai_dc/'
DC = 'http://purl.org/dc/elements/1.1/'
XSI = 'http://www.w3.org/2001/XMLSchema-instance'
ICAEW = 'https://www.icaew.com/metadata/'
XIP = 'http://preservica.com/XIP/v7.6'

# ICAEW elements in the order c_add_metadata_from_csv.py writes them (CSV column order)
ICAEW_FIELDS = ['icaew:ContentType', 'icaew:InternalReference', 'icaew:Notes']

# Model output keys -> DC element names, in the order they are written
DC_FIELDS = {
    'Title': 'title',
    'Creator': 'creator',
    'Subject': 'subject',
    'Description': 'description',
    'Publisher': 'publisher',
    'Contributor': 'contributor',
    'Date': 'date',
    'Type': 'type',
    'Format': 'format',
    'Identifier': 'identifier',
    'Source': 'source',
    'Language': 'language',
    'Relation': 'relation',
    'Coverage': 'coverage',
    'Rights': 'rights',
}

UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)


def create_client() -> EntityAPI:
    """Create a Preservica client from the USERNAME/PASSWORD/TENANT/SERVER env vars."""
    creds = {k: os.getenv(k.upper()) for k in ('username', 'password', 'tenant', 'server')}
    missing = [k.upper() for k, v in creds.items() if not v]
    if missing:
        raise EnvironmentError(f"Missing Preservica credentials in .env: {', '.join(missing)}")
    return EntityAPI(**creds)


def asset_ref_from_filename(filename: str) -> Optional[str]:
    """Return the asset UUID from a file named <uuid>.<ext>, or None."""
    stem = Path(filename).stem
    return stem if UUID_RE.match(stem) else None


def _values(value: Any) -> List[str]:
    """Normalise a metadata value to a list of non-empty strings."""
    items = value if isinstance(value, list) else [value]
    return [str(v).strip() for v in items if v is not None and str(v).strip()]


def build_dc_xml(metadata: Dict[str, Any], original_format: Optional[str] = None) -> Optional[str]:
    """Build an oai_dc:dc XML string, or None if there are no values."""
    root = ET.Element('oai_dc:dc', {"xmlns:oai_dc": OAI_DC, "xmlns:dc": DC, "xmlns:xsi": XSI})
    for key, element in DC_FIELDS.items():
        value = metadata.get(key)
        if key == 'Format' and original_format:
            value = original_format.lower()
        for v in _values(value):
            ET.SubElement(root, f'dc:{element}').text = v
    return ET.tostring(root, encoding='unicode') if len(root) else None


def build_icaew_xml(metadata: Dict[str, Any]) -> Optional[str]:
    """Build an icaew:ICAEW XML string from icaew:* keys, or None if there are no values."""
    root = ET.Element('icaew:ICAEW', {"xmlns:icaew": ICAEW, "xmlns": XIP})
    extra = [k for k in metadata if k.startswith('icaew:') and k not in ICAEW_FIELDS]
    for key in ICAEW_FIELDS + extra:
        for v in _values(metadata.get(key)):
            ET.SubElement(root, key).text = v
    return ET.tostring(root, encoding='unicode') if len(root) else None


def apply_record(client: EntityAPI, record: Dict[str, Any], descriptive: bool = True,
                 xip: bool = True, overwrite: bool = False) -> Dict[str, str]:
    """
    Apply one JSONMetadataWriter record to its Preservica asset.

    Args:
        descriptive: Add the DC and ICAEW metadata fragments
        xip: Update the asset's XIP title and description from Title/Description
        overwrite: Replace existing DC/ICAEW fragments; when False, an asset that
            already has either is left unchanged (XIP is still updated if requested)

    Returns:
        Dict with keys: filename, asset_ref, status ('applied'|'skipped'|'error'), message
    """
    filename = record.get('asset_id', '')
    asset_ref = asset_ref_from_filename(filename)
    result = {'filename': filename, 'asset_ref': asset_ref or '', 'status': 'error', 'message': ''}

    if not asset_ref:
        result['message'] = "Filename is not a Preservica asset reference (enable 'Use asset reference in filenames')"
        return result

    metadata = record.get('metadata', {})
    done, skipped = [], []

    try:
        asset = client.asset(asset_ref)

        if descriptive:
            existing = set(asset.metadata.values())
            if not overwrite and existing & {OAI_DC, ICAEW}:
                skipped.append('DC/ICAEW (existing metadata)')
            else:
                fragments = [
                    ('DC', OAI_DC, build_dc_xml(metadata, record.get('original_format'))),
                    ('ICAEW', ICAEW, build_icaew_xml(metadata)),
                ]
                for label, schema, xml in fragments:
                    if not xml:
                        continue
                    if schema in existing:
                        asset = client.update_metadata(asset, schema, xml)
                    else:
                        asset = client.add_metadata(asset, schema, xml)
                    done.append(label)

        if xip:
            # Mirror the CSV workflow: entity title/description copy dc:title/dc:description
            title = metadata.get('Title')
            description = metadata.get('Description')
            changed = False
            if title and asset.title != title:
                asset.title = title
                changed = True
            if description and (asset.description or '') != description:
                asset.description = description
                changed = True
            if changed:
                client.save(asset)
                done.append('XIP')
            else:
                skipped.append('XIP (unchanged)')

        result['status'] = 'applied' if done else 'skipped'
        parts = []
        if done:
            parts.append(f"updated {', '.join(done)}")
        if skipped:
            parts.append(f"skipped {', '.join(skipped)}")
        result['message'] = '; '.join(parts)
    except Exception as e:
        result['message'] = str(e)

    return result

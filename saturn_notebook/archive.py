import json
import os
import zipfile
from typing import Any, Dict, Optional


ARCHIVE_MANIFEST = '.saturn-archive.json'
ARCHIVE_MANIFEST_KIND = 'saturn-notebook-external-archive'


def archive_manifest(fn: str) -> Dict[str, Any]:
    return {
        'kind': ARCHIVE_MANIFEST_KIND,
        'version': 1,
        'notebook': os.path.basename(fn),
    }


def archive_manifest_json(fn: str) -> str:
    return json.dumps(archive_manifest(fn), sort_keys=True) + '\n'


def read_archive_manifest(external: str) -> Optional[Dict[str, Any]]:
    try:
        with zipfile.ZipFile(external) as zf:
            manifest = json.loads(zf.read(ARCHIVE_MANIFEST).decode('utf-8'))
    except (KeyError, OSError, ValueError, zipfile.BadZipFile):
        return None
    return manifest if isinstance(manifest, dict) else None


def validate_existing_archive(fn: str, external: str) -> None:
    if not external or not os.path.exists(external):
        return

    manifest = read_archive_manifest(external)
    if not manifest:
        raise ValueError(
            f"Refusing to overwrite external archive without Saturn manifest: {external}. "
            "Use --force-external to replace it."
        )
    if manifest.get('kind') != ARCHIVE_MANIFEST_KIND:
        raise ValueError(
            f"Refusing to overwrite external archive with unrecognized Saturn manifest: {external}. "
            "Use --force-external to replace it."
        )
    notebook_name = manifest.get('notebook')
    if notebook_name and notebook_name != os.path.basename(fn):
        raise ValueError(
            f"Refusing to overwrite external archive for {notebook_name}: {external}. "
            "Use --force-external to replace it."
        )

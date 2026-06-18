import json
import os
import zipfile
from typing import Any, Dict, Optional


ARCHIVE_MANIFEST = '.saturn-archive.json'
ARCHIVE_MANIFEST_KIND = 'saturn-notebook-external-archive'


def sibling_archive(fn: str, external: str) -> bool:
    return os.path.abspath(os.path.dirname(fn) or '.') == os.path.abspath(os.path.dirname(external) or '.')


def archive_manifest(fn: str, external: Optional[str] = None) -> Dict[str, Any]:
    manifest = {
        'kind': ARCHIVE_MANIFEST_KIND,
        'version': 1,
        'notebook': os.path.basename(fn),
    }
    if external is None or not sibling_archive(fn, external):
        manifest['notebook_path'] = os.path.abspath(fn)
    return manifest


def archive_manifest_json(fn: str, external: Optional[str] = None) -> str:
    return json.dumps(archive_manifest(fn, external), sort_keys=True) + '\n'


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
    if manifest.get('version') != 1 or not notebook_name or os.path.basename(notebook_name) != notebook_name:
        raise ValueError(
            f"Refusing to overwrite external archive with incomplete Saturn manifest: {external}. "
            "Use --force-external to replace it."
        )
    if notebook_name != os.path.basename(fn):
        raise ValueError(
            f"Refusing to overwrite external archive for {notebook_name}: {external}. "
            "Use --force-external to replace it."
        )
    notebook_path = manifest.get('notebook_path')
    if notebook_path and notebook_path != os.path.abspath(fn) and not sibling_archive(fn, external):
        raise ValueError(
            f"Refusing to overwrite external archive for {notebook_path}: {external}. "
            "Use --force-external to replace it."
        )

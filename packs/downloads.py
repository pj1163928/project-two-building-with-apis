"""What "Download files" fetches for a pack, or for one of its items.

The Toolbox never downloads, hosts or proxies a file (PRD, Out of Scope).
These functions only list the provider's URLs, each with the path it takes
inside the zip, and the browser fetches and zips them
(static/js/bundle-download.js), as the library's Download bundle does.

Every file goes under its item's import path, so unzipping a pack's download
into a project puts each file where the manifest says the engine would. The
pack's zip also holds CREDITS.txt and the manifest itself at the top.
"""

import json
import posixpath
import re
from collections.abc import Iterable, Sequence
from typing import Any

from catalog.files import BUNDLE_MAX_BYTES, safe_path

from .manifest import manifest_item
from .models import Pack, PackItem

TOO_LARGE = (
    "That's over 2 GB, too big to zip in the browser. Download the items one by one instead."
)
NO_FILES = "There are no files to download: the providers listed none for these items."
FALLBACK = "Use the file links on the pack page instead."


def _zip_files(entries: Iterable[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    """[(folder, manifest file)] -> [{url, path, size}], each path unique in the zip."""
    seen: set[str] = set()
    files = []
    for folder, file in entries:
        if not file.get("url"):
            continue
        name = safe_path(str(file.get("filename") or "")) or posixpath.basename(file["url"])
        path = f"{folder}/{safe_path(name) or 'file'}" if folder else safe_path(name) or "file"
        stem, ext = posixpath.splitext(path)
        number = 2
        while path in seen:
            path, number = f"{stem}-{number}{ext}", number + 1
        seen.add(path)
        files.append({"url": file["url"], "path": path, "size": file.get("size")})
    return files


def _too_large(files: Sequence[dict[str, Any]]) -> bool:
    return sum(file["size"] or 0 for file in files) > BUNDLE_MAX_BYTES


def _name(*parts: str) -> str:
    name = "_".join(part for part in parts if part)
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.") or "download"


def _bundle(
    *, zip_name: str, provider: str, files: list, extras: list, zip: bool
) -> dict[str, Any]:
    if not files:
        return {"error": NO_FILES}
    if _too_large(files):
        return {"error": TOO_LARGE}
    return {
        "zip_name": zip_name,
        "provider": provider,
        "files": files,
        "extras": extras,
        "zip": zip,
        "fallback": FALLBACK,
    }


def pack_download(
    pack: Pack, items: Sequence[PackItem], *, manifest: dict, credits_text: str
) -> dict[str, Any]:
    """The whole pack as the browser's zip needs it, or {"error": message}.

    Each item's chosen variant's files sit under its import path. CREDITS.txt
    and `<slug>.axcenity-pack.json` (the manifest) sit at the top. Over 2 GB,
    or with no files at all, it's an error the page shows instead.
    """
    entries = []
    for item in items:
        export = manifest_item(item)
        folder = safe_path(export["import_path"])
        entries += [(folder, file) for file in export["files"]]
    extras = [
        {"path": "CREDITS.txt", "text": credits_text},
        {
            "path": f"{pack.slug}.axcenity-pack.json",
            "text": json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        },
    ]
    return _bundle(
        zip_name=f"{_name(pack.slug)}.zip",
        provider="the providers",
        files=_zip_files(entries),
        extras=extras,
        zip=True,
    )


def item_download(item: PackItem, *, credits_text: str) -> dict[str, Any]:
    """One item's chosen variant, or {"error": message}.

    A single file is saved as it is. Several are zipped under the item's
    import path, with the item's CREDITS.txt beside them.
    """
    export = manifest_item(item)
    folder = safe_path(export["import_path"])
    files = _zip_files((folder, file) for file in export["files"])
    asset = item.asset
    return _bundle(
        zip_name=f"{_name(asset.external_id, export['variant'] or '')}.zip",
        provider=asset.get_provider_display(),
        files=files,
        extras=[
            {"path": f"{folder}/CREDITS.txt" if folder else "CREDITS.txt", "text": credits_text}
        ],
        zip=len(files) > 1,
    )

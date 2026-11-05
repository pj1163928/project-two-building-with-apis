"""The provider-neutral asset record the Toolbox works with.

Each provider's `search_records()` turns its own API's JSON into these, so
Discover (and later the library) never needs to know a response shape.
"""

from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlsplit

from .http import ProviderError

# The four asset kinds, in the order Discover shows them.
KINDS = ("texture", "hdri", "model", "sound")

CC0_LICENSE = "CC0"
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"


@dataclass(frozen=True)
class VariantFile:
    """One downloadable file: the provider's URL, never downloaded or copied."""

    url: str
    filename: str
    size: int | None = None  # bytes; None when the provider doesn't say


@dataclass(frozen=True)
class Variant:
    """One way to download an asset, e.g. "2K JPG": a label and its files."""

    label: str
    files: tuple[VariantFile, ...]

    @property
    def total_size(self) -> int | None:
        """The files' combined size in bytes, or None if any size is unknown."""
        sizes = [file.size for file in self.files]
        return None if None in sizes else sum(sizes)

    def as_dict(self) -> dict:
        """The variant as plain JSON data, the shape Asset.variants stores."""
        return {
            "label": self.label,
            "files": [
                {"url": file.url, "filename": file.filename, "size": file.size}
                for file in self.files
            ],
            "total_size": self.total_size,
        }


@dataclass(frozen=True)
class AssetRecord:
    """One asset as a provider describes it, ready to show or save.

    Search results leave `variants` empty; fetch_record() fills it in.
    """

    provider: str  # the provider module's KEY, e.g. "polyhaven"
    external_id: str  # the provider's own ID or slug
    kind: str  # one of KINDS
    title: str
    author: str
    thumbnail_url: str  # the provider's URL; never downloaded or copied
    license: str  # e.g. "CC0" or "CC BY 4.0"
    license_url: str
    attribution: str
    source_url: str  # the asset's page on the provider's site
    tags: tuple[str, ...] = ()
    preview_url: str = ""  # a sound's playable audio (the provider's URL, streamed, never copied)
    variants: tuple[Variant, ...] = ()  # the download options, from fetch_record() only


def items_in(data: object, key: str, provider: str) -> list[dict]:
    """Return the list of result objects under `key` in a decoded response.

    A body that isn't the expected shape becomes a ProviderError with a safe
    message, and any entry that isn't an object is dropped, so a provider's
    malformed answer can never crash a page.
    """
    items = data.get(key, []) if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ProviderError(f"{provider} sent back results the Toolbox couldn't read.")
    return [item for item in items if isinstance(item, dict)]


def text(value: object) -> str:
    """A provider value as display text: strings are trimmed, anything else is ''."""
    return value.strip() if isinstance(value, str) else ""


def byte_size(value: object) -> int | None:
    """A provider's file size in bytes, or None when it's missing or not a whole number."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def file_name(url: str, fallback: str = "") -> str:
    """A file URL's file name, else `fallback`.

    That's its `file=` query value (ambientCG's downloads), or the last part
    of its path when that has an extension. A bare path such as `/get` isn't
    a file name.
    """
    parts = urlsplit(url)
    named = parse_qs(parts.query).get("file", [""])[0].strip()
    last = unquote(parts.path.rsplit("/", 1)[-1]).strip()
    return named or (last if "." in last.strip(".") else "") or fallback


def tag_names(values: object) -> tuple[str, ...]:
    """Provider tags as a tuple of non-blank strings.

    They're kept as the provider wrote them; the Toolbox normalizes them
    when it stores an asset (catalog.tags.normalize_tag).
    """
    if not isinstance(values, list):
        return ()
    names = (value.get("name") if isinstance(value, dict) else value for value in values)
    return tuple(name for name in map(text, names) if name)

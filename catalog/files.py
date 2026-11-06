"""Telling an asset's downloadable files apart, and picking a member's bundle.

Every stored variant (Asset.variants) is described by its resolution ("2K"),
its format ("JPG", "glTF") and its package (loose maps, a bundle, an
archive, audio). Every file in it gets a role: the map it holds ("Normal
GL", "Roughness") or what else it is ("Scene", "Data"). The library drawer
shows these, and pick_bundle() uses them with a member's download defaults
(accounts.models.DownloadPreferences) to choose what "Download bundle"
fetches.

The Toolbox never downloads the files: the bundle is a list of the
provider's URLs, which the member's browser fetches and zips
(static/js/bundle-download.js).
"""

import posixpath
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

# Resolutions a member can choose as their default, smallest first.
RESOLUTIONS = ("1K", "2K", "4K", "8K")
RESOLUTION_CHOICES = [(value, value) for value in RESOLUTIONS]

# Each kind's formats a member can choose as their default: (key, label).
TEXTURE_FORMATS = [("jpg", "JPG"), ("png", "PNG"), ("exr", "EXR")]
HDRI_FORMATS = [("hdr", "HDR"), ("exr", "EXR")]
MODEL_FORMATS = [("gltf", "glTF"), ("blend", "Blend"), ("fbx", "FBX"), ("usd", "USD")]
SOUND_FORMATS = [("mp3", "MP3"), ("wav", "WAV"), ("ogg", "OGG"), ("flac", "FLAC")]

# The map types texture files are told apart by: (key, label, the name parts
# that mean it). Poly Haven names maps <slug>_<map>_<res>.<ext>.
MAP_TYPES = [
    ("color", "Color", ("diff", "diffuse", "col", "color", "albedo", "basecolor")),
    ("normal_gl", "Normal GL", ("nor_gl", "normal_gl", "nrm_gl", "normalgl")),
    ("normal_dx", "Normal DX", ("nor_dx", "normal_dx", "nrm_dx", "normaldx")),
    ("normal", "Normal", ("nor", "normal", "nrm")),
    ("rough", "Roughness", ("rough", "roughness")),
    ("metal", "Metalness", ("metal", "metallic", "metalness")),
    ("ao", "AO", ("ao", "occlusion", "ambientocclusion")),
    ("arm", "AO/Rough/Metal", ("arm",)),
    ("disp", "Displacement", ("disp", "displacement", "height")),
    ("bump", "Bump", ("bump",)),
    ("spec", "Specular", ("spec", "specular")),
    ("opacity", "Opacity", ("alpha", "opacity", "mask")),
    ("emission", "Emission", ("emission", "emissive")),
    ("translucency", "Translucency", ("translucent", "translucency", "sss")),
]
MAP_CHOICES = [(key, label) for key, label, _ in MAP_TYPES]
MAP_KEYS = tuple(key for key, _ in MAP_CHOICES)
MAP_LABELS = dict(MAP_CHOICES)
_MAP_BY_NAME = {name: key for key, _, names in MAP_TYPES for name in names}

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "exr", "hdr", "tif", "tiff", "webp"}
SCENE_EXTENSIONS = {"blend", "gltf", "glb", "fbx", "usd", "usda", "usdc", "usdz", "mtlx", "obj"}
AUDIO_EXTENSIONS = {"mp3", "wav", "ogg", "flac", "aiff", "aif", "m4a", "opus"}
ARCHIVE_EXTENSIONS = {"zip", "7z", "rar"}

# How formats are named in variant labels, by key; anything else is upper case.
FORMAT_LABELS = {"gltf": "glTF", "blend": "Blend", "materialx": "MaterialX", "mtlx": "MaterialX"}
# When a member's format isn't there, the next best, by kind.
FORMAT_FALLBACKS = {
    "texture": ("jpg", "png", "exr"),
    "hdri": ("hdr", "exr", "jpg"),
    "model": ("gltf", "blend", "fbx", "usd"),
    "sound": ("mp3", "ogg", "wav", "flac"),
}
# The browser builds the bundle in memory, so a bigger one is refused.
BUNDLE_MAX_BYTES = 2 * 1024**3

_RESOLUTION = re.compile(r"\b(\d{1,2})\s*k\b", re.I)


class Preferences(Protocol):
    """A member's download defaults (accounts.models.DownloadPreferences)."""

    resolution: str
    texture_format: str
    hdri_format: str
    model_format: str
    sound_format: str
    maps: list[str]

    def format_for(self, kind: str) -> str: ...


@dataclass(frozen=True)
class FileInfo:
    """One downloadable file with its role: a map type, or what else it is."""

    url: str
    filename: str
    size: int | None
    map_key: str  # one of MAP_KEYS, or "" for a file that isn't a map
    role: str  # "Normal GL", "Scene", "Data", "Archive", "Audio", "Image" or ""


@dataclass(frozen=True)
class VariantInfo:
    """One stored variant, told apart by resolution, format and package."""

    label: str
    resolution: str  # "2K", or "" when the label gives none
    format_key: str  # "jpg", "gltf"…, or "" when unknown
    format_label: str  # "JPG", "glTF"…
    package: str  # "maps", "bundle", "archive", "audio" or "files"
    files: tuple[FileInfo, ...]

    @property
    def package_label(self) -> str:
        return PACKAGE_LABELS[self.package]

    @property
    def resolution_value(self) -> int:
        """The resolution in K as a number (0 when there's none), for sorting."""
        return int(self.resolution[:-1]) if self.resolution else 0

    @property
    def total_size(self) -> int | None:
        sizes = [file.size for file in self.files]
        return None if None in sizes else sum(sizes)

    @property
    def map_labels(self) -> list[str]:
        """The map types among the files, in MAP_TYPES order."""
        keys = {file.map_key for file in self.files}
        return [label for key, label in MAP_CHOICES if key in keys]


PACKAGE_LABELS = {
    "maps": "Loose maps",
    "bundle": "Bundle",
    "archive": "Archive",
    "audio": "Audio",
    "files": "Files",
}


def extension(filename: str) -> str:
    """A file name's extension, lower case and without the dot ("" when none)."""
    _, ext = posixpath.splitext(filename.lower())
    return ext[1:]


def map_type(filename: str, external_id: str = "") -> str:
    """The map type a texture file holds (one of MAP_KEYS), or "" if it isn't a map.

    Only the part of the name between the asset's ID and the resolution is
    read, so "rusty_metal_02_rough_2k.jpg" is Roughness although the asset's
    own name says "metal".
    """
    if extension(filename) not in IMAGE_EXTENSIONS:
        return ""
    stem = posixpath.splitext(posixpath.basename(filename.replace("\\", "/")))[0].lower()
    slug = external_id.lower()
    if slug and stem.startswith(slug):
        stem = stem[len(slug) :]
    parts = [part for part in re.split(r"[_\-\s.]+", stem) if part]
    if parts and _RESOLUTION.fullmatch(parts[-1]):
        parts.pop()
    # Read from the end: the map comes last, and "nor_gl" is two parts.
    for size in (2, 1):
        name = "_".join(parts[-size:]) if len(parts) >= size else ""
        if name in _MAP_BY_NAME:
            return _MAP_BY_NAME[name]
    return ""


def _role(filename: str, map_key: str) -> str:
    ext = extension(filename)
    if map_key:
        return MAP_LABELS[map_key]
    if ext in SCENE_EXTENSIONS:
        return "Scene"
    if ext == "bin":
        return "Data"
    if ext in ARCHIVE_EXTENSIONS:
        return "Archive"
    if ext in AUDIO_EXTENSIONS:
        return "Audio"
    if ext in IMAGE_EXTENSIONS:
        return "Image"
    return ""


def describe_variant(variant: Mapping[str, Any], external_id: str = "") -> VariantInfo:
    """One stored variant ({"label", "files": [{"url", "filename", "size"}]}) described.

    The resolution and format come from the label ("2K JPG", ambientCG's "2K
    JPG", Poly Haven's "1K glTF"); a label without a format ("4K", an
    ambientCG HDRI) takes its first file's extension.
    """
    label = str(variant.get("label", ""))
    files = []
    for raw in variant.get("files") or []:
        if not isinstance(raw, Mapping):
            continue
        filename = str(raw.get("filename", ""))
        key = map_type(filename, external_id)
        size = raw.get("size")
        files.append(
            FileInfo(
                url=str(raw.get("url", "")),
                filename=filename,
                size=size if isinstance(size, int) and not isinstance(size, bool) else None,
                map_key=key,
                role=_role(filename, key),
            )
        )
    match = _RESOLUTION.search(label)
    resolution = f"{int(match.group(1))}K" if match else ""
    format_text = " ".join(_RESOLUTION.sub(" ", label.replace("-", " ")).split())
    if not format_text and files:
        format_text = extension(files[0].filename)
    format_key = format_text.lower().replace(" ", "")
    format_label = FORMAT_LABELS.get(format_key) or (
        format_text if format_text != format_text.lower() else format_text.upper()
    )
    return VariantInfo(
        label=label,
        resolution=resolution,
        format_key="mtlx" if format_key == "materialx" else format_key,
        format_label=format_label,
        package=_package(files),
        files=tuple(files),
    )


def _package(files: Sequence[FileInfo]) -> str:
    extensions = {extension(file.filename) for file in files}
    if extensions & SCENE_EXTENSIONS:
        return "bundle"
    if extensions and extensions <= ARCHIVE_EXTENSIONS:
        return "archive"
    if extensions and extensions <= AUDIO_EXTENSIONS:
        return "audio"
    if extensions and extensions <= IMAGE_EXTENSIONS:
        return "maps"
    return "files"


def describe_variants(
    variants: Iterable[Mapping[str, Any]], external_id: str = ""
) -> list[VariantInfo]:
    """Every stored variant described, in the order the provider listed them."""
    return [describe_variant(variant, external_id) for variant in variants]


@dataclass(frozen=True)
class FileFilters:
    """The choices the drawer's file filters offer for one asset."""

    resolutions: list[str]  # smallest first
    formats: list[tuple[str, str]]  # (key, label), in the order first listed


def file_filters(variants: Sequence[VariantInfo]) -> FileFilters:
    """The resolutions and formats an asset's variants come in, once each."""
    by_value = {variant.resolution_value: variant.resolution for variant in variants}
    resolutions = [by_value[value] for value in sorted(by_value) if value]
    formats = dict((variant.format_key, variant.format_label) for variant in variants)
    return FileFilters(resolutions=resolutions, formats=list(formats.items()))


@dataclass(frozen=True)
class Bundle:
    """What "Download bundle" fetches for one asset under a member's defaults.

    `variant` is the variant chosen (None when the asset has no files), and
    `files` the files taken from it: for loose maps only the member's map
    types, otherwise every file. `notes` say where the choice had to differ
    from the defaults.
    """

    variant: VariantInfo | None
    files: tuple[FileInfo, ...] = ()
    notes: tuple[str, ...] = field(default=())

    @property
    def total_size(self) -> int | None:
        sizes = [file.size for file in self.files]
        return None if None in sizes else sum(sizes)

    @property
    def too_large(self) -> bool:
        return (self.total_size or 0) > BUNDLE_MAX_BYTES

    @property
    def map_labels(self) -> list[str]:
        keys = {file.map_key for file in self.files}
        return [label for key, label in MAP_CHOICES if key in keys]

    def manifest(self, external_id: str) -> list[dict[str, Any]]:
        """The files as the browser's zip needs them: URL, path in the zip, size."""
        folder = safe_path(external_id) or "asset"
        seen: set[str] = set()
        entries = []
        for file in self.files:
            path = f"{folder}/{safe_path(file.filename) or 'file'}"
            stem, ext = posixpath.splitext(path)
            number = 2
            while path in seen:
                path, number = f"{stem}-{number}{ext}", number + 1
            seen.add(path)
            entries.append({"url": file.url, "path": path, "size": file.size})
        return entries

    def zip_name(self, external_id: str) -> str:
        """The bundle's file name, e.g. "blue_metal_plate_2K_JPG.zip"."""
        parts = [external_id]
        if self.variant:
            parts += [self.variant.resolution, self.variant.format_label]
        name = "_".join(part for part in parts if part)
        return f"{re.sub(r'[^A-Za-z0-9._-]+', '-', name).strip('-.') or 'bundle'}.zip"


def safe_path(path: str) -> str:
    """A provider's file name as a relative path that stays inside the zip's folder.

    Backslashes become "/", and empty, "." and ".." parts are dropped.
    """
    parts = [part for part in path.replace("\\", "/").split("/") if part not in ("", ".", "..")]
    return "/".join(parts)


def pick_bundle(kind: str, variants: Sequence[VariantInfo], prefs: Preferences) -> Bundle:
    """The bundle for an asset of `kind` under a member's download defaults.

    The format comes first: the member's format for the kind, else the next
    in FORMAT_FALLBACKS, else whatever is there. Then the resolution: the
    member's, else the nearest below it, else the nearest above. From loose
    maps only the member's map types are taken (files that aren't maps stay);
    a bundle or archive is taken whole, since its files belong together.
    """
    if not variants:
        return Bundle(variant=None)
    wanted_format = prefs.format_for(kind)
    order = [wanted_format, *FORMAT_FALLBACKS.get(kind, ())]
    rank = {key: index for index, key in enumerate(dict.fromkeys(order))}
    wanted_res = int(prefs.resolution[:-1]) if prefs.resolution else 0

    def score(variant: VariantInfo):
        res = variant.resolution_value
        if not res or not wanted_res:
            distance = (0, 0)
        elif res <= wanted_res:
            distance = (0, wanted_res - res)  # the member's, or the nearest below
        else:
            distance = (1, res - wanted_res)  # only then the nearest above
        return (rank.get(variant.format_key, len(rank)), distance)

    chosen = min(variants, key=score)
    files = chosen.files
    notes = []
    if chosen.format_key != wanted_format:
        notes.append(f"No {_format_label(kind, wanted_format)} here, so {chosen.format_label}.")
    if wanted_res and chosen.resolution and chosen.resolution != prefs.resolution:
        notes.append(f"No {prefs.resolution} here, so {chosen.resolution}, the nearest.")
    if chosen.package == "maps":
        wanted_maps = set(prefs.maps)
        kept = tuple(file for file in files if not file.map_key or file.map_key in wanted_maps)
        if kept != files:
            notes.append(f"{len(kept)} of {len(files)} maps, as your defaults choose.")
        files = kept
    return Bundle(variant=chosen, files=files, notes=tuple(notes))


def _format_label(kind: str, key: str) -> str:
    choices = {
        "texture": TEXTURE_FORMATS,
        "hdri": HDRI_FORMATS,
        "model": MODEL_FORMATS,
        "sound": SOUND_FORMATS,
    }
    return dict(choices.get(kind, [])).get(key, key.upper())

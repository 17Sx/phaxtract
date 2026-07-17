"""Pair annotated JSON gold files with their matching source images.

Given a folder of annotated JSONs and a (larger) folder of images, copy only
the images whose annotation exists, next to their JSON, into an output folder.

Matching strategy, tried in order:
  1. Exact stem match:            foo.json  <-> foo.JPG
  2. Prefix match:                foo.json  <-> foo_<digits>.JPG (trailing ms suffix)
  3. Normalized stem match:       lowercased, non-alphanumeric stripped
  4. Image name read from JSON:   a string field pointing to the source file

Image extensions are matched case-insensitively (.JPG, .jpg, .png, ...).

Usage:
    python scripts/pair_gold.py \
        --jsons gold/real/jsons_annotes \
        --images gold/real/images_all \
        --out gold/real/pairs

Add --dry-run to preview without copying.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff")
_NORMALIZE = re.compile(r"[^a-z0-9]")
_TRAILING_DIGITS = re.compile(r"^(.*)_\d+$")


def _norm(name: str) -> str:
    return _NORMALIZE.sub("", name.lower())


class ImageIndex:
    """Lookup tables for pairing JSON stems with image files."""

    def __init__(self) -> None:
        self.by_stem: dict[str, Path] = {}
        self.by_norm: dict[str, Path] = {}
        self.by_prefix: dict[str, list[Path]] = {}

    def add(self, path: Path) -> None:
        stem = path.stem
        self.by_stem.setdefault(stem, path)
        self.by_norm.setdefault(_norm(stem), path)
        match = _TRAILING_DIGITS.match(stem)
        if match:
            self.by_prefix.setdefault(match.group(1), []).append(path)


def _index_images(images_dir: Path) -> ImageIndex:
    index = ImageIndex()
    for path in images_dir.rglob("*"):
        if path.suffix.lower() in IMAGE_EXTS:
            index.add(path)
    return index


def _image_name_from_json(json_path: Path) -> str | None:
    """Best-effort: find an image filename referenced inside the JSON."""
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    for key in ("image", "image_name", "file_name", "filename", "source", "uri"):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, str) and value.lower().endswith(IMAGE_EXTS):
            return Path(value).name
    return None


def find_match(json_path: Path, index: ImageIndex) -> tuple[Path | None, bool]:
    """Return (matched image, ambiguous?). Ambiguous means >1 candidate found."""
    stem = json_path.stem
    if stem in index.by_stem:
        return index.by_stem[stem], False
    prefix_hits = index.by_prefix.get(stem)
    if prefix_hits:
        return sorted(prefix_hits)[0], len(prefix_hits) > 1
    if _norm(stem) in index.by_norm:
        return index.by_norm[_norm(stem)], False
    referenced = _image_name_from_json(json_path)
    if referenced:
        ref_stem = Path(referenced).stem
        if ref_stem in index.by_stem:
            return index.by_stem[ref_stem], False
        if _norm(ref_stem) in index.by_norm:
            return index.by_norm[_norm(ref_stem)], False
    return None, False


def main() -> None:
    parser = argparse.ArgumentParser(description="Pair gold JSONs with their images.")
    parser.add_argument("--jsons", type=Path, required=True, help="Folder of annotated JSONs")
    parser.add_argument("--images", type=Path, required=True, help="Folder of all images")
    parser.add_argument("--out", type=Path, required=True, help="Output folder for pairs")
    parser.add_argument("--dry-run", action="store_true", help="Preview without copying")
    args = parser.parse_args()

    index = _index_images(args.images)
    json_files = sorted(args.jsons.glob("*.json"))

    out_jsons = args.out / "jsons"
    out_images = args.out / "images"
    if not args.dry_run:
        out_jsons.mkdir(parents=True, exist_ok=True)
        out_images.mkdir(parents=True, exist_ok=True)

    matched = 0
    ambiguous: list[str] = []
    unmatched: list[str] = []
    for json_path in json_files:
        image, is_ambiguous = find_match(json_path, index)
        if image is None:
            unmatched.append(json_path.name)
            continue
        matched += 1
        if is_ambiguous:
            ambiguous.append(f"{json_path.name} -> {image.name}")
        if not args.dry_run:
            shutil.copy2(json_path, out_jsons / json_path.name)
            shutil.copy2(image, out_images / image.name)

    print(f"JSONs found:    {len(json_files)}")
    print(f"Images indexed: {len(index.by_stem)}")
    print(f"Matched pairs:  {matched}")
    print(f"Ambiguous:      {len(ambiguous)} (picked first, verify these)")
    print(f"Unmatched:      {len(unmatched)}")
    for entry in ambiguous:
        print(f"  ? {entry}")
    for name in unmatched:
        print(f"  ! no image for {name}")


if __name__ == "__main__":
    main()

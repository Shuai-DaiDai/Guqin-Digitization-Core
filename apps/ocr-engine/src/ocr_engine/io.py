"""Filesystem helpers for OCR engine bundles."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any

from ocr_engine.models import OCRBundle


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".pgm", ".pnm"}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_ndjson(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_ndjson(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def copy_file(source: Path, destination: Path) -> None:
    ensure_dir(destination.parent)
    shutil.copy2(source, destination)


def collect_image_paths(input_path: Path) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() == ".json":
            manifest = read_json(input_path)
            return [
                (input_path.parent / str(page.get("image_file", ""))).resolve()
                for page in manifest.get("pages", [])
                if isinstance(page, dict) and str(page.get("image_file", "")).strip()
            ]
        return [input_path]
    if input_path.is_dir():
        return sorted(
            path
            for path in input_path.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )
    raise FileNotFoundError(f"Input path does not exist: {input_path}")


def collect_input_pages(input_path: Path) -> list[dict[str, Any]]:
    """Collect normalized page inputs from a file, directory, or JSON manifest."""
    if input_path.is_file() and input_path.suffix.lower() == ".json":
        manifest = read_json(input_path)
        pages: list[dict[str, Any]] = []
        for index, page in enumerate(manifest.get("pages", []), start=1):
            if not isinstance(page, dict):
                continue
            image_file = str(page.get("image_file", "")).strip()
            if not image_file:
                continue
            pages.append(
                {
                    "page_id": str(page.get("page_id") or f"page-{index:03d}"),
                    "page_index": int(page.get("page_number", index)),
                    "image_path": (input_path.parent / image_file).resolve(),
                    "metadata": {
                        "note": page.get("note"),
                        "input_manifest": str(input_path.resolve()),
                    },
                }
            )
        return pages

    image_paths = collect_image_paths(input_path)
    return [
        {
            "page_id": f"{input_path.stem}-page-{index:03d}",
            "page_index": index,
            "image_path": image_path.resolve(),
            "metadata": {},
        }
        for index, image_path in enumerate(image_paths, start=1)
    ]


def write_bundle(bundle_dir: Path, bundle: OCRBundle) -> None:
    ensure_dir(bundle_dir)
    ensure_dir(bundle_dir / "raw")
    ensure_dir(bundle_dir / "reports")
    ensure_dir(bundle_dir / "logs")

    write_json(bundle_dir / "manifest.json", bundle.manifest.to_dict())
    write_ndjson(bundle_dir / "raw" / "pages.ndjson", [page.to_dict() for page in bundle.pages])
    write_ndjson(
        bundle_dir / "raw" / "detections.ndjson",
        [detection.to_dict() for detection in bundle.detections],
    )
    write_ndjson(
        bundle_dir / "raw" / "glyph_candidates.ndjson",
        [candidate.to_dict() for candidate in bundle.glyph_candidates],
    )
    write_ndjson(
        bundle_dir / "raw" / "component_candidates.ndjson",
        [candidate.to_dict() for candidate in bundle.component_candidates],
    )
    write_json(bundle_dir / "reports" / "summary.json", bundle.summary)
    if bundle.validation:
        write_json(bundle_dir / "reports" / "validation.json", bundle.validation)

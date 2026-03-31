"""Adapter for KuiSCIMA-style image-linked notation JSON files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from dataset_tools.adapters.gui_tools import _normalize_bbox, _slugify
from dataset_tools.models.glyph import GlyphRecord
from dataset_tools.models.manifest import SourceManifest
from dataset_tools.models.page import PageRecord


@dataclass(slots=True)
class KuiSCIMAImportBundle:
    """In-memory representation of imported KuiSCIMA data."""

    manifest: SourceManifest
    pages: list[PageRecord]
    glyphs: list[GlyphRecord]
    warnings: list[str]


def load_kuiscima_bundle(input_path: Path, images_root: Path | None = None) -> KuiSCIMAImportBundle:
    """Parse a KuiSCIMA JSON export into internal records."""
    raw = json.loads(input_path.read_text(encoding="utf-8"))

    notation_type = str(raw.get("notation_type", ""))
    if not notation_type:
        raise ValueError("KuiSCIMA JSON must include notation_type.")

    source_id = _slugify(input_path.stem)
    resolved_images_root = images_root if images_root is not None else input_path.parent
    image_entries = raw.get("images") or []
    image_paths: list[str] = []
    pages: list[PageRecord] = []
    page_ids: list[str] = []
    warnings: list[str] = []

    if not image_entries:
        page_id = f"{source_id}-page-001"
        page_ids.append(page_id)
        pages.append(
            PageRecord(
                page_id=page_id,
                source_id=source_id,
                page_index=1,
                image_path="",
                metadata={"missing_image_reference": True},
            )
        )
        warnings.append("No images list found in KuiSCIMA JSON; created a placeholder page record.")
    else:
        for index, image_ref in enumerate(image_entries, start=1):
            resolved_path = str((resolved_images_root / image_ref).resolve()) if image_ref else ""
            image_paths.append(resolved_path)
            page_id = f"{source_id}-page-{index:03d}"
            page_ids.append(page_id)
            page_metadata = {"source_image_ref": image_ref}
            if resolved_path and not Path(resolved_path).exists():
                page_metadata["missing_on_disk"] = True
                warnings.append(f"Image reference not found on disk: {image_ref}")
            pages.append(
                PageRecord(
                    page_id=page_id,
                    source_id=source_id,
                    page_index=index,
                    image_path=resolved_path,
                    metadata=page_metadata,
                )
            )

    manifest = SourceManifest(
        source_id=source_id,
        source_type="kuiscima",
        source_file=str(input_path.resolve()),
        notation_type=notation_type,
        composer=str(raw.get("composer", "")),
        piece_title=str(raw.get("piece_title") or input_path.stem),
        image_paths=image_paths,
        imported_at="",
        metadata={
            "version": raw.get("version"),
            "mode_properties": raw.get("mode_properties"),
            "notation_system_origin": "KuiSCIMA",
        },
    )

    glyphs: list[GlyphRecord] = []
    for order_index, box in enumerate(raw.get("content", []), start=1):
        if not isinstance(box, dict):
            warnings.append(f"Skipped non-object content entry at index {order_index - 1}.")
            continue

        page_pointer = 1
        metadata: dict[str, object] = {}
        if isinstance(box.get("image_index"), int):
            page_pointer = box["image_index"] + 1
            metadata["source_image_index"] = box["image_index"]
        if page_pointer < 1 or page_pointer > len(page_ids):
            warnings.append(
                f"Box {order_index} referenced image index {page_pointer - 1}, which is outside the image list."
            )
            page_pointer = 1

        metadata["notation_type"] = notation_type
        glyphs.append(
            GlyphRecord(
                glyph_id=f"{source_id}-glyph-{order_index:05d}",
                page_id=page_ids[page_pointer - 1],
                source_box_index=order_index - 1,
                box_type=str(box.get("box_type", "Unmarked")),
                order_index=order_index,
                text_bbox=_normalize_bbox(box.get("text_coordinates")),
                notation_bbox=_normalize_bbox(box.get("notation_coordinates")),
                text_content=box.get("text_content"),
                raw_notation_payload=box.get("notation_content"),
                is_excluded_from_dataset=bool(box.get("is_excluded_from_dataset", False)),
                is_line_break=bool(box.get("is_line_break", False)),
                metadata=metadata,
            )
        )

    return KuiSCIMAImportBundle(
        manifest=manifest,
        pages=pages,
        glyphs=glyphs,
        warnings=warnings,
    )

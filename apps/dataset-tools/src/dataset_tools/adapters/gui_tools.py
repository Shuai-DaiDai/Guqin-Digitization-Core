"""Adapter for gui-tools jianzipu annotation files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from dataset_tools.models.glyph import GlyphRecord
from dataset_tools.models.manifest import SourceManifest
from dataset_tools.models.page import PageRecord


def _slugify(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
    collapsed = "-".join(part for part in cleaned.split("-") if part)
    return collapsed or "untitled"


@dataclass(slots=True)
class GuiToolsImportBundle:
    """In-memory representation of imported gui-tools data."""

    manifest: SourceManifest
    pages: list[PageRecord]
    glyphs: list[GlyphRecord]
    warnings: list[str]


def _normalize_bbox(raw_bbox: object) -> list[list[int]] | None:
    if raw_bbox is None:
        return None
    if not isinstance(raw_bbox, list) or len(raw_bbox) != 2:
        return None
    points: list[list[int]] = []
    for point in raw_bbox:
        if (
            not isinstance(point, list)
            or len(point) != 2
            or not all(isinstance(value, int) for value in point)
        ):
            return None
        points.append([point[0], point[1]])
    return points


def load_gui_tools_bundle(input_path: Path, images_root: Path | None = None) -> GuiToolsImportBundle:
    """Parse a gui-tools jianzipu JSON export into internal records."""
    raw = json.loads(input_path.read_text(encoding="utf-8"))

    if raw.get("notation_type") != "Jianzipu":
        raise ValueError("Only gui-tools Jianzipu exports are supported in the first importer.")

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
        warnings.append("No images list found in gui-tools JSON; created a placeholder page record.")
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
        source_type="gui-tools",
        source_file=str(input_path.resolve()),
        notation_type=str(raw.get("notation_type", "")),
        composer=str(raw.get("composer", "")),
        piece_title=input_path.stem,
        image_paths=image_paths,
        imported_at="",
        metadata={
            "version": raw.get("version"),
            "mode_properties": raw.get("mode_properties"),
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

    return GuiToolsImportBundle(
        manifest=manifest,
        pages=pages,
        glyphs=glyphs,
        warnings=warnings,
    )

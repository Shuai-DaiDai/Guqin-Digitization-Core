"""Adapter for manually prepared metadata and rough annotation CSV files."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from dataset_tools.adapters.gui_tools import _normalize_bbox, _slugify
from dataset_tools.models.glyph import GlyphRecord
from dataset_tools.models.manifest import SourceManifest
from dataset_tools.models.page import PageRecord


@dataclass(slots=True)
class ManualCsvImportBundle:
    """In-memory representation of imported manual preparation files."""

    manifest: SourceManifest
    pages: list[PageRecord]
    glyphs: list[GlyphRecord]
    warnings: list[str]


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return int(stripped)
    except ValueError:
        return None


def _to_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _build_bbox(row: dict[str, str]) -> list[list[int]] | None:
    x1 = _to_int(row.get("bbox_x1"))
    y1 = _to_int(row.get("bbox_y1"))
    x2 = _to_int(row.get("bbox_x2"))
    y2 = _to_int(row.get("bbox_y2"))
    if None in {x1, y1, x2, y2}:
        return None
    return _normalize_bbox([[x1, y1], [x2, y2]])


def load_manual_csv_bundle(
    metadata_path: Path,
    annotations_path: Path,
    images_root: Path | None = None,
) -> ManualCsvImportBundle:
    """Parse manually prepared metadata and annotation CSV files into internal records."""
    metadata_rows = _read_csv_rows(metadata_path)
    annotation_rows = _read_csv_rows(annotations_path)
    warnings: list[str] = []

    if not metadata_rows:
        raise ValueError("Metadata CSV must contain at least one row.")

    first_row = metadata_rows[0]
    source_id = _slugify(first_row.get("source_id") or first_row.get("piece_title") or metadata_path.stem)
    resolved_images_root = images_root if images_root is not None else metadata_path.parent

    pages: list[PageRecord] = []
    image_paths: list[str] = []
    page_id_by_image_file: dict[str, str] = {}

    for row_index, row in enumerate(metadata_rows, start=1):
        image_file = (row.get("image_file") or "").strip()
        resolved_path = str((resolved_images_root / image_file).resolve()) if image_file else ""
        page_id = f"{source_id}-page-{row_index:03d}"
        page_id_by_image_file[image_file] = page_id
        image_paths.append(resolved_path)

        metadata = {
            "source_book": row.get("source_book", ""),
            "edition_note": row.get("edition_note", ""),
            "page_number_original": row.get("page_number_original", ""),
            "page_number_in_piece": row.get("page_number_in_piece", ""),
            "source_url": row.get("source_url", ""),
            "quality_note": row.get("quality_note", ""),
            "remarks": row.get("remarks", ""),
        }
        if resolved_path and not Path(resolved_path).exists():
            metadata["missing_on_disk"] = True
            warnings.append(f"Image reference not found on disk: {image_file}")

        pages.append(
            PageRecord(
                page_id=page_id,
                source_id=source_id,
                page_index=row_index,
                image_path=resolved_path,
                metadata=metadata,
            )
        )

    manifest = SourceManifest(
        source_id=source_id,
        source_type="manual-csv",
        source_file=str(metadata_path.resolve()),
        notation_type="Jianzipu",
        composer="",
        piece_title=first_row.get("piece_title") or metadata_path.stem,
        image_paths=image_paths,
        imported_at="",
        metadata={
            "source_book": first_row.get("source_book", ""),
            "edition_note": first_row.get("edition_note", ""),
            "source_url": first_row.get("source_url", ""),
            "tuning": first_row.get("tuning", ""),
            "performer_or_transcriber": first_row.get("performer_or_transcriber", ""),
            "rights_note": first_row.get("rights_note", ""),
            "annotations_file": str(annotations_path.resolve()),
        },
    )

    glyphs: list[GlyphRecord] = []
    for order_index, row in enumerate(annotation_rows, start=1):
        image_file = (row.get("image_file") or "").strip()
        page_id = page_id_by_image_file.get(image_file)
        if page_id is None:
            warnings.append(
                f"Annotation row {order_index} references unknown image_file '{image_file}'."
            )
            continue

        char_guess = (row.get("char_guess") or "").strip()
        component_guess = (row.get("component_guess") or "").strip()
        left_hand_guess = (row.get("left_hand_guess") or "").strip()
        raw_notation_payload = {
            "type": "MANUAL_GUESS",
            "char_guess": char_guess,
            "component_guess": component_guess,
            "line_index": _to_int(row.get("line_index")),
            "glyph_index": _to_int(row.get("glyph_index")),
            "confidence": (row.get("confidence") or "").strip().lower() or "unknown",
            "needs_review": _to_bool(row.get("needs_review")),
            "note_type_guess": (row.get("note_type") or "").strip() or "unknown",
            "string": _to_int(row.get("string_number")),
            "hui_guess": _to_int(row.get("hui_guess")),
            "fraction_guess": (row.get("fraction_guess") or "").strip() or None,
            "right_hand_guess": (row.get("right_hand_guess") or "").strip() or None,
            "left_hand_guess": left_hand_guess or None,
        }

        left_hand_symbols: list[str] = []
        if left_hand_guess:
            left_hand_symbols = [item.strip() for item in left_hand_guess.split("|") if item.strip()]
            raw_notation_payload["left_hand_symbols"] = left_hand_symbols

        glyphs.append(
            GlyphRecord(
                glyph_id=f"{source_id}-glyph-{order_index:05d}",
                page_id=page_id,
                source_box_index=order_index - 1,
                box_type="Music",
                order_index=order_index,
                text_bbox=_build_bbox(row),
                notation_bbox=_build_bbox(row),
                text_content=char_guess or None,
                raw_notation_payload=raw_notation_payload,
                is_excluded_from_dataset=False,
                is_line_break=False,
                metadata={
                    "line_index": _to_int(row.get("line_index")),
                    "glyph_index": _to_int(row.get("glyph_index")),
                    "annotation_note": row.get("note", ""),
                },
            )
        )

    return ManualCsvImportBundle(
        manifest=manifest,
        pages=pages,
        glyphs=glyphs,
        warnings=warnings,
    )

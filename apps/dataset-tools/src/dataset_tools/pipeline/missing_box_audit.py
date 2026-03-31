"""Prepare lightweight page packs for missing-box audits."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from dataset_tools.io_utils import ensure_dir, read_json, read_ndjson, write_csv, write_json, write_ndjson


SUPPORTED_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def prepare_missing_box_audit(
    bundle_path: Path,
    output_dir: Path,
    *,
    page_images_root: Path,
    page_ids: list[str] | None = None,
    only_reviewed_pages: bool = False,
    max_pages: int | None = None,
) -> dict[str, object]:
    """Export a compact page pack for humans to inspect missing OCR boxes."""
    raw_dir = bundle_path / "raw"
    derived_dir = bundle_path / "derived"

    manifest = read_json(raw_dir / "source_manifest.json")
    pages = read_ndjson(raw_dir / "pages.ndjson")
    glyphs = read_ndjson(raw_dir / "glyphs.ndjson")
    review_items = read_ndjson(derived_dir / "review_queue" / "items.ndjson")

    selected_page_ids = {
        page_id.strip()
        for page_id in (page_ids or [])
        if page_id and page_id.strip()
    }
    if not selected_page_ids:
        selected_page_ids = _select_page_ids(
            pages=pages,
            glyphs=glyphs,
            only_reviewed_pages=only_reviewed_pages,
            max_pages=max_pages,
        )

    page_lookup = {
        str(page.get("page_id", "")).strip(): page
        for page in pages
        if str(page.get("page_id", "")).strip()
    }
    glyphs_by_page: dict[str, list[dict[str, object]]] = {}
    for glyph in glyphs:
        page_id = str(glyph.get("page_id", "")).strip()
        if not page_id:
            continue
        glyphs_by_page.setdefault(page_id, []).append(glyph)

    review_items_by_page: dict[str, list[dict[str, object]]] = {}
    for item in review_items:
        page_id = str(item.get("page_id", "")).strip()
        if not page_id:
            continue
        review_items_by_page.setdefault(page_id, []).append(item)

    ensure_dir(output_dir)
    ensure_dir(output_dir / "page_images")

    missing_images: list[str] = []
    page_rows: list[dict[str, object]] = []
    note_rows: list[dict[str, object]] = []

    resolved_images = _resolve_page_images(page_images_root=page_images_root, page_ids=selected_page_ids)

    ordered_page_ids = sorted(
        selected_page_ids,
        key=lambda page_id: (
            int(page_lookup.get(page_id, {}).get("page_index"))
            if isinstance(page_lookup.get(page_id, {}).get("page_index"), int)
            else 10**9,
            page_id,
        ),
    )

    for page_id in ordered_page_ids:
        page = page_lookup.get(page_id, {})
        image_path = resolved_images.get(page_id)
        copied_image_rel = ""
        if image_path is not None:
            copied_name = f"{page_id}{image_path.suffix.lower()}"
            target_path = output_dir / "page_images" / copied_name
            ensure_dir(target_path.parent)
            shutil.copy2(image_path, target_path)
            copied_image_rel = f"page_images/{copied_name}"
        else:
            missing_images.append(page_id)

        page_glyphs = glyphs_by_page.get(page_id, [])
        music_glyphs = [glyph for glyph in page_glyphs if str(glyph.get("box_type", "")) == "Music"]
        reviewed_music_glyphs = [
            glyph
            for glyph in music_glyphs
            if isinstance(glyph.get("metadata"), dict) and str(glyph["metadata"].get("review_verdict", "")).strip()
        ]
        excluded_music_glyphs = [
            glyph for glyph in music_glyphs if glyph.get("is_excluded_from_dataset") is True
        ]

        row = {
            "page_id": page_id,
            "page_index": page.get("page_index", ""),
            "image_path": copied_image_rel,
            "music_box_count": len(music_glyphs),
            "reviewed_music_box_count": len(reviewed_music_glyphs),
            "excluded_music_box_count": len(excluded_music_glyphs),
            "pending_review_item_count": len(review_items_by_page.get(page_id, [])),
            "audit_status": "pending",
            "missing_box_count": "",
            "has_missing_boxes": "",
            "auditor": "",
            "notes": "",
        }
        page_rows.append(row)
        note_rows.append(
            {
                "page_id": page_id,
                "page_index": page.get("page_index", ""),
                "status": "pending",
                "has_missing_boxes": "",
                "missing_box_count": "",
                "notes": "",
            }
        )

    audit_manifest = {
        "source_id": manifest.get("source_id"),
        "bundle_path": str(bundle_path.resolve()),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "page_images_root": str(page_images_root.resolve()),
        "page_count": len(page_rows),
        "missing_image_count": len(missing_images),
        "pages": page_rows,
    }

    write_json(output_dir / "audit_manifest.json", audit_manifest)
    write_ndjson(output_dir / "pages.ndjson", page_rows)
    write_csv(
        output_dir / "pages.csv",
        fieldnames=[
            "page_id",
            "page_index",
            "image_path",
            "music_box_count",
            "reviewed_music_box_count",
            "excluded_music_box_count",
            "pending_review_item_count",
            "audit_status",
            "has_missing_boxes",
            "missing_box_count",
            "auditor",
            "notes",
        ],
        rows=page_rows,
    )
    write_csv(
        output_dir / "missing_box_notes_template.csv",
        fieldnames=[
            "page_id",
            "page_index",
            "status",
            "has_missing_boxes",
            "missing_box_count",
            "notes",
        ],
        rows=note_rows,
    )
    write_json(
        output_dir / "summary.json",
        {
            "source_id": manifest.get("source_id"),
            "generated_at": audit_manifest["generated_at"],
            "page_count": len(page_rows),
            "missing_image_count": len(missing_images),
            "only_reviewed_pages": only_reviewed_pages,
            "max_pages": max_pages,
            "selected_page_ids": ordered_page_ids,
        },
    )
    return audit_manifest


def _select_page_ids(
    *,
    pages: list[dict[str, object]],
    glyphs: list[dict[str, object]],
    only_reviewed_pages: bool,
    max_pages: int | None,
) -> set[str]:
    page_meta: dict[str, dict[str, object]] = {
        str(page.get("page_id", "")).strip(): page
        for page in pages
        if str(page.get("page_id", "")).strip()
    }
    reviewed_page_ids: set[str] = set()
    music_page_ids: set[str] = set()
    for glyph in glyphs:
        page_id = str(glyph.get("page_id", "")).strip()
        if not page_id or str(glyph.get("box_type", "")) != "Music":
            continue
        music_page_ids.add(page_id)
        metadata = glyph.get("metadata", {})
        if isinstance(metadata, dict) and str(metadata.get("review_verdict", "")).strip():
            reviewed_page_ids.add(page_id)

    selected = reviewed_page_ids if only_reviewed_pages else music_page_ids
    ordered = sorted(
        selected,
        key=lambda page_id: (
            int(page_meta.get(page_id, {}).get("page_index"))
            if isinstance(page_meta.get(page_id, {}).get("page_index"), int)
            else 10**9,
            page_id,
        ),
    )
    if max_pages is not None:
        ordered = ordered[:max_pages]
    return set(ordered)


def _resolve_page_images(*, page_images_root: Path, page_ids: set[str]) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for image_path in page_images_root.rglob("*"):
        if not image_path.is_file():
            continue
        if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            continue
        stem = image_path.stem
        if stem in page_ids and stem not in resolved:
            resolved[stem] = image_path
    return resolved

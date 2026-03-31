"""Export static review sites for human OCR correction."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from dataset_tools.io_utils import ensure_dir, read_json, read_ndjson, write_json


SUPPORTED_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def _resolve_page_images(page_images_root: Path, page_ids: set[str]) -> dict[str, Path]:
    page_image_by_id: dict[str, Path] = {}
    for image_path in page_images_root.rglob("*"):
        if not image_path.is_file():
            continue
        if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            continue
        stem = image_path.stem
        if stem in page_ids and stem not in page_image_by_id:
            page_image_by_id[stem] = image_path
    return page_image_by_id


def _copy_static_template(output_dir: Path) -> None:
    template_root = Path("apps/review-studio/static")
    for source in template_root.iterdir():
        if source.is_file():
            target = output_dir / source.name
            ensure_dir(target.parent)
            shutil.copy2(source, target)


def _copy_page_image(source: Path, target: Path) -> None:
    ensure_dir(target.parent)
    shutil.copy2(source, target)


def _existing_exported_page_image(output_dir: Path, page_id: str) -> Path | None:
    assets_dir = output_dir / "assets" / "pages"
    for candidate in sorted(assets_dir.glob(f"{page_id}.*")):
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
            return candidate
    return None


def export_review_site(
    *,
    bundle_path: Path,
    output_dir: Path,
    page_images_root: Path,
    batch_id: str | None = None,
    site_title: str | None = None,
    api_base_url: str | None = None,
    require_token: bool = False,
) -> dict[str, object]:
    """Export a shareable static review site for one batch or full queue."""
    raw_dir = bundle_path / "raw"
    review_dir = bundle_path / "derived" / "review_queue"
    drafts_dir = bundle_path / "derived" / "jianzi_code_drafts"

    manifest = read_json(raw_dir / "source_manifest.json")
    pages = read_ndjson(raw_dir / "pages.ndjson")
    glyphs = read_ndjson(raw_dir / "glyphs.ndjson")
    drafts = read_ndjson(drafts_dir / "event_drafts.ndjson")

    items_path = review_dir / "items.ndjson"
    if batch_id:
        items_path = review_dir / "batches" / batch_id / "items.ndjson"
    items = read_ndjson(items_path)

    page_ids = {
        str(item.get("page_id", "")).strip()
        for item in items
        if str(item.get("page_id", "")).strip()
    }
    page_image_by_id = _resolve_page_images(page_images_root, page_ids)

    page_meta_by_id = {
        str(page.get("page_id", "")): page
        for page in pages
        if str(page.get("page_id", ""))
    }
    glyph_meta_by_id = {
        str(glyph.get("glyph_id", "")): glyph
        for glyph in glyphs
        if str(glyph.get("glyph_id", ""))
    }
    draft_by_id = {
        str(draft.get("draft_id", "")): draft
        for draft in drafts
        if str(draft.get("draft_id", ""))
    }

    ensure_dir(output_dir)
    ensure_dir(output_dir / "data")
    ensure_dir(output_dir / "assets" / "pages")
    _copy_static_template(output_dir)

    exported_pages: list[dict[str, object]] = []
    copied_pages = 0
    missing_pages: list[str] = []

    for page_id in sorted(page_ids):
        page = page_meta_by_id.get(page_id, {})
        source_image = page_image_by_id.get(page_id)
        image_filename = ""
        if source_image is not None:
            image_filename = f"{page_id}{source_image.suffix.lower()}"
            _copy_page_image(source_image, output_dir / "assets" / "pages" / image_filename)
            copied_pages += 1
        else:
            raw_image_path = Path(str(page.get("image_path", "")).strip()) if page.get("image_path") else None
            existing_image = _existing_exported_page_image(output_dir, page_id)
            if raw_image_path and raw_image_path.is_file():
                image_filename = f"{page_id}{raw_image_path.suffix.lower()}"
                _copy_page_image(raw_image_path, output_dir / "assets" / "pages" / image_filename)
                copied_pages += 1
            elif existing_image is not None:
                image_filename = existing_image.name
            else:
                missing_pages.append(page_id)

        exported_pages.append(
            {
                "pageId": page_id,
                "pageIndex": page.get("page_index"),
                "width": page.get("width"),
                "height": page.get("height"),
                "imagePath": f"assets/pages/{image_filename}" if image_filename else "",
            }
        )

    exported_items: list[dict[str, object]] = []
    for item in items:
        review_id = str(item.get("review_id", ""))
        glyph_id = str(item.get("glyph_id", ""))
        glyph = glyph_meta_by_id.get(glyph_id, {})
        draft = draft_by_id.get(review_id, {})
        bbox = glyph.get("notation_bbox", [])
        x1 = y1 = x2 = y2 = 0
        if isinstance(bbox, list) and len(bbox) == 2:
            first, second = bbox
            if (
                isinstance(first, list)
                and isinstance(second, list)
                and len(first) == 2
                and len(second) == 2
            ):
                x1, y1 = int(first[0]), int(first[1])
                x2, y2 = int(second[0]), int(second[1])

        glyph_payload = glyph.get("raw_notation_payload", {})
        glyph_candidates = (
            glyph_payload.get("glyph_candidates", [])
            if isinstance(glyph_payload, dict)
            else []
        )
        component_candidates = (
            glyph_payload.get("component_candidates", [])
            if isinstance(glyph_payload, dict)
            else []
        )
        top_candidate = glyph_candidates[0] if glyph_candidates else {}

        metadata = draft.get("metadata", {}) if isinstance(draft.get("metadata"), dict) else {}
        exported_items.append(
            {
                "reviewId": review_id,
                "glyphId": glyph_id,
                "pageId": item.get("page_id", ""),
                "pageIndex": item.get("page_index"),
                "priority": item.get("priority", "high"),
                "currentIssues": item.get("issues", []),
                "suggestedAction": item.get("suggested_action", ""),
                "notationKind": item.get("notation_kind", ""),
                "visualCharText": item.get("visual_char_text", ""),
                "detectionConfidence": item.get("detection_confidence"),
                "reviewReasons": metadata.get("review_reasons", []),
                "bbox": {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                },
                "systemGuess": {
                    "label": top_candidate.get("label", item.get("visual_char_text", "")),
                    "confidence": top_candidate.get("confidence"),
                    "layout": glyph_payload.get("layout_guess", ""),
                },
                "componentHints": [
                    {
                        "slot": component.get("slot", ""),
                        "label": component.get("label", ""),
                        "confidence": component.get("confidence"),
                    }
                    for component in component_candidates
                    if isinstance(component, dict)
                ],
            }
        )

    payload = {
        "site": {
            "title": site_title or f"Guqin OCR Review {batch_id or 'full'}",
            "sourceId": manifest.get("source_id", ""),
            "batchId": batch_id or "full",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "siteId": f"{manifest.get('source_id', '')}::{batch_id or 'full'}",
            "localStorageKey": f"guqin-review::{manifest.get('source_id', '')}::{batch_id or 'full'}",
        },
        "summary": {
            "itemCount": len(exported_items),
            "pageCount": len(exported_pages),
            "missingPageCount": len(missing_pages),
        },
        "pages": exported_pages,
        "items": exported_items,
    }
    write_json(output_dir / "data" / "review-data.json", payload)
    write_json(
        output_dir / "data" / "review-config.json",
        {
            "apiBaseUrl": api_base_url or "",
            "requireToken": require_token,
            "siteId": payload["site"]["siteId"],
            "siteTitle": payload["site"]["title"],
        },
    )

    report = {
        "output_dir": str(output_dir),
        "batch_id": batch_id,
        "item_count": len(exported_items),
        "page_count": len(exported_pages),
        "copied_page_count": copied_pages,
        "missing_pages": missing_pages,
        "api_base_url": api_base_url or "",
        "require_token": require_token,
    }
    write_json(output_dir / "data" / "export-report.json", report)
    print(f"Wrote review site to {output_dir}")
    return report

"""Materialize one recommended next-batch selection into a real batch folder."""

from __future__ import annotations

from pathlib import Path

from dataset_tools.io_utils import read_json, read_ndjson, write_csv, write_json, write_ndjson


def materialize_next_review_batch(
    *,
    bundle_path: Path,
    batch_id: str,
    recommendation_dir: Path | None = None,
    max_pages: int | None = None,
) -> dict[str, object]:
    """Turn one recommendation result into a concrete review batch directory."""
    review_dir = bundle_path / "derived" / "review_queue"
    recommendation_root = recommendation_dir or (bundle_path / "derived" / "next_batch")
    recommendation = read_json(recommendation_root / "recommendation.json")
    selected_pages = recommendation.get("selected_pages", [])
    selected_items = read_ndjson(recommendation_root / "selected_items.ndjson")
    review_items = read_ndjson(review_dir / "items.ndjson")

    review_item_by_id = {
        str(item.get("review_id", "")).strip(): item
        for item in review_items
        if str(item.get("review_id", "")).strip()
    }

    page_ids_in_order: list[str] = []
    for row in selected_pages:
        page_id = str(row.get("page_id", "")).strip()
        if not page_id:
            continue
        page_ids_in_order.append(page_id)
    if max_pages is not None:
        page_ids_in_order = page_ids_in_order[:max_pages]
    page_id_set = set(page_ids_in_order)

    batch_items: list[dict[str, object]] = []
    missing_review_ids: list[str] = []
    for selection in selected_items:
        page_id = str(selection.get("page_id", "")).strip()
        review_id = str(selection.get("review_id", "")).strip()
        if page_id not in page_id_set or not review_id:
            continue
        item = review_item_by_id.get(review_id)
        if item is None:
            missing_review_ids.append(review_id)
            continue
        batch_items.append(item)

    batch_dir = review_dir / "batches" / batch_id
    write_ndjson(batch_dir / "items.ndjson", batch_items)
    write_csv(
        batch_dir / "items.csv",
        fieldnames=[
            "review_id",
            "source_id",
            "glyph_id",
            "page_id",
            "page_index",
            "priority",
            "issue_count",
            "issues",
            "visual_char_text",
            "notation_kind",
            "suggested_action",
            "detection_confidence",
            "crop_ref",
            "image_path",
        ],
        rows=[
            {
                "review_id": item.get("review_id", ""),
                "source_id": item.get("source_id", ""),
                "glyph_id": item.get("glyph_id", ""),
                "page_id": item.get("page_id", ""),
                "page_index": item.get("page_index", ""),
                "priority": item.get("priority", ""),
                "issue_count": item.get("issue_count", 0),
                "issues": "|".join(item.get("issues", [])) if isinstance(item.get("issues"), list) else "",
                "visual_char_text": item.get("visual_char_text", ""),
                "notation_kind": item.get("notation_kind", "") or "",
                "suggested_action": item.get("suggested_action", ""),
                "detection_confidence": item.get("detection_confidence", "") if item.get("detection_confidence") is not None else "",
                "crop_ref": item.get("crop_ref", "") or "",
                "image_path": item.get("image_path", "") or "",
            }
            for item in batch_items
        ],
    )

    page_counts: dict[str, int] = {}
    for item in batch_items:
        page_id = str(item.get("page_id", "")).strip()
        if not page_id:
            continue
        page_counts[page_id] = page_counts.get(page_id, 0) + 1

    summary = {
        "batch_id": batch_id,
        "recommendation_dir": str(recommendation_root.resolve()),
        "selected_page_ids": page_ids_in_order,
        "selected_page_count": len(page_ids_in_order),
        "item_count": len(batch_items),
        "page_counts": page_counts,
        "missing_review_id_count": len(missing_review_ids),
        "missing_review_ids": missing_review_ids[:50],
    }
    write_json(batch_dir / "summary.json", summary)
    write_json(batch_dir / "materialization_report.json", summary)
    return summary

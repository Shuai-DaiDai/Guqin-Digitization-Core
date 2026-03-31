"""Slice large review queues into manageable human-review batches."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import shutil

from dataset_tools.io_utils import read_ndjson, write_csv, write_json, write_ndjson


PRIORITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
}


def slice_review_queue(
    *,
    bundle_path: Path,
    batch_size: int = 200,
    max_per_page: int = 20,
) -> dict[str, object]:
    """Split one large review queue into balanced batches for human reviewers."""
    review_dir = bundle_path / "derived" / "review_queue"
    items = read_ndjson(review_dir / "items.ndjson")
    ordered_items = sorted(
        items,
        key=lambda item: (
            PRIORITY_ORDER.get(str(item.get("priority", "low")), 99),
            -int(item.get("issue_count", 0)),
            int(item.get("page_index", 10**9)) if isinstance(item.get("page_index"), int) else 10**9,
            str(item.get("review_id", "")),
        ),
    )

    batches_root = review_dir / "batches"
    if batches_root.exists():
        shutil.rmtree(batches_root)
    remaining = list(ordered_items)
    batch_summaries: list[dict[str, object]] = []
    batch_index = 0

    while remaining:
        batch_index += 1
        page_counts: Counter[str] = Counter()
        batch_items: list[dict[str, object]] = []
        next_remaining: list[dict[str, object]] = []

        for item in remaining:
            page_id = str(item.get("page_id", ""))
            if len(batch_items) < batch_size and (not page_id or page_counts[page_id] < max_per_page):
                batch_items.append(item)
                if page_id:
                    page_counts[page_id] += 1
            else:
                next_remaining.append(item)

        if not batch_items:
            batch_items = remaining[:batch_size]
            next_remaining = remaining[batch_size:]

        batch_id = f"batch_{batch_index:03d}"
        batch_dir = batches_root / batch_id
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

        priority_counts = Counter(str(item.get("priority", "low")) for item in batch_items)
        batch_summary = {
            "batch_id": batch_id,
            "item_count": len(batch_items),
            "priority_counts": dict(priority_counts),
            "page_count": len({str(item.get("page_id", "")) for item in batch_items if item.get("page_id")}),
            "first_review_id": batch_items[0].get("review_id") if batch_items else None,
            "last_review_id": batch_items[-1].get("review_id") if batch_items else None,
        }
        write_json(batch_dir / "summary.json", batch_summary)
        batch_summaries.append(batch_summary)
        remaining = next_remaining

    summary = {
        "batch_count": len(batch_summaries),
        "batch_size": batch_size,
        "max_per_page": max_per_page,
        "total_items": len(ordered_items),
        "batches": batch_summaries,
    }
    write_json(batches_root / "batches_summary.json", summary)
    print(f"Wrote {len(batch_summaries)} review batch(es) to {batches_root}")
    return summary

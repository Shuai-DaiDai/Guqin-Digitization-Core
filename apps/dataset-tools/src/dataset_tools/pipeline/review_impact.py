"""Offline review impact reporting for reviewed bundles."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dataset_tools.io_utils import read_json, read_ndjson, write_csv, write_json, write_ndjson


def evaluate_review_impact(bundle_path: Path, output_dir: Path | None = None) -> dict[str, object]:
    """Summarize how human review changed a bundle."""
    raw_dir = bundle_path / "raw"
    derived_dir = bundle_path / "derived"

    manifest = read_json(raw_dir / "source_manifest.json")
    pages = read_ndjson(raw_dir / "pages.ndjson")
    glyphs = read_ndjson(raw_dir / "glyphs.ndjson")
    review_items = read_ndjson(derived_dir / "review_queue" / "items.ndjson")

    page_totals: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "page_id": "",
            "page_index": None,
            "music_boxes": 0,
            "title_boxes": 0,
            "reviewed_music_boxes": 0,
            "excluded_music_boxes": 0,
            "review_queue_items": 0,
        }
    )

    for page in pages:
        page_id = str(page.get("page_id", "")).strip()
        if not page_id:
            continue
        page_totals[page_id]["page_id"] = page_id
        page_totals[page_id]["page_index"] = page.get("page_index")

    for glyph in glyphs:
        page_id = str(glyph.get("page_id", "")).strip()
        if not page_id:
            continue
        row = page_totals[page_id]
        box_type = str(glyph.get("box_type", ""))
        metadata = glyph.get("metadata", {})
        if box_type == "Music":
            row["music_boxes"] = int(row["music_boxes"]) + 1
            if glyph.get("is_excluded_from_dataset") is True:
                row["excluded_music_boxes"] = int(row["excluded_music_boxes"]) + 1
            if isinstance(metadata, dict) and str(metadata.get("review_verdict", "")).strip():
                row["reviewed_music_boxes"] = int(row["reviewed_music_boxes"]) + 1
        elif box_type == "Title":
            row["title_boxes"] = int(row["title_boxes"]) + 1

    for item in review_items:
        page_id = str(item.get("page_id", "")).strip()
        if not page_id:
            continue
        if page_id in page_totals:
            page_totals[page_id]["review_queue_items"] = int(page_totals[page_id]["review_queue_items"]) + 1

    page_rows: list[dict[str, object]] = []
    reviewed_pages = 0
    untouched_pages = 0
    partial_pages = 0
    complete_pages = 0

    for row in page_totals.values():
        music_boxes = int(row["music_boxes"])
        reviewed_music_boxes = int(row["reviewed_music_boxes"])
        excluded_music_boxes = int(row["excluded_music_boxes"])
        if music_boxes == 0:
            review_state = "empty"
        elif reviewed_music_boxes == 0:
            review_state = "untouched"
            untouched_pages += 1
        elif reviewed_music_boxes >= music_boxes:
            review_state = "complete"
            complete_pages += 1
            reviewed_pages += 1
        else:
            review_state = "partial"
            partial_pages += 1
            reviewed_pages += 1

        row_data = {
            "page_id": row["page_id"],
            "page_index": row["page_index"],
            "review_state": review_state,
            "music_boxes": music_boxes,
            "title_boxes": int(row["title_boxes"]),
            "reviewed_music_boxes": reviewed_music_boxes,
            "excluded_music_boxes": excluded_music_boxes,
            "review_queue_items": int(row["review_queue_items"]),
            "retained_music_boxes": music_boxes - excluded_music_boxes,
            "review_coverage": round(reviewed_music_boxes / float(music_boxes), 4) if music_boxes else 0.0,
        }
        page_rows.append(row_data)

    page_rows.sort(
        key=lambda row: (
            int(row["page_index"]) if isinstance(row.get("page_index"), int) else 10**9,
            str(row["page_id"]),
        )
    )

    summary = {
        "source_id": manifest.get("source_id"),
        "bundle_path": str(bundle_path.resolve()),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "page_count": len(page_rows),
        "music_box_count": sum(int(row["music_boxes"]) for row in page_rows),
        "title_box_count": sum(int(row["title_boxes"]) for row in page_rows),
        "reviewed_music_boxes": sum(int(row["reviewed_music_boxes"]) for row in page_rows),
        "excluded_music_boxes": sum(int(row["excluded_music_boxes"]) for row in page_rows),
        "retained_music_boxes": sum(int(row["retained_music_boxes"]) for row in page_rows),
        "review_queue_items": len(review_items),
        "reviewed_page_count": reviewed_pages,
        "untouched_page_count": untouched_pages,
        "partial_page_count": partial_pages,
        "complete_page_count": complete_pages,
        "verdict_counts": _count_verdicts(glyphs),
    }

    destination_dir = output_dir or (derived_dir / "review_impact")
    write_json(destination_dir / "summary.json", summary)
    write_ndjson(destination_dir / "pages.ndjson", page_rows)
    write_csv(
        destination_dir / "pages.csv",
        fieldnames=[
            "page_id",
            "page_index",
            "review_state",
            "music_boxes",
            "title_boxes",
            "reviewed_music_boxes",
            "excluded_music_boxes",
            "retained_music_boxes",
            "review_queue_items",
            "review_coverage",
        ],
        rows=page_rows,
    )
    write_json(
        derived_dir / "review_impact_report.json",
        {
            "destination_dir": str(destination_dir),
            "summary": summary,
        },
    )
    print(f"Wrote review impact report to {destination_dir}")
    return summary


def _count_verdicts(glyphs: list[dict[str, object]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for glyph in glyphs:
        metadata = glyph.get("metadata", {})
        if isinstance(metadata, dict):
            verdict = str(metadata.get("review_verdict", "")).strip().lower()
            if verdict:
                counts.update([verdict])
    return dict(counts)

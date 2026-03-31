"""Recommend the next high-value review batch from a processed bundle."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dataset_tools.io_utils import read_json, read_ndjson, write_csv, write_json, write_ndjson


def recommend_next_review_batch(
    bundle_path: Path,
    output_dir: Path | None = None,
    *,
    target_item_count: int = 200,
    max_pages: int | None = None,
    include_partial_pages: bool = False,
) -> dict[str, object]:
    """Build a page-ranked recommendation for the next review batch."""
    raw_dir = bundle_path / "raw"
    derived_dir = bundle_path / "derived"
    reports_dir = bundle_path / "reports"

    manifest = read_json(raw_dir / "source_manifest.json")
    pages = read_ndjson(raw_dir / "pages.ndjson")
    glyphs = read_ndjson(raw_dir / "glyphs.ndjson")
    review_items = read_ndjson(derived_dir / "review_queue" / "items.ndjson")

    review_items_by_page: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in review_items:
        page_id = str(item.get("page_id", "")).strip()
        if page_id:
            review_items_by_page[page_id].append(item)

    glyphs_by_page: dict[str, list[dict[str, object]]] = defaultdict(list)
    for glyph in glyphs:
        page_id = str(glyph.get("page_id", "")).strip()
        if not page_id:
            continue
        glyphs_by_page[page_id].append(glyph)

    candidate_pages: list[dict[str, object]] = []
    skipped_pages: list[dict[str, object]] = []

    for page in pages:
        page_id = str(page.get("page_id", "")).strip()
        if not page_id:
            continue

        page_glyphs = glyphs_by_page.get(page_id, [])
        music_glyphs = [glyph for glyph in page_glyphs if str(glyph.get("box_type", "")) == "Music"]
        title_glyphs = [glyph for glyph in page_glyphs if str(glyph.get("box_type", "")) == "Title"]
        reviewed_music_glyphs = [
            glyph
            for glyph in music_glyphs
            if isinstance(glyph.get("metadata"), dict) and str(glyph["metadata"].get("review_verdict", "")).strip()
        ]
        review_items_on_page = review_items_by_page.get(page_id, [])
        page_index = page.get("page_index")
        reviewed_music_count = len(reviewed_music_glyphs)
        music_box_count = len(music_glyphs)
        pending_review_count = len(review_items_on_page)

        if music_box_count == 0:
            skipped_pages.append(
                {
                    "page_id": page_id,
                    "page_index": page_index,
                    "review_state": "empty",
                    "reason": "no_music_boxes",
                    "music_box_count": music_box_count,
                    "reviewed_music_count": reviewed_music_count,
                    "pending_review_count": pending_review_count,
                }
            )
            continue

        if reviewed_music_count == 0:
            review_state = "untouched"
        elif reviewed_music_count >= music_box_count:
            review_state = "complete"
        else:
            review_state = "partial"

        row = {
            "page_id": page_id,
            "page_index": page_index,
            "review_state": review_state,
            "music_box_count": music_box_count,
            "title_box_count": len(title_glyphs),
            "reviewed_music_count": reviewed_music_count,
            "pending_review_count": pending_review_count,
            "reviewed_ratio": round(reviewed_music_count / float(music_box_count), 4) if music_box_count else 0.0,
            "queue_coverage_ratio": round(pending_review_count / float(music_box_count), 4) if music_box_count else 0.0,
            "score": _score_page(
                review_state=review_state,
                pending_review_count=pending_review_count,
                music_box_count=music_box_count,
                title_box_count=len(title_glyphs),
            ),
        }

        if review_state == "untouched" or include_partial_pages:
            candidate_pages.append(row)
        else:
            skipped_pages.append(
                {
                    **row,
                    "reason": "already_reviewed" if review_state == "complete" else "partially_reviewed",
                }
            )

    candidate_pages.sort(
        key=lambda row: (
            -int(row["score"]),
            -int(row["pending_review_count"]),
            -int(row["music_box_count"]),
            int(row["page_index"]) if isinstance(row.get("page_index"), int) else 10**9,
            str(row["page_id"]),
        )
    )

    selected_pages: list[dict[str, object]] = []
    selected_items: list[dict[str, object]] = []
    selected_page_count = 0
    selected_item_count = 0

    for page_rank, page_row in enumerate(candidate_pages, start=1):
        page_id = str(page_row["page_id"])
        page_items = sorted(
            review_items_by_page.get(page_id, []),
            key=lambda item: (
                PRIORITY_ORDER.get(str(item.get("priority", "low")), 99),
                -int(item.get("issue_count", 0)),
                str(item.get("review_id", "")),
            ),
        )
        if not page_items:
            continue

        if max_pages is not None and selected_page_count >= max_pages:
            break

        selected_pages.append(
            {
                **page_row,
                "selection_rank": page_rank,
                "selected_review_item_count": len(page_items),
            }
        )
        selected_page_count += 1
        selected_item_count += len(page_items)

        for item_order, item in enumerate(page_items, start=1):
            selected_items.append(
                {
                    "selection_rank": len(selected_items) + 1,
                    "page_selection_rank": page_rank,
                    "item_order_in_page": item_order,
                    "review_id": item.get("review_id", ""),
                    "glyph_id": item.get("glyph_id", ""),
                    "page_id": page_id,
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
            )

        if selected_item_count >= target_item_count:
            break

    selected_page_rank_by_page_id = {
        str(page["page_id"]): int(page["selection_rank"])
        for page in selected_pages
    }
    selected_item_count_by_page_id = {
        str(page["page_id"]): int(page["selected_review_item_count"])
        for page in selected_pages
    }

    recommendation = {
        "source_id": manifest.get("source_id"),
        "bundle_path": str(bundle_path.resolve()),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "target_item_count": target_item_count,
        "max_pages": max_pages,
        "include_partial_pages": include_partial_pages,
        "candidate_page_count": len(candidate_pages),
        "selected_page_count": len(selected_pages),
        "selected_item_count": len(selected_items),
        "skipped_page_count": len(skipped_pages),
        "selected_pages": selected_pages,
        "skipped_pages": skipped_pages[:100],
    }

    destination_dir = output_dir or (derived_dir / "next_batch")
    write_json(destination_dir / "recommendation.json", recommendation)
    write_json(destination_dir / "summary.json", {k: recommendation[k] for k in [
        "source_id",
        "generated_at",
        "target_item_count",
        "max_pages",
        "include_partial_pages",
        "candidate_page_count",
        "selected_page_count",
        "selected_item_count",
        "skipped_page_count",
    ]})
    write_ndjson(destination_dir / "pages.ndjson", candidate_pages)
    write_csv(
        destination_dir / "pages.csv",
        fieldnames=[
            "page_id",
            "page_index",
            "review_state",
            "music_box_count",
            "title_box_count",
            "reviewed_music_count",
            "pending_review_count",
            "reviewed_ratio",
            "queue_coverage_ratio",
            "score",
            "selection_rank",
            "selected_review_item_count",
        ],
        rows=[
            {
                **row,
                "selection_rank": selected_page_rank_by_page_id.get(str(row["page_id"]), ""),
                "selected_review_item_count": selected_item_count_by_page_id.get(str(row["page_id"]), ""),
            }
            for row in candidate_pages
        ],
    )
    write_ndjson(destination_dir / "selected_items.ndjson", selected_items)
    write_csv(
        destination_dir / "selected_items.csv",
        fieldnames=[
            "selection_rank",
            "page_selection_rank",
            "item_order_in_page",
            "review_id",
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
        rows=selected_items,
    )
    write_json(
        reports_dir / "next_batch_recommendation.json",
        {
            "destination_dir": str(destination_dir),
            "selected_page_count": len(selected_pages),
            "selected_item_count": len(selected_items),
            "candidate_page_count": len(candidate_pages),
        },
    )
    print(f"Wrote next-batch recommendation to {destination_dir}")
    return recommendation


def _score_page(*, review_state: str, pending_review_count: int, music_box_count: int, title_box_count: int) -> float:
    base = pending_review_count * 100.0 + music_box_count * 5.0 + title_box_count * 1.0
    if review_state == "untouched":
        base += 250.0
    elif review_state == "partial":
        base += 25.0
    return base
PRIORITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
}

"""Review queue generation for human correction workflows."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from dataset_tools.io_utils import read_json, read_ndjson, write_csv, write_json, write_ndjson
from dataset_tools.models.review_queue_item import ReviewQueueItem


PRIORITY_RULES = {
    "missing_acoustic_layer": "medium",
    "missing_position": "high",
    "unresolved_right_hand_technique": "high",
    "unresolved_left_hand_finger": "high",
}


def _resolve_priority(issues: list[str]) -> str:
    if any(PRIORITY_RULES.get(issue) == "high" for issue in issues):
        return "high"
    if any(PRIORITY_RULES.get(issue) == "medium" for issue in issues):
        return "medium"
    return "low"


def _suggest_action(issues: list[str]) -> str:
    if "missing_position" in issues:
        return "补充徽位和分位信息"
    if "unresolved_right_hand_technique" in issues:
        return "确认右手技法"
    if "unresolved_left_hand_finger" in issues:
        return "确认左手指法"
    if "missing_acoustic_layer" in issues:
        return "补充音高、时值和 MusicXML"
    return "人工复核"


def build_review_queue(bundle_path: Path) -> dict[str, object]:
    """Build a review queue from draft events that still have schema gaps."""
    raw_dir = bundle_path / "raw"
    derived_dir = bundle_path / "derived"
    reports_dir = bundle_path / "reports"

    manifest = read_json(raw_dir / "source_manifest.json")
    pages = read_ndjson(raw_dir / "pages.ndjson")
    glyphs = read_ndjson(raw_dir / "glyphs.ndjson")
    drafts = read_ndjson(derived_dir / "jianzi_code_drafts" / "event_drafts.ndjson")
    normalized_notes = read_ndjson(derived_dir / "normalized_notes" / "notes.ndjson")
    page_id_by_glyph_id = {
        str(note.get("glyph_id", "")): str(note.get("page_id", ""))
        for note in normalized_notes
    }
    page_info_by_page_id = {
        str(page.get("page_id", "")): {
            "page_index": page.get("page_index"),
            "image_path": page.get("image_path"),
        }
        for page in pages
    }
    glyph_info_by_glyph_id = {}
    for glyph in glyphs:
        glyph_id = str(glyph.get("glyph_id", ""))
        metadata = glyph.get("metadata", {}) if isinstance(glyph.get("metadata"), dict) else {}
        glyph_info_by_glyph_id[glyph_id] = {
            "crop_ref": metadata.get("crop_ref"),
            "detection_confidence": metadata.get("detection_confidence"),
        }

    items: list[dict[str, object]] = []
    priority_counts: Counter[str] = Counter()

    for draft in drafts:
        issues = [str(item) for item in draft.get("schema_gaps", [])] if isinstance(draft.get("schema_gaps"), list) else []
        if not issues:
            continue

        event_draft = draft.get("event_draft", {})
        visual = event_draft.get("visual", {}) if isinstance(event_draft, dict) else {}
        metadata = draft.get("metadata", {}) if isinstance(draft.get("metadata"), dict) else {}
        glyph_id = str(draft.get("glyph_id", ""))
        page_id = page_id_by_glyph_id.get(glyph_id, "")
        page_info = page_info_by_page_id.get(page_id, {})
        glyph_info = glyph_info_by_glyph_id.get(glyph_id, {})
        priority = _resolve_priority(issues)
        priority_counts.update([priority])

        item = ReviewQueueItem(
            review_id=str(draft.get("draft_id", "")),
            source_id=str(manifest.get("source_id", "")),
            glyph_id=glyph_id,
            page_id=page_id,
            page_index=page_info.get("page_index") if isinstance(page_info.get("page_index"), int) else None,
            priority=priority,
            issue_count=len(issues),
            issues=issues,
            visual_char_text=str(visual.get("char_text", "")),
            notation_kind=str(metadata.get("notation_kind")) if metadata.get("notation_kind") is not None else None,
            suggested_action=_suggest_action(issues),
            crop_ref=str(glyph_info.get("crop_ref")) if glyph_info.get("crop_ref") else None,
            image_path=str(page_info.get("image_path")) if page_info.get("image_path") else None,
            detection_confidence=float(glyph_info.get("detection_confidence")) if isinstance(glyph_info.get("detection_confidence"), (int, float)) else None,
            metadata={
                "review_reasons": metadata.get("review_reasons", []),
            },
        )
        items.append(item.to_dict())

    review_dir = derived_dir / "review_queue"
    write_ndjson(review_dir / "items.ndjson", items)
    report = {
        "source_id": manifest.get("source_id"),
        "review_item_count": len(items),
        "priority_counts": dict(priority_counts),
    }
    csv_rows = [
        {
            "review_id": item["review_id"],
            "source_id": item["source_id"],
            "glyph_id": item["glyph_id"],
            "page_id": item["page_id"],
            "page_index": item["page_index"] if item["page_index"] is not None else "",
            "priority": item["priority"],
            "issue_count": item["issue_count"],
            "issues": "|".join(item["issues"]),
            "visual_char_text": item["visual_char_text"],
            "notation_kind": item["notation_kind"] or "",
            "suggested_action": item["suggested_action"],
            "detection_confidence": item["detection_confidence"] if item["detection_confidence"] is not None else "",
            "crop_ref": item["crop_ref"] or "",
            "image_path": item["image_path"] or "",
        }
        for item in items
    ]
    write_csv(
        review_dir / "items.csv",
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
        rows=csv_rows,
    )
    write_json(review_dir / "review_report.json", report)
    write_json(reports_dir / "review_queue_summary.json", report)
    print(f"Wrote {len(items)} review queue item(s) to {review_dir / 'items.ndjson'}")
    return report

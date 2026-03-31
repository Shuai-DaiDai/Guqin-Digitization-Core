"""Export blank review-decision templates for human correction work."""

from __future__ import annotations

from pathlib import Path

from dataset_tools.io_utils import read_ndjson, write_csv


def export_review_decisions_template(
    *,
    bundle_path: Path,
    output_path: Path,
    batch_id: str | None = None,
) -> dict[str, object]:
    """Write a blank CSV template for human review decisions."""
    review_dir = bundle_path / "derived" / "review_queue"
    if batch_id:
        items_path = review_dir / "batches" / batch_id / "items.ndjson"
    else:
        items_path = review_dir / "items.ndjson"

    items = read_ndjson(items_path)
    rows = []
    for item in items:
        issues = item.get("issues", [])
        rows.append(
            {
                "review_id": item.get("review_id", ""),
                "decision_status": "",
                "resolved_issues": "",
                "resolved_string": "",
                "resolved_hui": "",
                "resolved_fraction": "",
                "resolved_right_hand_technique": "",
                "resolved_left_hand_finger": "",
                "resolved_pitch_name": "",
                "resolved_midi_note": "",
                "resolved_duration_beats": "",
                "resolved_musicxml_snippet": "",
                "resolution_note": "",
                "current_issues": "|".join(issues) if isinstance(issues, list) else "",
                "suggested_action": item.get("suggested_action", ""),
                "page_id": item.get("page_id", ""),
                "page_index": item.get("page_index", ""),
                "crop_ref": item.get("crop_ref", "") or "",
                "image_path": item.get("image_path", "") or "",
                "detection_confidence": item.get("detection_confidence", "") if item.get("detection_confidence") is not None else "",
            }
        )

    write_csv(
        output_path,
        fieldnames=[
            "review_id",
            "decision_status",
            "resolved_issues",
            "resolved_string",
            "resolved_hui",
            "resolved_fraction",
            "resolved_right_hand_technique",
            "resolved_left_hand_finger",
            "resolved_pitch_name",
            "resolved_midi_note",
            "resolved_duration_beats",
            "resolved_musicxml_snippet",
            "resolution_note",
            "current_issues",
            "suggested_action",
            "page_id",
            "page_index",
            "crop_ref",
            "image_path",
            "detection_confidence",
        ],
        rows=rows,
    )
    print(f"Wrote review decisions template to {output_path}")
    return {
        "row_count": len(rows),
        "output_path": str(output_path),
        "batch_id": batch_id,
    }

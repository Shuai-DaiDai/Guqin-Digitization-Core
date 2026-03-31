"""Template export helpers for manual preparation workflows."""

from __future__ import annotations

from pathlib import Path

from dataset_tools.io_utils import write_csv


def export_manual_templates(output_dir: Path) -> dict[str, object]:
    """Write blank CSV templates for manual preparation and review workflows."""
    metadata_rows = [
        {
            "source_id": "",
            "piece_title": "",
            "source_book": "",
            "edition_note": "",
            "image_file": "",
            "page_number_original": "",
            "page_number_in_piece": "",
            "source_url": "",
            "tuning": "",
            "performer_or_transcriber": "",
            "rights_note": "",
            "quality_note": "",
            "remarks": "",
        }
    ]
    annotation_rows = [
        {
            "image_file": "",
            "line_index": "",
            "glyph_index": "",
            "bbox_x1": "",
            "bbox_y1": "",
            "bbox_x2": "",
            "bbox_y2": "",
            "char_guess": "",
            "component_guess": "",
            "confidence": "",
            "needs_review": "",
            "note": "",
            "note_type": "",
            "string_number": "",
            "hui_guess": "",
            "fraction_guess": "",
            "right_hand_guess": "",
            "left_hand_guess": "",
        }
    ]
    decisions_rows = [
        {
            "review_id": "",
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
        }
    ]

    write_csv(output_dir / "metadata.template.csv", list(metadata_rows[0].keys()), metadata_rows)
    write_csv(output_dir / "annotations.template.csv", list(annotation_rows[0].keys()), annotation_rows)
    write_csv(output_dir / "review_decisions.template.csv", list(decisions_rows[0].keys()), decisions_rows)
    print(f"Wrote manual workflow templates to {output_dir}")
    return {
        "output_dir": str(output_dir),
        "templates": [
            "metadata.template.csv",
            "annotations.template.csv",
            "review_decisions.template.csv",
        ],
    }

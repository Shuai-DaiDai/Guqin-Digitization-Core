"""Apply human review decisions back into draft events."""

from __future__ import annotations

from pathlib import Path

from dataset_tools.io_utils import read_csv, read_ndjson, write_json, write_ndjson


def _parse_int(value: object) -> int | None:
    try:
        stripped = str(value).strip()
        return int(stripped) if stripped else None
    except ValueError:
        return None


def _parse_float(value: object) -> float | None:
    try:
        stripped = str(value).strip()
        return float(stripped) if stripped else None
    except ValueError:
        return None


def apply_review_decisions(bundle_path: Path, decisions_path: Path) -> dict[str, object]:
    """Apply human review decisions CSV to draft events."""
    draft_dir = bundle_path / "derived" / "jianzi_code_drafts"
    review_dir = bundle_path / "derived" / "review_queue"

    drafts = read_ndjson(draft_dir / "event_drafts.ndjson")
    decisions = read_csv(decisions_path)
    decisions_by_review_id = {
        str(row.get("review_id", "")).strip(): row
        for row in decisions
        if str(row.get("review_id", "")).strip()
    }

    updated_count = 0
    unresolved_count = 0

    for draft in drafts:
        review_id = str(draft.get("draft_id", ""))
        decision = decisions_by_review_id.get(review_id)
        if decision is None:
            unresolved_count += 1
            continue

        event_draft = draft.get("event_draft", {})
        if not isinstance(event_draft, dict):
            unresolved_count += 1
            continue
        physical = event_draft.get("physical", {})
        if not isinstance(physical, dict):
            unresolved_count += 1
            continue
        left_hand = physical.get("left_hand", {})
        right_hand = physical.get("right_hand", {})
        position = physical.get("position", {})
        if not isinstance(left_hand, dict) or not isinstance(right_hand, dict) or not isinstance(position, dict):
            unresolved_count += 1
            continue

        string_number = _parse_int(decision.get("resolved_string"))
        if string_number is not None:
            physical["string"] = string_number
        hui = _parse_int(decision.get("resolved_hui"))
        if hui is not None:
            position["hui"] = hui
        fraction = _parse_float(decision.get("resolved_fraction"))
        if fraction is not None:
            position["fraction"] = fraction

        right_hand_technique = str(decision.get("resolved_right_hand_technique", "")).strip()
        if right_hand_technique:
            right_hand["technique"] = right_hand_technique
        left_hand_finger = str(decision.get("resolved_left_hand_finger", "")).strip()
        if left_hand_finger:
            left_hand["finger"] = left_hand_finger

        pitch_name = str(decision.get("resolved_pitch_name", "")).strip()
        midi_note = _parse_int(decision.get("resolved_midi_note"))
        duration_beats = _parse_float(decision.get("resolved_duration_beats"))
        musicxml_snippet = str(decision.get("resolved_musicxml_snippet", "")).strip()
        if pitch_name or midi_note is not None or duration_beats is not None or musicxml_snippet:
            event_draft["acoustic"] = {
                "pitch_name": pitch_name or "C3",
                "midi_note": midi_note if midi_note is not None else 48,
                "duration_beats": duration_beats if duration_beats is not None else 1.0,
                "musicxml_snippet": musicxml_snippet or "<note/>",
            }

        resolved_issues = {
            issue.strip()
            for issue in str(decision.get("resolved_issues", "")).split("|")
            if issue.strip()
        }
        draft["schema_gaps"] = [
            str(issue)
            for issue in draft.get("schema_gaps", [])
            if str(issue) not in resolved_issues
        ] if isinstance(draft.get("schema_gaps"), list) else []

        metadata = draft.get("metadata", {})
        if isinstance(metadata, dict):
            metadata["review_resolution_note"] = str(decision.get("resolution_note", "")).strip()
            metadata["review_decision_status"] = str(decision.get("decision_status", "")).strip() or "applied"
        updated_count += 1

    write_ndjson(draft_dir / "event_drafts.ndjson", drafts)
    report = {
        "decisions_path": str(decisions_path),
        "updated_count": updated_count,
        "unresolved_count": unresolved_count,
        "remaining_gap_count": sum(
            len(draft.get("schema_gaps", []))
            for draft in drafts
            if isinstance(draft.get("schema_gaps"), list)
        ),
    }
    write_json(review_dir / "reconcile_report.json", report)
    print(f"Applied review decisions from {decisions_path}")
    return report

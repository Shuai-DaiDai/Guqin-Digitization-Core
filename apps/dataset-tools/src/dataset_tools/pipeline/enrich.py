"""Rule-based enrichment from normalized notes toward Jianzi-Code drafts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from dataset_tools.io_utils import read_json, read_ndjson, write_json, write_ndjson
from dataset_tools.models.jianzi_event_draft import JianziEventDraft


RIGHT_HAND_TECHNIQUE_MAP = {
    "勾": "gou",
    "抹": "mo",
    "挑": "tiao",
    "剔": "ti",
    "打": "da",
    "擘": "bo",
    "拂": "fu",
    "轮": "lun",
    "劈": "pi",
    "摘": "zhai",
}

LEFT_HAND_PITCH_MAP = {
    "吟": "yin",
    "猱": "nao",
    "绰": "chuo",
    "注": "zhu",
    "进": "jin",
    "退": "tui",
    "泛起": "fanqi",
}

LEFT_HAND_ORNAMENT_MAP = {
    "吟": "vibrato",
    "猱": "vibrato",
    "绰": "slide_in",
    "注": "slide_out",
}


def _first_matching_symbol(text: str, mapping: dict[str, str]) -> str | None:
    for symbol, mapped_value in mapping.items():
        if symbol in text:
            return mapped_value
    return None


def _parse_fraction(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric if 0 <= numeric < 1 else None
    stripped = str(value).strip()
    if not stripped:
        return None
    try:
        numeric = float(stripped)
    except ValueError:
        return None
    return numeric if 0 <= numeric < 1 else None


def _infer_note_type(note: dict[str, object]) -> str:
    note_type_guess = str(note.get("note_type_guess", "unknown"))
    visual_char_text = str(note.get("visual_char_text", ""))
    left_hand_symbols = note.get("left_hand_symbols", [])
    notation_kind = note.get("notation_kind")
    string_number = note.get("string_number")

    if "泛" in visual_char_text:
        return "harmonic"
    if note_type_guess == "open":
        return "open"
    if note_type_guess == "harmonic":
        return "harmonic"
    if note_type_guess == "stopped":
        return "stopped"
    if isinstance(left_hand_symbols, list) and left_hand_symbols:
        return "stopped"
    if notation_kind == "LEFT_HAND":
        return "stopped"
    if note_type_guess == "compound":
        return "stopped"
    if notation_kind == "STRING_NUMBER" and isinstance(string_number, int):
        return "open"
    return "stopped"


def _infer_right_hand_technique(
    visual_char_text: str,
    components: dict[str, object],
    raw_notation_payload: dict[str, object] | None = None,
) -> str:
    explicit_guess = None
    if isinstance(raw_notation_payload, dict):
        explicit_guess = raw_notation_payload.get("right_hand_guess")
    if isinstance(explicit_guess, str) and explicit_guess.strip():
        lowered = explicit_guess.strip().lower()
        if lowered in RIGHT_HAND_TECHNIQUE_MAP.values():
            return lowered
        return f"custom:{lowered}"

    search_parts = [visual_char_text] + [str(value) for value in components.values() if value]
    search_text = "".join(search_parts)
    return _first_matching_symbol(search_text, RIGHT_HAND_TECHNIQUE_MAP) or "custom:unresolved"


def _infer_left_hand_pitch_variation(left_hand_symbols: list[str]) -> str:
    joined = "".join(left_hand_symbols)
    return _first_matching_symbol(joined, LEFT_HAND_PITCH_MAP) or "none"


def _infer_ornaments(left_hand_symbols: list[str]) -> list[str]:
    joined = "".join(left_hand_symbols)
    ornaments: list[str] = []
    for symbol, ornament in LEFT_HAND_ORNAMENT_MAP.items():
        if symbol in joined and ornament not in ornaments:
            ornaments.append(ornament)
    return ornaments


def enrich_bundle(bundle_path: Path) -> dict[str, object]:
    """Build rule-based Jianzi-Code draft events from normalized notes."""
    raw_dir = bundle_path / "raw"
    derived_dir = bundle_path / "derived"
    draft_dir = derived_dir / "jianzi_code_drafts"

    manifest = read_json(raw_dir / "source_manifest.json")
    raw_glyphs = read_ndjson(raw_dir / "glyphs.ndjson")
    normalized_notes = read_ndjson(derived_dir / "normalized_notes" / "notes.ndjson")
    candidates = read_ndjson(derived_dir / "jianzi_code_candidates" / "candidates.ndjson")
    raw_glyph_by_id = {str(glyph.get("glyph_id", "")): glyph for glyph in raw_glyphs}
    candidate_by_id = {str(candidate.get("candidate_id", "")): candidate for candidate in candidates}

    drafts: list[dict[str, object]] = []
    gap_counts: Counter[str] = Counter()
    note_type_counts: Counter[str] = Counter()
    right_hand_counts: Counter[str] = Counter()

    for note in normalized_notes:
        candidate = candidate_by_id.get(str(note.get("note_id", "")), {})
        raw_glyph = raw_glyph_by_id.get(str(note.get("glyph_id", "")), {})
        raw_notation_payload = (
            raw_glyph.get("raw_notation_payload", {}) if isinstance(raw_glyph, dict) else {}
        )
        partial_event = candidate.get("partial_event", {}) if isinstance(candidate, dict) else {}
        visual = partial_event.get("visual", {}) if isinstance(partial_event, dict) else {}
        visual_components = visual.get("components", {}) if isinstance(visual, dict) else {}

        visual_char_text = str(note.get("visual_char_text", ""))
        left_hand_symbols = (
            [str(item) for item in note.get("left_hand_symbols", [])]
            if isinstance(note.get("left_hand_symbols"), list)
            else []
        )

        note_type = _infer_note_type(note)
        right_hand_technique = _infer_right_hand_technique(
            visual_char_text=visual_char_text,
            components=visual_components if isinstance(visual_components, dict) else {},
            raw_notation_payload=raw_notation_payload if isinstance(raw_notation_payload, dict) else None,
        )
        left_hand_pitch = _infer_left_hand_pitch_variation(left_hand_symbols)
        ornaments = _infer_ornaments(left_hand_symbols)
        timbre_variation = {
            "open": "open_string",
            "harmonic": "harmonic",
            "stopped": "stopped_string",
        }[note_type]

        position_hui = None
        position_fraction = None
        if isinstance(raw_notation_payload, dict):
            hui_guess = raw_notation_payload.get("hui_guess")
            position_hui = hui_guess if isinstance(hui_guess, int) else None
            position_fraction = _parse_fraction(raw_notation_payload.get("fraction_guess"))

        schema_gaps = ["missing_acoustic_layer"]
        if position_hui is None and position_fraction is None:
            schema_gaps.append("missing_position")
        if right_hand_technique == "custom:unresolved":
            schema_gaps.append("unresolved_right_hand_technique")
        if note_type == "stopped":
            schema_gaps.append("unresolved_left_hand_finger")

        gap_counts.update(schema_gaps)
        note_type_counts.update([note_type])
        right_hand_counts.update([right_hand_technique])

        draft = JianziEventDraft(
            draft_id=str(note.get("note_id", "")),
            source_id=str(manifest.get("source_id", "")),
            glyph_id=str(note.get("glyph_id", "")),
            event_draft={
                "id": str(note.get("note_id", "")),
                "visual": {
                    "char_text": visual_char_text,
                    "layout": str(visual.get("layout", "single")) if isinstance(visual, dict) else "single",
                    "components": visual_components if isinstance(visual_components, dict) else {},
                },
                "physical": {
                    "note_type": note_type,
                    "string": note.get("string_number"),
                    "position": {
                        "hui": position_hui,
                        "fraction": position_fraction,
                    },
                    "right_hand": {
                        "finger": "unknown",
                        "technique": right_hand_technique,
                    },
                    "left_hand": {
                        "finger": "none" if note_type in {"open", "harmonic"} else "unknown",
                        "pitch_variation": left_hand_pitch,
                        "timbre_variation": timbre_variation,
                    },
                    "ornaments": ornaments,
                },
            },
            schema_gaps=schema_gaps,
            confidence=str(note.get("candidate_confidence", "low")),
            metadata={
                "notation_kind": note.get("notation_kind"),
                "needs_review": note.get("needs_review"),
                "review_reasons": note.get("review_reasons", []),
                "raw_note_type_guess": note.get("note_type_guess"),
            },
        )
        drafts.append(draft.to_dict())

    write_ndjson(draft_dir / "event_drafts.ndjson", drafts)
    report = {
        "source_id": manifest.get("source_id"),
        "draft_count": len(drafts),
        "note_type_counts": dict(note_type_counts),
        "right_hand_technique_counts": dict(right_hand_counts),
        "schema_gap_counts": dict(gap_counts),
    }
    write_json(draft_dir / "draft_report.json", report)
    print(f"Wrote {len(drafts)} Jianzi-Code draft event(s) to {draft_dir / 'event_drafts.ndjson'}")
    return report

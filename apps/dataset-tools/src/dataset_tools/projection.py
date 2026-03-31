"""Projection helpers from imported notation objects to Jianzi-Code candidates."""

from __future__ import annotations

from typing import Any

from dataset_tools.models.jianzi_candidate import JianziCodeCandidate


def _collect_tree_leaves(node: Any) -> list[str]:
    if not isinstance(node, dict):
        return []
    content = node.get("content")
    children = node.get("children")
    if isinstance(children, list) and children:
        leaves: list[str] = []
        for child in children:
            leaves.extend(_collect_tree_leaves(child))
        return leaves
    if isinstance(content, str):
        return [content]
    return []


def _infer_visual_payload(raw_notation_payload: object) -> tuple[str, dict[str, object]]:
    char_text = ""
    components = {
        "top_left": None,
        "top_right": None,
        "bottom_inner": None,
        "bottom_outer": None,
    }
    if not isinstance(raw_notation_payload, dict):
        return char_text, components

    notation_type = raw_notation_payload.get("type")
    if notation_type == "STRING_NUMBER":
        content = raw_notation_payload.get("content")
        char_text = str(content) if content is not None else ""
    elif notation_type == "LEFT_HAND":
        content = raw_notation_payload.get("content")
        if isinstance(content, list):
            char_text = "".join(str(item) for item in content)
            if content:
                components["top_left"] = str(content[0])
                if len(content) > 1:
                    components["bottom_inner"] = str(content[1])
    elif notation_type == "FULL_JIANZIPU":
        leaves = _collect_tree_leaves(raw_notation_payload.get("content"))
        char_text = "".join(leaves)
        slots = ["top_left", "top_right", "bottom_inner", "bottom_outer"]
        for slot, value in zip(slots, leaves):
            components[slot] = value
    elif notation_type == "MANUAL_GUESS":
        char_text = str(raw_notation_payload.get("char_guess") or "")
        component_guess = str(raw_notation_payload.get("component_guess") or "")
        if component_guess:
            component_parts = [part.strip() for part in component_guess.split("|") if part.strip()]
            slots = ["top_left", "top_right", "bottom_inner", "bottom_outer"]
            for slot, value in zip(slots, component_parts):
                components[slot] = value
    elif notation_type == "OCR_CANDIDATES":
        char_text = str(raw_notation_payload.get("char_guess") or "")
        component_candidates = raw_notation_payload.get("component_candidates")
        if isinstance(component_candidates, list):
            for item in component_candidates:
                if not isinstance(item, dict):
                    continue
                slot = item.get("slot")
                label = item.get("label")
                if slot in components and isinstance(label, str) and label:
                    components[str(slot)] = label

    return char_text, components


def _infer_layout(raw_notation_payload: object) -> str:
    if not isinstance(raw_notation_payload, dict):
        return "single"
    layout_guess = raw_notation_payload.get("layout_guess")
    if isinstance(layout_guess, str) and layout_guess:
        return layout_guess
    return "single"


def _map_confidence_level(raw_notation_payload: object) -> str:
    if not isinstance(raw_notation_payload, dict):
        return "low"
    numeric = raw_notation_payload.get("calibrated_confidence")
    if not isinstance(numeric, (int, float)):
        numeric = raw_notation_payload.get("top_candidate_confidence")
    if not isinstance(numeric, (int, float)):
        return "low"
    if numeric >= 0.75:
        return "high"
    if numeric >= 0.45:
        return "medium"
    return "low"


def _infer_physical_payload(raw_notation_payload: object) -> dict[str, object]:
    physical = {
        "string": None,
        "left_hand_symbols": [],
        "note_type_guess": "unknown",
    }
    if not isinstance(raw_notation_payload, dict):
        return physical

    notation_type = raw_notation_payload.get("type")
    if notation_type == "STRING_NUMBER":
        content = raw_notation_payload.get("content")
        physical["string"] = int(content) if isinstance(content, str) and content.isdigit() else None
    elif notation_type == "LEFT_HAND":
        content = raw_notation_payload.get("content")
        if isinstance(content, list):
            physical["left_hand_symbols"] = [str(item) for item in content]
            physical["note_type_guess"] = "stopped"
    elif notation_type == "FULL_JIANZIPU":
        physical["note_type_guess"] = "compound"
    elif notation_type == "MANUAL_GUESS":
        string_value = raw_notation_payload.get("string")
        physical["string"] = string_value if isinstance(string_value, int) else None
        if isinstance(raw_notation_payload.get("left_hand_symbols"), list):
            physical["left_hand_symbols"] = [
                str(item) for item in raw_notation_payload.get("left_hand_symbols", [])
            ]
        physical["note_type_guess"] = str(raw_notation_payload.get("note_type_guess", "unknown"))
    elif notation_type == "OCR_CANDIDATES":
        glyph_candidates = raw_notation_payload.get("glyph_candidates")
        if isinstance(glyph_candidates, list):
            top_label = None
            top_confidence = -1.0
            for candidate in glyph_candidates:
                if not isinstance(candidate, dict):
                    continue
                confidence = candidate.get("confidence")
                numeric_confidence = float(confidence) if isinstance(confidence, (int, float)) else 0.0
                if numeric_confidence > top_confidence:
                    top_confidence = numeric_confidence
                    top_label = candidate.get("label")
            if isinstance(top_label, str) and top_label.isdigit():
                physical["string"] = int(top_label)
                physical["note_type_guess"] = "open"

    return physical


def project_candidate(glyph: dict[str, object], source_id: str) -> JianziCodeCandidate | None:
    """Project one imported glyph into a partial Jianzi-Code candidate."""
    if glyph.get("box_type") != "Music":
        return None
    if glyph.get("is_excluded_from_dataset") is True:
        return None

    raw_notation_payload = glyph.get("raw_notation_payload")
    char_text, components = _infer_visual_payload(raw_notation_payload)
    layout = _infer_layout(raw_notation_payload)
    confidence = _map_confidence_level(raw_notation_payload)
    physical = _infer_physical_payload(raw_notation_payload)
    notation_kind = raw_notation_payload.get("type") if isinstance(raw_notation_payload, dict) else None

    candidate = JianziCodeCandidate(
        candidate_id=f"{glyph['glyph_id']}-candidate",
        glyph_id=str(glyph["glyph_id"]),
        source_id=source_id,
        candidate_status="projected_partial",
        confidence=confidence,
        partial_event={
            "id": f"{glyph['glyph_id']}-event",
            "visual": {
                "char_text": char_text,
                "layout": layout,
                "components": components,
            },
            "physical_guess": physical,
        },
        provenance={
            "source_box_index": glyph.get("source_box_index"),
            "page_id": glyph.get("page_id"),
            "notation_kind": notation_kind,
        },
    )
    return candidate

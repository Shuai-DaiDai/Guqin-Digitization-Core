"""Normalized note record model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class NormalizedNoteRecord:
    """Intermediate normalized note record derived from a projected candidate."""

    note_id: str
    source_id: str
    glyph_id: str
    page_id: str
    notation_kind: str | None
    visual_char_text: str
    string_number: int | None
    note_type_guess: str
    left_hand_symbols: list[str] = field(default_factory=list)
    candidate_confidence: str = "low"
    needs_review: bool = True
    review_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize the normalized record into a JSON-friendly dictionary."""
        return asdict(self)

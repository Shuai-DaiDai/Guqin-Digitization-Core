"""Enriched Jianzi-Code draft event model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class JianziEventDraft:
    """Draft event that moves imported data closer to the Jianzi-Code schema."""

    draft_id: str
    source_id: str
    glyph_id: str
    event_draft: dict[str, object]
    schema_gaps: list[str] = field(default_factory=list)
    confidence: str = "low"
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize the draft into a JSON-friendly dictionary."""
        return asdict(self)

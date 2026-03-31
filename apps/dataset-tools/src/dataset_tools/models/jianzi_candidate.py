"""Jianzi-Code candidate model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class JianziCodeCandidate:
    """Partial Jianzi-Code candidate projected from imported notation data."""

    candidate_id: str
    glyph_id: str
    source_id: str
    candidate_status: str
    confidence: str
    partial_event: dict[str, object]
    provenance: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize the candidate into a JSON-friendly dictionary."""
        return asdict(self)

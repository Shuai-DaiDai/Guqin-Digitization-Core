"""Human review queue item model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class ReviewQueueItem:
    """One human-review task derived from a Jianzi-Code draft event."""

    review_id: str
    source_id: str
    glyph_id: str
    page_id: str
    priority: str
    issue_count: int
    page_index: int | None = None
    issues: list[str] = field(default_factory=list)
    visual_char_text: str = ""
    notation_kind: str | None = None
    suggested_action: str = ""
    crop_ref: str | None = None
    image_path: str | None = None
    detection_confidence: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize the review item into a JSON-friendly dictionary."""
        return asdict(self)

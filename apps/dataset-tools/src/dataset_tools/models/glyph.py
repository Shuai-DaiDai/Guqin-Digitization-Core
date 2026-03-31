"""Glyph record model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class GlyphRecord:
    """Normalized glyph/box record derived from an external annotation tool."""

    glyph_id: str
    page_id: str
    source_box_index: int
    box_type: str
    order_index: int
    text_bbox: list[list[int]] | None
    notation_bbox: list[list[int]] | None
    text_content: object | None
    raw_notation_payload: object | None
    is_excluded_from_dataset: bool
    is_line_break: bool
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize the glyph record into a JSON-friendly dictionary."""
        return asdict(self)

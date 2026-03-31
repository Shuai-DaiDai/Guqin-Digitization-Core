"""Page record model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class PageRecord:
    """Normalized page-level object inside the internal workspace."""

    page_id: str
    source_id: str
    page_index: int
    image_path: str
    width: int | None = None
    height: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize the page record into a JSON-friendly dictionary."""
        return asdict(self)

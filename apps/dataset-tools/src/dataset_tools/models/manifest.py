"""Source manifest model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class SourceManifest:
    """Normalized source-level metadata for an imported corpus artifact."""

    source_id: str
    source_type: str
    source_file: str
    notation_type: str
    composer: str
    piece_title: str
    image_paths: list[str]
    imported_at: str
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize the manifest into a JSON-friendly dictionary."""
        return asdict(self)

"""Import log model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class ImportLog:
    """Machine-readable log for one import run."""

    import_id: str
    importer: str
    input_path: str
    output_path: str
    imported_at: str
    summary: dict[str, object]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize the import log into a JSON-friendly dictionary."""
        return asdict(self)

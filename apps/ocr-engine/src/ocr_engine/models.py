"""Data models for OCR engine bundles and detections."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class OCRBundleManifest:
    """Metadata describing one OCR run."""

    bundle_id: str
    source_id: str
    detector_name: str
    created_at: str
    input_paths: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OCRPage:
    """One input page processed by OCR."""

    page_id: str
    image_path: str
    width: int
    height: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OCRDetection:
    """One detected object or candidate box."""

    detection_id: str
    page_id: str
    box_type: str
    bbox: list[list[int]]
    confidence: float
    label: str
    source_detector: str
    glyph_id: str | None = None
    order_index: int | None = None
    layout_guess: str | None = None
    calibrated_confidence: float | None = None
    crop_ref: str | None = None
    needs_review_hint: str | None = None
    score_breakdown: dict[str, float] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OCRGlyphCandidate:
    """Glyph-level top-k candidate for one detection."""

    glyph_id: str
    rank: int
    label: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OCRComponentCandidate:
    """Component-level candidate for one detection."""

    glyph_id: str
    slot: str
    label: str
    bbox: list[list[int]]
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OCRBundle:
    """Bundle written by the OCR engine for downstream tools."""

    manifest: OCRBundleManifest
    pages: list[OCRPage]
    detections: list[OCRDetection]
    glyph_candidates: list[OCRGlyphCandidate]
    component_candidates: list[OCRComponentCandidate]
    summary: dict[str, Any]
    validation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "pages": [page.to_dict() for page in self.pages],
            "detections": [detection.to_dict() for detection in self.detections],
            "glyph_candidates": [candidate.to_dict() for candidate in self.glyph_candidates],
            "component_candidates": [candidate.to_dict() for candidate in self.component_candidates],
            "summary": dict(self.summary),
            "validation": dict(self.validation),
        }

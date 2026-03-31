"""Adapter for OCR-engine output bundles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dataset_tools.adapters.gui_tools import _normalize_bbox, _slugify
from dataset_tools.io_utils import read_json, read_ndjson
from dataset_tools.models.glyph import GlyphRecord
from dataset_tools.models.manifest import SourceManifest
from dataset_tools.models.page import PageRecord


@dataclass(slots=True)
class OcrBundleImport:
    """In-memory representation of imported OCR bundle data."""

    manifest: SourceManifest
    pages: list[PageRecord]
    glyphs: list[GlyphRecord]
    warnings: list[str]


def _normalize_bbox_object(raw_bbox: object) -> list[list[int]] | None:
    if isinstance(raw_bbox, list):
        return _normalize_bbox(raw_bbox)
    if isinstance(raw_bbox, dict):
        x1 = raw_bbox.get("x1")
        y1 = raw_bbox.get("y1")
        x2 = raw_bbox.get("x2")
        y2 = raw_bbox.get("y2")
        if all(isinstance(value, int) for value in [x1, y1, x2, y2]):
            return [[x1, y1], [x2, y2]]
    return None


def load_ocr_bundle(bundle_path: Path) -> OcrBundleImport:
    """Parse a standard OCR bundle into internal workspace records."""
    manifest_path = bundle_path / "manifest.json"
    pages_path = bundle_path / "pages.ndjson"
    if not pages_path.exists():
        pages_path = bundle_path / "raw" / "pages.ndjson"

    detections_path = bundle_path / "glyph_detections.ndjson"
    if not detections_path.exists():
        detections_path = bundle_path / "raw" / "detections.ndjson"

    glyph_candidates_path = bundle_path / "glyph_candidates.ndjson"
    if not glyph_candidates_path.exists():
        glyph_candidates_path = bundle_path / "raw" / "glyph_candidates.ndjson"

    component_candidates_path = bundle_path / "component_candidates.ndjson"
    if not component_candidates_path.exists():
        component_candidates_path = bundle_path / "raw" / "component_candidates.ndjson"

    if not manifest_path.exists():
        raise ValueError(f"OCR bundle is missing manifest.json: {bundle_path}")

    raw_manifest = read_json(manifest_path)
    raw_pages = read_ndjson(pages_path)
    raw_detections = read_ndjson(detections_path)
    raw_glyph_candidates = read_ndjson(glyph_candidates_path) if glyph_candidates_path.exists() else []
    raw_component_candidates = read_ndjson(component_candidates_path) if component_candidates_path.exists() else []
    warnings: list[str] = []

    source_id = _slugify(str(raw_manifest.get("source_id") or bundle_path.name))
    image_paths: list[str] = []
    pages: list[PageRecord] = []

    for page_index, page in enumerate(raw_pages, start=1):
        image_path = str(page.get("image_path", ""))
        if image_path:
            image_paths.append(image_path)
        pages.append(
            PageRecord(
                page_id=str(page.get("page_id") or f"{source_id}-page-{page_index:03d}"),
                source_id=source_id,
                page_index=int(page.get("page_index") or page.get("metadata", {}).get("page_index", page_index)),
                image_path=image_path,
                width=page.get("width") if isinstance(page.get("width"), int) else None,
                height=page.get("height") if isinstance(page.get("height"), int) else None,
                metadata={
                    "preprocess": page.get("preprocess") or page.get("metadata", {}).get("preprocess"),
                    "layout_regions": page.get("layout_regions") or page.get("metadata", {}).get("layout_regions"),
                    "ocr_metadata": page.get("metadata", {}),
                },
            )
        )

    glyph_candidates_by_id: dict[str, list[dict[str, object]]] = {}
    for item in raw_glyph_candidates:
        glyph_id = str(item.get("glyph_id", ""))
        glyph_candidates_by_id.setdefault(glyph_id, []).append(item)

    component_candidates_by_id: dict[str, list[dict[str, object]]] = {}
    for item in raw_component_candidates:
        glyph_id = str(item.get("glyph_id", ""))
        component_candidates_by_id.setdefault(glyph_id, []).append(item)

    glyphs: list[GlyphRecord] = []
    for order_index, detection in enumerate(raw_detections, start=1):
        glyph_id = str(
            detection.get("glyph_id")
            or detection.get("detection_id")
            or f"{source_id}-glyph-{order_index:05d}"
        )
        notation_bbox = _normalize_bbox_object(detection.get("bbox"))
        glyph_candidates = glyph_candidates_by_id.get(glyph_id, [])
        component_candidates = component_candidates_by_id.get(glyph_id, [])
        if not glyph_candidates:
            raw_label = detection.get("label")
            raw_confidence = detection.get("confidence")
            glyph_candidates = [
                {
                    "glyph_id": glyph_id,
                    "rank": 1,
                    "label": raw_label if isinstance(raw_label, str) else "glyph",
                    "confidence": raw_confidence if isinstance(raw_confidence, (int, float)) else 0.0,
                    "source": detection.get("source_detector", "ocr-bundle"),
                }
            ]
        top_candidate = max(
            glyph_candidates,
            key=lambda item: float(item.get("confidence", 0.0)),
            default=None,
        )

        crop_ref = detection.get("crop_ref")
        crop_path = None
        if isinstance(crop_ref, str) and crop_ref.strip():
            candidate_path = Path(crop_ref)
            crop_path = (bundle_path / candidate_path).resolve() if not candidate_path.is_absolute() else candidate_path
            if not crop_path.exists():
                warnings.append(f"OCR crop file referenced by detection is missing: {crop_path}")

        glyphs.append(
            GlyphRecord(
                glyph_id=glyph_id,
                page_id=str(detection.get("page_id", "")),
                source_box_index=int(detection.get("source_box_index", order_index - 1)),
                box_type=str(detection.get("box_type", "Music")),
                order_index=int(detection.get("order_index", order_index)),
                text_bbox=None,
                notation_bbox=notation_bbox,
                text_content=top_candidate.get("label") if isinstance(top_candidate, dict) else None,
                raw_notation_payload={
                    "type": "OCR_CANDIDATES",
                    "char_guess": top_candidate.get("label") if isinstance(top_candidate, dict) else None,
                    "glyph_candidates": glyph_candidates,
                    "component_candidates": component_candidates,
                    "layout_guess": detection.get("layout_guess"),
                    "top_candidate_confidence": top_candidate.get("confidence") if isinstance(top_candidate, dict) else None,
                    "calibrated_confidence": detection.get("calibrated_confidence", detection.get("confidence")),
                    "provenance": detection.get("provenance"),
                },
                is_excluded_from_dataset=False,
                is_line_break=False,
                metadata={
                    "detection_confidence": detection.get("detection_confidence", detection.get("confidence")),
                    "crop_ref": str(crop_path) if crop_path is not None else None,
                    "model_version": raw_manifest.get("model_version", raw_manifest.get("detector_name")),
                    "decoder_version": raw_manifest.get("decoder_version"),
                    "needs_review_hint": detection.get("needs_review_hint"),
                    "ocr_label": detection.get("label"),
                    "layout_guess": detection.get("layout_guess"),
                    "score_breakdown": detection.get("score_breakdown"),
                },
            )
        )

    manifest = SourceManifest(
        source_id=source_id,
        source_type="ocr-bundle",
        source_file=str(manifest_path.resolve()),
        notation_type="Jianzipu",
        composer="",
        piece_title=str(raw_manifest.get("piece_title") or source_id),
        image_paths=image_paths,
        imported_at="",
        metadata={
            "bundle_id": raw_manifest.get("bundle_id"),
            "model_version": raw_manifest.get("model_version", raw_manifest.get("detector_name")),
            "decoder_version": raw_manifest.get("decoder_version"),
            "generated_at": raw_manifest.get("generated_at", raw_manifest.get("created_at")),
            "input_manifest": raw_manifest.get("input_manifest"),
        },
    )

    return OcrBundleImport(
        manifest=manifest,
        pages=pages,
        glyphs=glyphs,
        warnings=warnings,
    )

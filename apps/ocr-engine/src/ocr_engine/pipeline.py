"""OCR pipeline orchestration."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ocr_engine.detectors import DetectionSettings
from ocr_engine.detectors import HeuristicComponentDetector
from ocr_engine.io import collect_input_pages
from ocr_engine.io import collect_image_paths
from ocr_engine.io import read_json
from ocr_engine.io import write_bundle
from ocr_engine.models import OCRBundle
from ocr_engine.models import OCRBundleManifest
from ocr_engine.models import OCRComponentCandidate
from ocr_engine.models import OCRDetection
from ocr_engine.models import OCRGlyphCandidate
from ocr_engine.models import OCRPage
from ocr_engine.image import load_image
from ocr_engine.image import crop_grayscale
from ocr_engine.image import write_pgm
from ocr_engine.preprocess import preprocess_page


def run_baseline_detection(
    input_path: Path,
    output_root: Path,
    source_id: str | None = None,
    min_area: int = 64,
    model_name: str | None = None,
    expected_layout_path: Path | None = None,
    workers: int = 1,
) -> Path:
    """Run the phase 0/1 baseline detection flow and write an OCR bundle."""
    image_paths = collect_image_paths(input_path)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    bundle_id = f"ocr-{run_id}-{uuid4().hex[:8]}"
    bundle_dir = output_root / bundle_id

    detector_name = model_name or HeuristicComponentDetector.name
    settings = DetectionSettings(min_area=min_area)
    input_pages = collect_input_pages(input_path)
    expected_layout = read_json(expected_layout_path) if expected_layout_path is not None else {}
    expected_by_page = {
        str(page.get("page_id", "")): page
        for page in expected_layout.get("pages", [])
        if isinstance(page, dict)
    }

    pages: list[OCRPage] = []
    detections: list[OCRDetection] = []
    glyph_candidates: list[OCRGlyphCandidate] = []
    component_candidates: list[OCRComponentCandidate] = []
    validation_pages: list[dict[str, object]] = []

    page_jobs = [
        {
            "index": index,
            "input_page": input_page,
            "source_stub": source_id or input_path.stem,
            "settings": settings,
            "detector_name": detector_name,
            "expected_page": expected_by_page.get(
                str(input_page.get("page_id") or f"{source_id or input_path.stem}-page-{index:03d}"),
                {},
            ),
            "bundle_dir": str(bundle_dir),
        }
        for index, input_page in enumerate(input_pages, start=1)
    ]
    max_workers = max(1, min(workers, len(page_jobs)))
    if max_workers == 1:
        page_results = [_process_input_page(job) for job in page_jobs]
    else:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            page_results = list(executor.map(_process_input_page, page_jobs))

    for page_result in page_results:
        pages.append(page_result["page"])
        detections.extend(page_result["detections"])
        glyph_candidates.extend(page_result["glyph_candidates"])
        component_candidates.extend(page_result["component_candidates"])
        if page_result["validation"]:
            validation_pages.append(page_result["validation"])

    summary = {
        "bundle_id": bundle_id,
        "source_id": source_id or input_path.stem,
        "input_type": "manifest" if input_path.is_file() and input_path.suffix.lower() == ".json" else ("file" if input_path.is_file() else "directory"),
        "input_path": str(input_path.resolve()),
        "page_count": len(pages),
        "detection_count": len(detections),
        "glyph_candidate_count": len(glyph_candidates),
        "component_candidate_count": len(component_candidates),
        "box_type_counts": _count_by_box_type(detections),
        "detector_name": detector_name,
        "min_area": min_area,
    }
    validation = (
        {
            "expected_layout_path": str(expected_layout_path.resolve()) if expected_layout_path is not None else None,
            "summary": _build_validation_summary(validation_pages),
            "page_validations": validation_pages,
        }
        if validation_pages
        else {}
    )

    bundle = OCRBundle(
        manifest=OCRBundleManifest(
            bundle_id=bundle_id,
            source_id=source_id or input_path.stem,
            detector_name=detector_name,
            created_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
            input_paths=[str(path.resolve()) for path in image_paths],
            metadata={
                "min_area": min_area,
                "input_path": str(input_path.resolve()),
                "baseline": True,
            },
        ),
        pages=pages,
        detections=detections,
        glyph_candidates=glyph_candidates,
        component_candidates=component_candidates,
        summary=summary,
        validation=validation,
    )

    write_bundle(bundle_dir, bundle)
    write_bundle_logs(bundle_dir, bundle)
    return bundle_dir


def _process_input_page(job: dict[str, object]) -> dict[str, object]:
    index = int(job["index"])
    input_page = dict(job["input_page"])
    source_stub = str(job["source_stub"])
    settings = job["settings"]
    detector_name = str(job["detector_name"])
    expected_page = job["expected_page"] if isinstance(job["expected_page"], dict) else {}
    bundle_dir = Path(str(job["bundle_dir"]))

    image_path = Path(str(input_page["image_path"]))
    page_id = str(input_page.get("page_id") or f"{source_stub}-page-{index:03d}")
    loaded = load_image(image_path)
    preprocess = preprocess_page(loaded.grayscale)
    detector = HeuristicComponentDetector()

    page = OCRPage(
        page_id=page_id,
        image_path=str(image_path.resolve()),
        width=loaded.width,
        height=loaded.height,
        metadata={
            "page_index": int(input_page.get("page_index", index)),
            "input_metadata": input_page.get("metadata", {}),
            "threshold": preprocess.threshold,
            "preprocess": preprocess.metadata,
            "image_metadata": loaded.metadata,
        },
    )

    page_detections = detector.detect(page_id=page_id, mask=preprocess.foreground_mask, settings=settings)
    page_detections = _finalize_page_detections(
        detections=page_detections,
        page_index=int(input_page.get("page_index", index)),
        detector_name=detector_name,
        expected_layout_used=bool(expected_page),
    )
    _write_detection_crops(bundle_dir=bundle_dir, grayscale=loaded.grayscale, detections=page_detections)
    validation = (
        _build_page_validation(
            page_id=page_id,
            expected_boxes=expected_page.get("expected_glyph_boxes", []),
            detections=page_detections,
        )
        if expected_page
        else None
    )
    return {
        "page": page,
        "detections": page_detections,
        "glyph_candidates": _build_glyph_candidates(page_detections),
        "component_candidates": _build_component_candidates(page_detections),
        "validation": validation,
    }


def _count_by_box_type(detections: list[OCRDetection]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for detection in detections:
        counts[detection.box_type] = counts.get(detection.box_type, 0) + 1
    return counts


def _finalize_page_detections(
    *,
    detections: list[OCRDetection],
    page_index: int,
    detector_name: str,
    expected_layout_used: bool,
) -> list[OCRDetection]:
    ordered = sorted(detections, key=lambda item: (item.bbox[0][1], item.bbox[0][0], item.bbox[1][1], item.bbox[1][0]))
    for order_index, detection in enumerate(ordered, start=1):
        detection.glyph_id = detection.detection_id
        detection.order_index = order_index
        detection.layout_guess = _infer_layout_guess(detection)
        detection.calibrated_confidence = _calibrate_confidence(detection)
        detection.crop_ref = f"raw/crops/{detection.page_id}/{detection.detection_id}.pgm"
        detection.needs_review_hint = _infer_review_hint(detection)
        detection.provenance = {
            "stage": "baseline-detect",
            "detector": detector_name,
            "page_index": page_index,
            "expected_layout_used": expected_layout_used,
        }
    return ordered


def _write_detection_crops(
    *,
    bundle_dir: Path,
    grayscale: list[list[int]],
    detections: list[OCRDetection],
) -> None:
    for detection in detections:
        if not detection.crop_ref:
            continue
        crop = crop_grayscale(grayscale, detection.bbox)
        write_pgm(bundle_dir / detection.crop_ref, crop)


def write_bundle_logs(bundle_dir: Path, bundle: OCRBundle) -> None:
    from ocr_engine.io import write_json

    write_json(
        bundle_dir / "logs" / "run_log.json",
        {
            "bundle_id": bundle.manifest.bundle_id,
            "source_id": bundle.manifest.source_id,
            "detector_name": bundle.manifest.detector_name,
            "created_at": bundle.manifest.created_at,
            "page_count": len(bundle.pages),
            "detection_count": len(bundle.detections),
            "glyph_candidate_count": len(bundle.glyph_candidates),
            "component_candidate_count": len(bundle.component_candidates),
        },
    )


def _build_glyph_candidates(detections: list[OCRDetection]) -> list[OCRGlyphCandidate]:
    candidates: list[OCRGlyphCandidate] = []
    for detection in detections:
        width = detection.metadata.get("width")
        height = detection.metadata.get("height")
        aspect_ratio = float(width) / float(height) if isinstance(width, int) and isinstance(height, int) and height else 1.0
        base_label = "title" if detection.box_type == "Title" else "glyph_cluster"
        secondary_label = "unknown"
        if detection.box_type == "Music":
            if aspect_ratio < 0.7:
                secondary_label = "string_number_like"
            elif aspect_ratio > 1.35:
                secondary_label = "left_hand_like"
        candidates.append(
            OCRGlyphCandidate(
                glyph_id=detection.glyph_id or detection.detection_id,
                rank=1,
                label=base_label,
                confidence=round(detection.calibrated_confidence or detection.confidence, 4),
                metadata={
                    "source_detector": detection.source_detector,
                    "box_type": detection.box_type,
                    "layout_guess": detection.layout_guess,
                },
            )
        )
        candidates.append(
            OCRGlyphCandidate(
                glyph_id=detection.glyph_id or detection.detection_id,
                rank=2,
                label=secondary_label,
                confidence=max(0.05, round(detection.confidence * 0.55, 4)),
                metadata={
                    "source_detector": detection.source_detector,
                    "box_type": detection.box_type,
                    "layout_guess": detection.layout_guess,
                },
            )
        )
    return candidates


def _build_component_candidates(detections: list[OCRDetection]) -> list[OCRComponentCandidate]:
    candidates: list[OCRComponentCandidate] = []
    for detection in detections:
        if detection.box_type != "Music":
            continue
        (x1, y1), (x2, y2) = detection.bbox
        mid_x = x1 + (x2 - x1) // 2
        mid_y = y1 + (y2 - y1) // 2
        glyph_id = detection.glyph_id or detection.detection_id
        candidates.append(
            OCRComponentCandidate(
                glyph_id=glyph_id,
                slot="top_left",
                label="unknown_component",
                bbox=[[x1, y1], [mid_x, mid_y]],
                confidence=max(0.1, round(detection.confidence * 0.45, 4)),
                metadata={
                    "source_detector": detection.source_detector,
                    "layout_guess": detection.layout_guess,
                },
            )
        )
        candidates.append(
            OCRComponentCandidate(
                glyph_id=glyph_id,
                slot="top_right",
                label="unknown_component",
                bbox=[[mid_x, y1], [x2, mid_y]],
                confidence=max(0.1, round(detection.confidence * 0.4, 4)),
                metadata={
                    "source_detector": detection.source_detector,
                    "layout_guess": detection.layout_guess,
                },
            )
        )
        candidates.append(
            OCRComponentCandidate(
                glyph_id=glyph_id,
                slot="bottom_inner",
                label="unknown_component",
                bbox=[[x1, mid_y], [mid_x, y2]],
                confidence=max(0.1, round(detection.confidence * 0.35, 4)),
                metadata={
                    "source_detector": detection.source_detector,
                    "layout_guess": detection.layout_guess,
                },
            )
        )
        candidates.append(
            OCRComponentCandidate(
                glyph_id=glyph_id,
                slot="bottom_outer",
                label="unknown_component",
                bbox=[[mid_x, mid_y], [x2, y2]],
                confidence=max(0.1, round(detection.confidence * 0.3, 4)),
                metadata={
                    "source_detector": detection.source_detector,
                    "layout_guess": detection.layout_guess,
                },
            )
        )
    return candidates


def _build_page_validation(
    *,
    page_id: str,
    expected_boxes: object,
    detections: list[OCRDetection],
) -> dict[str, object]:
    expected = [item for item in expected_boxes if isinstance(item, dict)] if isinstance(expected_boxes, list) else []
    music_detections = [item for item in detections if item.box_type == "Music"]
    return {
        "page_id": page_id,
        "expected_glyph_box_count": len(expected),
        "detected_music_box_count": len(music_detections),
        "count_gap": len(music_detections) - len(expected),
        "detected_total_box_count": len(detections),
    }


def _build_validation_summary(page_validations: list[dict[str, object]]) -> dict[str, object]:
    total_expected = 0
    total_detected = 0
    pages_with_gap = 0
    for page in page_validations:
        expected = page.get("expected_glyph_box_count")
        detected = page.get("detected_music_box_count")
        gap = page.get("count_gap")
        if isinstance(expected, int):
            total_expected += expected
        if isinstance(detected, int):
            total_detected += detected
        if isinstance(gap, int) and gap != 0:
            pages_with_gap += 1
    return {
        "page_count": len(page_validations),
        "pages_with_count_gap": pages_with_gap,
        "total_expected_glyph_boxes": total_expected,
        "total_detected_music_boxes": total_detected,
        "total_count_gap": total_detected - total_expected,
    }


def _infer_layout_guess(detection: OCRDetection) -> str:
    width = detection.metadata.get("width")
    height = detection.metadata.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or height <= 0:
        return "single"
    aspect_ratio = width / float(height)
    if aspect_ratio >= 1.6:
        return "left_right"
    if aspect_ratio <= 0.75:
        return "top_bottom"
    return "single"


def _calibrate_confidence(detection: OCRDetection) -> float:
    confidence = detection.confidence
    if detection.box_type == "Music":
        confidence += 0.03
    if detection.box_type == "Title":
        confidence -= 0.04
    return round(max(0.01, min(0.99, confidence)), 4)


def _infer_review_hint(detection: OCRDetection) -> str:
    calibrated = detection.calibrated_confidence or detection.confidence
    if detection.box_type != "Music":
        return "non_music_region"
    if calibrated < 0.45:
        return "low_confidence_music_box"
    return "baseline_placeholder_candidates"

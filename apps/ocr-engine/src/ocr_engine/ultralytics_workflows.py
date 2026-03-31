"""Ultralytics training and inference workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import shutil
from typing import Any
from uuid import uuid4

from ocr_engine.io import collect_image_paths
from ocr_engine.io import collect_input_pages
from ocr_engine.io import read_json
from ocr_engine.io import read_ndjson
from ocr_engine.io import ensure_dir
from ocr_engine.io import write_bundle
from ocr_engine.io import write_json
from ocr_engine.io import write_ndjson
from ocr_engine.models import OCRBundle
from ocr_engine.models import OCRBundleManifest
from ocr_engine.models import OCRDetection
from ocr_engine.models import OCRPage
from ocr_engine.pipeline import _build_component_candidates
from ocr_engine.pipeline import _build_glyph_candidates
from ocr_engine.pipeline import _count_by_box_type
from ocr_engine.pipeline import _finalize_page_detections
from ocr_engine.pipeline import _write_detection_crops
from ocr_engine.pipeline import write_bundle_logs
from ocr_engine.image import load_image


def train_yolo_detection_model(
    *,
    dataset_path: Path,
    output_root: Path,
    model_name: str,
    pretrained: bool,
    amp: bool,
    epochs: int,
    imgsz: int,
    batch: int,
    device: str,
    workers: int,
    dry_run: bool,
) -> Path:
    """Launch or stage one Ultralytics detection training run."""
    run_id = f"train-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    run_dir = output_root / run_id
    ensure_dir(run_dir)

    data_yaml = dataset_path / "data.yaml" if dataset_path.is_dir() else dataset_path
    request = {
        "run_id": run_id,
        "task": "yolo-detect-train",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "dataset_path": str(dataset_path.resolve()),
        "data_yaml": str(data_yaml.resolve()),
        "model_name": model_name,
        "pretrained": pretrained,
        "amp": amp,
        "epochs": epochs,
        "imgsz": imgsz,
        "batch": batch,
        "device": device,
        "workers": workers,
        "dry_run": dry_run,
    }
    write_json(run_dir / "run_request.json", request)

    available, detail = _get_ultralytics_status()
    if dry_run or not available:
        write_json(
            run_dir / "run_status.json",
            {
                "state": "dry_run" if dry_run else "dependency_missing",
                "detail": detail,
                "next_action": "Install ultralytics and run this command again without --dry-run.",
            },
        )
        return run_dir

    from ultralytics import YOLO  # type: ignore

    model = YOLO(model_name)
    results = model.train(
        data=str(data_yaml.resolve()),
        pretrained=pretrained,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        workers=workers,
        amp=amp,
        project=str(output_root.resolve()),
        name=run_id,
        exist_ok=True,
        plots=False,
    )

    save_dir = Path(str(getattr(results, "save_dir", run_dir)))
    best_candidate = save_dir / "weights" / "best.pt"
    last_candidate = save_dir / "weights" / "last.pt"
    write_json(
        save_dir / "run_status.json",
        {
            "state": "completed",
            "detail": "Ultralytics training run finished.",
            "save_dir": str(save_dir.resolve()),
            "best_path": str(best_candidate.resolve()) if best_candidate.exists() else _safe_path(getattr(results, "best", None)),
            "last_path": str(last_candidate.resolve()) if last_candidate.exists() else _safe_path(getattr(results, "last", None)),
        },
    )
    return save_dir


def train_yolo_classification_model(
    *,
    dataset_path: Path,
    output_root: Path,
    model_name: str,
    pretrained: bool,
    amp: bool,
    epochs: int,
    imgsz: int,
    batch: int,
    device: str,
    workers: int,
    dry_run: bool,
) -> Path:
    """Launch or stage one Ultralytics classification training run."""
    run_id = f"train-cls-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    run_dir = output_root / run_id
    ensure_dir(run_dir)

    request = {
        "run_id": run_id,
        "task": "yolo-classify-train",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "dataset_path": str(dataset_path.resolve()),
        "model_name": model_name,
        "pretrained": pretrained,
        "amp": amp,
        "epochs": epochs,
        "imgsz": imgsz,
        "batch": batch,
        "device": device,
        "workers": workers,
        "dry_run": dry_run,
    }
    write_json(run_dir / "run_request.json", request)

    available, detail = _get_ultralytics_status()
    if dry_run or not available:
        write_json(
            run_dir / "run_status.json",
            {
                "state": "dry_run" if dry_run else "dependency_missing",
                "detail": detail,
                "next_action": "Install ultralytics and run this command again without --dry-run.",
            },
        )
        return run_dir

    from ultralytics import YOLO  # type: ignore

    model = YOLO(model_name)
    results = model.train(
        data=str(dataset_path.resolve()),
        pretrained=pretrained,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        workers=workers,
        amp=amp,
        project=str(output_root.resolve()),
        name=run_id,
        exist_ok=True,
        plots=False,
    )

    save_dir = Path(str(getattr(results, "save_dir", run_dir)))
    best_candidate = save_dir / "weights" / "best.pt"
    last_candidate = save_dir / "weights" / "last.pt"
    write_json(
        save_dir / "run_status.json",
        {
            "state": "completed",
            "detail": "Ultralytics classification training run finished.",
            "save_dir": str(save_dir.resolve()),
            "best_path": str(best_candidate.resolve()) if best_candidate.exists() else _safe_path(getattr(results, "best", None)),
            "last_path": str(last_candidate.resolve()) if last_candidate.exists() else _safe_path(getattr(results, "last", None)),
        },
    )
    return save_dir


def evaluate_yolo_classification_model(
    *,
    dataset_path: Path,
    output_root: Path,
    model_path: Path,
    split: str,
    dry_run: bool,
) -> Path:
    """Stage or run classification evaluation on one reviewed crop split."""
    run_id = f"eval-cls-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    run_dir = output_root / run_id
    ensure_dir(run_dir)

    split_dir = dataset_path / split
    image_rows = _collect_classification_rows(split_dir)
    request = {
        "run_id": run_id,
        "task": "yolo-classify-eval",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "dataset_path": str(dataset_path.resolve()),
        "split": split,
        "split_dir": str(split_dir.resolve()),
        "model_path": str(model_path.resolve()),
        "image_count": len(image_rows),
        "dry_run": dry_run,
    }
    write_json(run_dir / "run_request.json", request)

    available, detail = _get_ultralytics_status()
    if dry_run or not available:
        write_json(
            run_dir / "run_status.json",
            {
                "state": "dry_run" if dry_run else "dependency_missing",
                "detail": detail,
                "next_action": "Install ultralytics and run this command again without --dry-run.",
            },
        )
        return run_dir

    predictions = _predict_classification_rows(image_rows=image_rows, model_path=model_path)
    metrics = _build_classification_metrics(predictions)
    write_ndjson(run_dir / "predictions.ndjson", predictions)
    write_json(run_dir / "metrics.json", metrics)
    write_json(
        run_dir / "run_status.json",
        {
            "state": "completed",
            "detail": "Classification evaluation finished.",
            "metrics_path": str((run_dir / "metrics.json").resolve()),
            "prediction_count": len(predictions),
        },
    )
    return run_dir


def filter_ocr_bundle_with_classifier(
    *,
    bundle_path: Path,
    output_root: Path,
    model_path: Path,
    keep_label: str = "correct",
    min_confidence: float = 0.5,
    dry_run: bool,
) -> Path:
    """Stage or run classification-based OCR bundle filtering."""
    run_id = f"filter-cls-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    filtered_bundle_dir = output_root / run_id
    ensure_dir(filtered_bundle_dir)

    raw_dir = bundle_path / "raw"
    detections = read_ndjson(raw_dir / "detections.ndjson")
    request = {
        "run_id": run_id,
        "task": "yolo-classify-filter-bundle",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "source_bundle": str(bundle_path.resolve()),
        "model_path": str(model_path.resolve()),
        "keep_label": keep_label,
        "min_confidence": min_confidence,
        "detection_count": len(detections),
        "dry_run": dry_run,
    }

    available, detail = _get_ultralytics_status()
    if dry_run or not available:
        write_json(filtered_bundle_dir / "logs" / "filter_request.json", request)
        write_json(
            filtered_bundle_dir / "logs" / "filter_status.json",
            {
                "state": "dry_run" if dry_run else "dependency_missing",
                "detail": detail,
                "next_action": "Install ultralytics and run this command again without --dry-run.",
            },
        )
        return filtered_bundle_dir

    crop_rows = _collect_bundle_crop_rows(bundle_path=bundle_path)
    predictions = _predict_classification_rows(image_rows=crop_rows, model_path=model_path)
    predicted_by_detection_id = {
        str(row["detection_id"]): row
        for row in predictions
        if str(row.get("detection_id", "")).strip()
    }

    pages = read_ndjson(raw_dir / "pages.ndjson")
    glyph_candidates = read_ndjson(raw_dir / "glyph_candidates.ndjson")
    component_candidates = read_ndjson(raw_dir / "component_candidates.ndjson")
    manifest = read_json(bundle_path / "manifest.json")
    summary = read_json(bundle_path / "reports" / "summary.json")
    validation_path = bundle_path / "reports" / "validation.json"
    validation = read_json(validation_path) if validation_path.exists() else {}

    kept_detections = []
    kept_glyph_ids: set[str] = set()
    filtered_out = 0
    for detection in detections:
        detection_id = str(detection.get("detection_id", "")).strip()
        prediction = predicted_by_detection_id.get(detection_id)
        if prediction is None:
            kept_detections.append(detection)
            kept_glyph_ids.add(str(detection.get("glyph_id") or detection_id))
            continue
        predicted_label = str(prediction.get("predicted_label", "")).strip()
        predicted_confidence = prediction.get("predicted_confidence")
        if predicted_label == keep_label and isinstance(predicted_confidence, (int, float)) and float(predicted_confidence) >= min_confidence:
            kept_detections.append(detection)
            kept_glyph_ids.add(str(detection.get("glyph_id") or detection_id))
        else:
            filtered_out += 1

    kept_glyph_candidates = [
        row for row in glyph_candidates
        if str(row.get("glyph_id", "")).strip() in kept_glyph_ids
    ]
    kept_component_candidates = [
        row for row in component_candidates
        if str(row.get("glyph_id", "")).strip() in kept_glyph_ids
    ]

    if filtered_bundle_dir.exists():
        shutil.rmtree(filtered_bundle_dir)
    shutil.copytree(bundle_path, filtered_bundle_dir)
    write_json(filtered_bundle_dir / "logs" / "filter_request.json", request)

    manifest.setdefault("metadata", {})
    if isinstance(manifest["metadata"], dict):
        manifest["metadata"]["filter_model_path"] = str(model_path.resolve())
        manifest["metadata"]["filter_keep_label"] = keep_label
        manifest["metadata"]["filter_min_confidence"] = min_confidence
        manifest["metadata"]["source_bundle"] = str(bundle_path.resolve())
    summary = dict(summary)
    summary["filter_model_path"] = str(model_path.resolve())
    summary["pre_filter_detection_count"] = len(detections)
    summary["detection_count"] = len(kept_detections)
    summary["glyph_candidate_count"] = len(kept_glyph_candidates)
    summary["component_candidate_count"] = len(kept_component_candidates)
    summary["filtered_out_detection_count"] = filtered_out
    summary["filter_keep_label"] = keep_label
    summary["filter_min_confidence"] = min_confidence
    summary["box_type_counts"] = _count_by_box_type(_rows_to_detection_objects(kept_detections))

    write_json(filtered_bundle_dir / "manifest.json", manifest)
    write_ndjson(filtered_bundle_dir / "raw" / "detections.ndjson", kept_detections)
    write_ndjson(filtered_bundle_dir / "raw" / "glyph_candidates.ndjson", kept_glyph_candidates)
    write_ndjson(filtered_bundle_dir / "raw" / "component_candidates.ndjson", kept_component_candidates)
    write_ndjson(filtered_bundle_dir / "raw" / "classification_filter_predictions.ndjson", predictions)
    write_json(filtered_bundle_dir / "reports" / "summary.json", summary)
    if validation:
        write_json(filtered_bundle_dir / "reports" / "validation.json", validation)
    write_json(
        filtered_bundle_dir / "reports" / "classification_filter_report.json",
        {
            "source_bundle": str(bundle_path.resolve()),
            "model_path": str(model_path.resolve()),
            "keep_label": keep_label,
            "min_confidence": min_confidence,
            "input_detection_count": len(detections),
            "kept_detection_count": len(kept_detections),
            "filtered_out_detection_count": filtered_out,
            "prediction_count": len(predictions),
        },
    )
    write_json(
        filtered_bundle_dir / "logs" / "filter_status.json",
        {
            "state": "completed",
            "detail": "Classification filter bundle written.",
            "prediction_count": len(predictions),
            "kept_detection_count": len(kept_detections),
            "filtered_out_detection_count": filtered_out,
        },
    )
    return filtered_bundle_dir


def predict_yolo_detection_bundle(
    *,
    input_path: Path,
    output_root: Path,
    model_path: Path,
    source_id: str | None,
    conf: float,
    dry_run: bool,
) -> Path:
    """Run Ultralytics detection inference and write a standard OCR bundle."""
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    bundle_id = f"ocr-yolo-{run_id}-{uuid4().hex[:8]}"
    bundle_dir = output_root / bundle_id
    ensure_dir(bundle_dir)

    request = {
        "bundle_id": bundle_id,
        "task": "yolo-detect-predict",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "input_path": str(input_path.resolve()),
        "model_path": str(model_path.resolve()),
        "source_id": source_id,
        "conf": conf,
        "dry_run": dry_run,
    }
    write_json(bundle_dir / "logs" / "inference_request.json", request)

    available, detail = _get_ultralytics_status()
    if dry_run or not available:
        write_json(
            bundle_dir / "logs" / "inference_status.json",
            {
                "state": "dry_run" if dry_run else "dependency_missing",
                "detail": detail,
                "next_action": "Install ultralytics and run this command again without --dry-run.",
            },
        )
        return bundle_dir

    from ultralytics import YOLO  # type: ignore

    input_pages = collect_input_pages(input_path)
    image_paths = collect_image_paths(input_path)
    model = YOLO(str(model_path.resolve()))
    results = model.predict(
        source=[str(Path(str(page["image_path"])).resolve()) for page in input_pages],
        conf=conf,
        save=False,
        verbose=False,
    )

    pages: list[OCRPage] = []
    detections: list[OCRDetection] = []
    page_lookup = {
        str(Path(str(page["image_path"])).resolve()): page
        for page in input_pages
    }

    for result_index, result in enumerate(results, start=1):
        image_path = Path(str(getattr(result, "path", ""))).resolve()
        input_page = page_lookup.get(str(image_path), input_pages[result_index - 1] if result_index - 1 < len(input_pages) else {})
        page_id = str(input_page.get("page_id") or f"{source_id or input_path.stem}-page-{result_index:03d}")
        width, height = _resolve_page_dimensions(result, image_path)
        pages.append(
            OCRPage(
                page_id=page_id,
                image_path=str(image_path),
                width=width,
                height=height,
                metadata={
                    "page_index": int(input_page.get("page_index", result_index)),
                    "input_metadata": input_page.get("metadata", {}),
                    "inference_mode": "ultralytics-detect",
                },
            )
        )

        page_detections = _build_yolo_detections(
            result=result,
            page_id=page_id,
            conf=conf,
        )
        page_detections = _finalize_page_detections(
            detections=page_detections,
            page_index=int(input_page.get("page_index", result_index)),
            detector_name="ultralytics",
            expected_layout_used=False,
        )
        detections.extend(page_detections)

        try:
            loaded = load_image(image_path)
        except Exception:
            loaded = None
        if loaded is not None:
            _write_detection_crops(bundle_dir=bundle_dir, grayscale=loaded.grayscale, detections=page_detections)

    glyph_candidates = _build_glyph_candidates(detections)
    component_candidates = _build_component_candidates(detections)
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
        "detector_name": "ultralytics",
        "model_path": str(model_path.resolve()),
        "conf": conf,
    }
    bundle = OCRBundle(
        manifest=OCRBundleManifest(
            bundle_id=bundle_id,
            source_id=source_id or input_path.stem,
            detector_name="ultralytics",
            created_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
            input_paths=[str(path.resolve()) for path in image_paths],
            metadata={
                "input_path": str(input_path.resolve()),
                "model_path": str(model_path.resolve()),
                "conf": conf,
                "baseline": False,
            },
        ),
        pages=pages,
        detections=detections,
        glyph_candidates=glyph_candidates,
        component_candidates=component_candidates,
        summary=summary,
        validation={},
    )
    write_bundle(bundle_dir, bundle)
    write_bundle_logs(bundle_dir, bundle)
    write_json(
        bundle_dir / "logs" / "inference_status.json",
        {
            "state": "completed",
            "detail": "Ultralytics inference bundle written.",
            "model_path": str(model_path.resolve()),
        },
    )
    return bundle_dir


def _collect_classification_rows(split_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not split_dir.exists():
        return rows
    for label_dir in sorted(path for path in split_dir.iterdir() if path.is_dir()):
        label = label_dir.name
        for image_path in sorted(path for path in label_dir.rglob("*") if path.is_file()):
            rows.append(
                {
                    "image_path": image_path,
                    "ground_truth_label": label,
                    "image_id": image_path.stem,
                }
            )
    return rows


def _collect_bundle_crop_rows(*, bundle_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    detections = read_ndjson(bundle_path / "raw" / "detections.ndjson")
    for detection in detections:
        crop_ref = str(detection.get("crop_ref", "")).strip()
        detection_id = str(detection.get("detection_id", "")).strip()
        if not crop_ref or not detection_id:
            continue
        crop_path = bundle_path / crop_ref
        if not crop_path.exists():
            continue
        rows.append(
            {
                "image_path": crop_path,
                "detection_id": detection_id,
                "glyph_id": str(detection.get("glyph_id") or detection_id),
                "page_id": str(detection.get("page_id", "")),
            }
        )
    return rows


def _predict_classification_rows(
    *,
    image_rows: list[dict[str, object]],
    model_path: Path,
) -> list[dict[str, object]]:
    if not image_rows:
        return []

    from ultralytics import YOLO  # type: ignore

    model = YOLO(str(model_path.resolve()))
    results = model.predict(
        source=[str(Path(str(row["image_path"])).resolve()) for row in image_rows],
        save=False,
        verbose=False,
    )

    predictions: list[dict[str, object]] = []
    for row, result in zip(image_rows, results):
        probs = getattr(result, "probs", None)
        top1 = _scalar(getattr(probs, "top1", None))
        top1_conf = _scalar(getattr(probs, "top1conf", None))
        names = getattr(result, "names", {})
        predicted_label = _resolve_class_name(names, int(top1) if isinstance(top1, (int, float)) else 0)
        predictions.append(
            {
                "image_path": str(Path(str(row["image_path"])).resolve()),
                "image_id": row.get("image_id") or Path(str(row["image_path"])).stem,
                "ground_truth_label": row.get("ground_truth_label"),
                "predicted_label": predicted_label,
                "predicted_confidence": round(float(top1_conf), 6) if isinstance(top1_conf, (int, float)) else None,
                "detection_id": row.get("detection_id"),
                "glyph_id": row.get("glyph_id"),
                "page_id": row.get("page_id"),
            }
        )
    return predictions


def _scalar(value: object) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if hasattr(value, "item"):
        try:
            extracted = value.item()
            if isinstance(extracted, (int, float)):
                return extracted
        except Exception:
            return None
    return None


def _build_classification_metrics(predictions: list[dict[str, object]]) -> dict[str, object]:
    total = len(predictions)
    correct = 0
    confusion: dict[str, dict[str, int]] = {}
    for row in predictions:
        truth = str(row.get("ground_truth_label", "")).strip()
        pred = str(row.get("predicted_label", "")).strip()
        if truth and pred and truth == pred:
            correct += 1
        if truth not in confusion:
            confusion[truth] = {}
        confusion[truth][pred] = confusion[truth].get(pred, 0) + 1
    return {
        "prediction_count": total,
        "accuracy": round(correct / total, 6) if total else 0.0,
        "correct_count": correct,
        "incorrect_count": total - correct,
        "confusion": confusion,
    }


def _rows_to_detection_objects(rows: list[dict[str, Any]]) -> list[OCRDetection]:
    detections: list[OCRDetection] = []
    for row in rows:
        bbox = row.get("bbox")
        if not isinstance(bbox, list):
            continue
        detections.append(
            OCRDetection(
                detection_id=str(row.get("detection_id", "")),
                page_id=str(row.get("page_id", "")),
                box_type=str(row.get("box_type", "Music")),
                bbox=bbox,
                confidence=float(row.get("confidence", 0.0)) if isinstance(row.get("confidence"), (int, float)) else 0.0,
                label=str(row.get("label", "")),
                source_detector=str(row.get("source_detector", "filtered")),
            )
        )
    return detections


def _get_ultralytics_status() -> tuple[bool, str]:
    try:
        import ultralytics  # type: ignore

        return True, f"ultralytics {getattr(ultralytics, '__version__', 'unknown')}"
    except Exception as exc:
        return False, str(exc)


def _safe_path(value: object) -> str | None:
    if value is None:
        return None
    return str(Path(str(value)).resolve())


def _resolve_page_dimensions(result: object, image_path: Path) -> tuple[int, int]:
    orig_shape = getattr(result, "orig_shape", None)
    if isinstance(orig_shape, tuple) and len(orig_shape) == 2:
        height, width = orig_shape
        if isinstance(width, int) and isinstance(height, int):
            return width, height
    loaded = load_image(image_path)
    return loaded.width, loaded.height


def _build_yolo_detections(*, result: object, page_id: str, conf: float) -> list[OCRDetection]:
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return []

    xyxy_values = _tensor_to_list(getattr(boxes, "xyxy", []))
    conf_values = _tensor_to_list(getattr(boxes, "conf", []))
    cls_values = _tensor_to_list(getattr(boxes, "cls", []))
    names = getattr(result, "names", {})

    detections: list[OCRDetection] = []
    for index, coords in enumerate(xyxy_values, start=1):
        if not isinstance(coords, list) or len(coords) != 4:
            continue
        confidence = float(conf_values[index - 1]) if index - 1 < len(conf_values) else conf
        class_id = int(cls_values[index - 1]) if index - 1 < len(cls_values) else 0
        label = _resolve_class_name(names, class_id)
        box_type = _normalize_box_type(label)
        x1, y1, x2, y2 = [int(round(float(value))) for value in coords]
        detections.append(
            OCRDetection(
                detection_id=f"{page_id}-det-{index:04d}",
                page_id=page_id,
                box_type=box_type,
                bbox=[[x1, y1], [x2, y2]],
                confidence=round(confidence, 4),
                label=label,
                source_detector="ultralytics",
                score_breakdown={"model_confidence": round(confidence, 4)},
                metadata={
                    "class_id": class_id,
                    "width": max(0, x2 - x1 + 1),
                    "height": max(0, y2 - y1 + 1),
                },
            )
        )
    return detections


def _tensor_to_list(value: object) -> list[Any]:
    if hasattr(value, "tolist"):
        converted = value.tolist()
        return converted if isinstance(converted, list) else []
    return value if isinstance(value, list) else []


def _resolve_class_name(names: object, class_id: int) -> str:
    if isinstance(names, dict):
        value = names.get(class_id)
        if isinstance(value, str):
            return value
    if isinstance(names, list) and 0 <= class_id < len(names):
        value = names[class_id]
        if isinstance(value, str):
            return value
    return str(class_id)


def _normalize_box_type(label: str) -> str:
    normalized = label.strip().lower()
    if normalized in {"title", "header"}:
        return "Title"
    return "Music"

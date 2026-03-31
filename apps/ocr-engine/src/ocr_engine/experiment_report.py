"""Experiment reporting helpers for OCR training and filtering runs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ocr_engine.io import read_json, write_json


def build_experiment_report(*, output_dir: Path, roots: list[Path]) -> dict[str, object]:
    """Summarize OCR training/evaluation/filter runs across one or more roots."""
    train_runs: list[dict[str, object]] = []
    eval_runs: list[dict[str, object]] = []
    filter_runs: list[dict[str, object]] = []

    for root in roots:
        if not root.exists():
            continue
        for run_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            run_request_path = run_dir / "run_request.json"
            run_status_path = run_dir / "run_status.json"
            if not run_request_path.exists() or not run_status_path.exists():
                continue

            request = read_json(run_request_path)
            status = read_json(run_status_path)
            task = str(request.get("task", "")).strip()
            entry = {
                "run_dir": str(run_dir.resolve()),
                "run_id": request.get("run_id"),
                "task": task,
                "created_at": request.get("created_at"),
                "state": status.get("state"),
                "detail": status.get("detail"),
            }

            if task == "yolo-detect-train":
                entry.update(
                    {
                        "dataset_path": request.get("dataset_path"),
                        "model_name": request.get("model_name"),
                        "epochs": request.get("epochs"),
                        "batch": request.get("batch"),
                        "imgsz": request.get("imgsz"),
                        "best_path": status.get("best_path"),
                    }
                )
                train_runs.append(entry)
            elif task == "yolo-classify-train":
                entry.update(
                    {
                        "dataset_path": request.get("dataset_path"),
                        "model_name": request.get("model_name"),
                        "epochs": request.get("epochs"),
                        "batch": request.get("batch"),
                        "imgsz": request.get("imgsz"),
                        "best_path": status.get("best_path"),
                    }
                )
                train_runs.append(entry)
            elif task == "yolo-classify-eval":
                metrics_path = run_dir / "metrics.json"
                metrics = read_json(metrics_path) if metrics_path.exists() else {}
                entry.update(
                    {
                        "dataset_path": request.get("dataset_path"),
                        "split": request.get("split"),
                        "model_path": request.get("model_path"),
                        "image_count": request.get("image_count"),
                        "accuracy": metrics.get("accuracy"),
                        "correct_count": metrics.get("correct_count"),
                        "incorrect_count": metrics.get("incorrect_count"),
                    }
                )
                eval_runs.append(entry)
            elif task == "yolo-classify-filter-bundle":
                report_path = run_dir / "reports" / "classification_filter_report.json"
                report = read_json(report_path) if report_path.exists() else {}
                entry.update(
                    {
                        "source_bundle": request.get("source_bundle"),
                        "model_path": request.get("model_path"),
                        "keep_label": request.get("keep_label"),
                        "min_confidence": request.get("min_confidence"),
                        "input_detection_count": report.get("input_detection_count"),
                        "kept_detection_count": report.get("kept_detection_count"),
                        "filtered_out_detection_count": report.get("filtered_out_detection_count"),
                    }
                )
                filter_runs.append(entry)

    report = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "roots": [str(root.resolve()) for root in roots if root.exists()],
        "train_runs": train_runs,
        "evaluation_runs": eval_runs,
        "filter_runs": filter_runs,
        "summary": {
            "train_run_count": len(train_runs),
            "evaluation_run_count": len(eval_runs),
            "filter_run_count": len(filter_runs),
        },
    }
    write_json(output_dir / "experiment_report.json", report)
    return report

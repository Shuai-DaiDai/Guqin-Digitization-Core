"""Command line interface for the OCR engine."""

from __future__ import annotations

import argparse
from pathlib import Path

from ocr_engine.experiment_report import build_experiment_report
from ocr_engine.io import read_json
from ocr_engine.pipeline import run_baseline_detection
from ocr_engine.training_export import export_reviewed_crop_dataset
from ocr_engine.training_export import export_yolo_detection_dataset
from ocr_engine.ultralytics_workflows import evaluate_yolo_classification_model
from ocr_engine.ultralytics_workflows import filter_ocr_bundle_with_classifier
from ocr_engine.ultralytics_workflows import train_yolo_classification_model
from ocr_engine.ultralytics_workflows import predict_yolo_detection_bundle
from ocr_engine.ultralytics_workflows import train_yolo_detection_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ocr-engine",
        description="Baseline OCR engine for Guqin Digitization Core.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect = subparsers.add_parser(
        "detect",
        help="Run the baseline detector on one image or a directory of images.",
    )
    detect.add_argument("--input", required=True, type=Path, help="Input image file or directory.")
    detect.add_argument("--output", required=True, type=Path, help="Output directory for the OCR bundle.")
    detect.add_argument("--source-id", default=None, help="Optional source identifier for the run.")
    detect.add_argument("--min-area", type=int, default=64, help="Minimum connected-component area.")
    detect.add_argument("--workers", type=int, default=1, help="Worker process count for page-level baseline detection.")
    detect.add_argument(
        "--expected-layout",
        type=Path,
        default=None,
        help="Optional expected layout JSON used for simple regression checks.",
    )

    summarize = subparsers.add_parser(
        "summarize",
        help="Summarize one OCR bundle that was created by the detect command.",
    )
    summarize.add_argument("--bundle", required=True, type=Path, help="Path to an OCR bundle directory.")

    export_yolo = subparsers.add_parser(
        "export-yolo-detect",
        help="Export one dataset-tools bundle into a YOLO-style detection dataset.",
    )
    export_yolo.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one dataset-tools bundle directory.",
    )
    export_yolo.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output directory where the YOLO dataset will be written.",
    )
    export_yolo.add_argument(
        "--page-images-root",
        type=Path,
        default=None,
        help="Optional page-image root used when raw page paths still point to remote paths.",
    )
    export_yolo.add_argument(
        "--val-ratio",
        type=float,
        default=0.2,
        help="Validation split ratio between 0 and 1.",
    )
    export_yolo.add_argument(
        "--include-box-type",
        action="append",
        default=None,
        help="Restrict export to one or more box types, for example Music or Title. Repeatable.",
    )
    export_yolo.add_argument("--min-box-area", type=int, default=0, help="Skip boxes smaller than this area.")
    export_yolo.add_argument("--min-box-width", type=int, default=0, help="Skip boxes narrower than this width.")
    export_yolo.add_argument("--min-box-height", type=int, default=0, help="Skip boxes shorter than this height.")
    export_yolo.add_argument(
        "--min-detection-confidence",
        type=float,
        default=0.0,
        help="Skip boxes below this stored detection confidence.",
    )
    export_yolo.add_argument(
        "--min-candidate-confidence",
        type=float,
        default=0.0,
        help="Skip boxes whose top glyph candidate confidence is below this threshold.",
    )
    export_yolo.add_argument(
        "--min-primitive-count",
        type=int,
        default=0,
        help="Skip boxes formed from fewer primitive connected components.",
    )

    export_reviewed_crops = subparsers.add_parser(
        "export-reviewed-crops",
        help="Export reviewed OCR boxes as positive/negative crop data.",
    )
    export_reviewed_crops.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one dataset-tools bundle directory.",
    )
    export_reviewed_crops.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output directory where the reviewed crop dataset will be written.",
    )
    export_reviewed_crops.add_argument(
        "--page-images-root",
        type=Path,
        default=None,
        help="Optional page-image root used when raw page paths still point to remote paths.",
    )
    export_reviewed_crops.add_argument(
        "--val-ratio",
        type=float,
        default=0.2,
        help="Validation split ratio between 0 and 1.",
    )
    export_reviewed_crops.add_argument(
        "--crop-margin",
        type=int,
        default=8,
        help="Extra padding added around each reviewed box crop.",
    )

    train_yolo = subparsers.add_parser(
        "train-yolo-detect",
        help="Stage or launch one Ultralytics detection training run.",
    )
    train_yolo.add_argument("--dataset", required=True, type=Path, help="Path to one YOLO dataset directory or its data.yaml.")
    train_yolo.add_argument("--output", required=True, type=Path, help="Directory where training runs should be written.")
    train_yolo.add_argument("--model", default="yolo11n.pt", help="Base Ultralytics model name or path.")
    train_yolo.add_argument(
        "--pretrained",
        action="store_true",
        help="Allow Ultralytics to start from pretrained weights instead of training from scratch.",
    )
    train_yolo.add_argument(
        "--amp",
        action="store_true",
        help="Enable automatic mixed precision checks and training acceleration.",
    )
    train_yolo.add_argument("--epochs", type=int, default=100, help="Number of training epochs.")
    train_yolo.add_argument("--imgsz", type=int, default=1024, help="Training image size.")
    train_yolo.add_argument("--batch", type=int, default=8, help="Training batch size.")
    train_yolo.add_argument("--device", default="0", help="Training device string, for example 0 or cpu.")
    train_yolo.add_argument("--workers", type=int, default=8, help="Data loader worker count.")
    train_yolo.add_argument(
        "--dry-run",
        action="store_true",
        help="Only write the run request without launching training.",
    )

    train_yolo_cls = subparsers.add_parser(
        "train-yolo-classify",
        help="Stage or launch one Ultralytics classification training run for reviewed box crops.",
    )
    train_yolo_cls.add_argument("--dataset", required=True, type=Path, help="Path to one reviewed crop dataset directory.")
    train_yolo_cls.add_argument("--output", required=True, type=Path, help="Directory where training runs should be written.")
    train_yolo_cls.add_argument("--model", default="yolo11n-cls.pt", help="Base Ultralytics classification model name or path.")
    train_yolo_cls.add_argument(
        "--pretrained",
        action="store_true",
        help="Allow Ultralytics to start from pretrained weights instead of training from scratch.",
    )
    train_yolo_cls.add_argument(
        "--amp",
        action="store_true",
        help="Enable automatic mixed precision checks and training acceleration.",
    )
    train_yolo_cls.add_argument("--epochs", type=int, default=100, help="Number of training epochs.")
    train_yolo_cls.add_argument("--imgsz", type=int, default=224, help="Training image size.")
    train_yolo_cls.add_argument("--batch", type=int, default=64, help="Training batch size.")
    train_yolo_cls.add_argument("--device", default="0", help="Training device string, for example 0 or cpu.")
    train_yolo_cls.add_argument("--workers", type=int, default=8, help="Data loader worker count.")
    train_yolo_cls.add_argument(
        "--dry-run",
        action="store_true",
        help="Only write the run request without launching training.",
    )

    eval_yolo_cls = subparsers.add_parser(
        "evaluate-yolo-classify",
        help="Stage or run one reviewed-crop classification evaluation.",
    )
    eval_yolo_cls.add_argument("--dataset", required=True, type=Path, help="Path to one reviewed crop dataset directory.")
    eval_yolo_cls.add_argument("--output", required=True, type=Path, help="Directory where evaluation runs should be written.")
    eval_yolo_cls.add_argument("--model", required=True, type=Path, help="Path to one trained classification model weight file.")
    eval_yolo_cls.add_argument("--split", default="val", help="Dataset split directory to evaluate, usually val.")
    eval_yolo_cls.add_argument(
        "--dry-run",
        action="store_true",
        help="Only write the evaluation request without launching inference.",
    )

    filter_yolo_cls = subparsers.add_parser(
        "filter-yolo-bundle",
        help="Stage or run classification-based OCR bundle filtering.",
    )
    filter_yolo_cls.add_argument("--bundle", required=True, type=Path, help="Path to one OCR bundle directory.")
    filter_yolo_cls.add_argument("--output", required=True, type=Path, help="Directory where filtered OCR bundles should be written.")
    filter_yolo_cls.add_argument("--model", required=True, type=Path, help="Path to one trained classification model weight file.")
    filter_yolo_cls.add_argument("--keep-label", default="correct", help="Classification label that should be kept.")
    filter_yolo_cls.add_argument("--min-confidence", type=float, default=0.5, help="Minimum classification confidence required to keep one box.")
    filter_yolo_cls.add_argument(
        "--dry-run",
        action="store_true",
        help="Only write the filtering request without launching inference.",
    )

    experiment_report = subparsers.add_parser(
        "build-experiment-report",
        help="Summarize detection/classification experiment runs across one or more roots.",
    )
    experiment_report.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory where the experiment report should be written.",
    )
    experiment_report.add_argument(
        "--root",
        action="append",
        required=True,
        type=Path,
        help="Run root directory to scan. Repeatable.",
    )

    detect_yolo = subparsers.add_parser(
        "detect-yolo",
        help="Stage or run Ultralytics detection inference and write an OCR bundle.",
    )
    detect_yolo.add_argument("--input", required=True, type=Path, help="Input image file, directory, or input manifest JSON.")
    detect_yolo.add_argument("--model", required=True, type=Path, help="Path to one trained model weight file.")
    detect_yolo.add_argument("--output", required=True, type=Path, help="Output directory for OCR bundles.")
    detect_yolo.add_argument("--source-id", default=None, help="Optional source identifier for this inference run.")
    detect_yolo.add_argument("--conf", type=float, default=0.25, help="Confidence threshold passed to the detector.")
    detect_yolo.add_argument(
        "--dry-run",
        action="store_true",
        help="Only write the inference request without launching the model.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "detect":
        bundle_dir = run_baseline_detection(
            input_path=args.input,
            output_root=args.output,
            source_id=args.source_id,
            min_area=args.min_area,
            expected_layout_path=args.expected_layout,
            workers=args.workers,
        )
        print(f"Wrote OCR bundle to {bundle_dir}")
        return 0

    if args.command == "summarize":
        summary = read_json(args.bundle / "reports" / "summary.json")
        print(summary)
        return 0

    if args.command == "export-yolo-detect":
        include_box_types = tuple(args.include_box_type or ["Music", "Title"])
        dataset_dir = export_yolo_detection_dataset(
            bundle_path=args.bundle,
            output_root=args.output,
            page_images_root=args.page_images_root,
            val_ratio=args.val_ratio,
            include_box_types=include_box_types,
            min_box_area=args.min_box_area,
            min_box_width=args.min_box_width,
            min_box_height=args.min_box_height,
            min_detection_confidence=args.min_detection_confidence,
            min_candidate_confidence=args.min_candidate_confidence,
            min_primitive_count=args.min_primitive_count,
        )
        print(f"Wrote YOLO detection dataset to {dataset_dir}")
        return 0

    if args.command == "export-reviewed-crops":
        dataset_dir = export_reviewed_crop_dataset(
            bundle_path=args.bundle,
            output_root=args.output,
            page_images_root=args.page_images_root,
            val_ratio=args.val_ratio,
            crop_margin=args.crop_margin,
        )
        print(f"Wrote reviewed crop dataset to {dataset_dir}")
        return 0

    if args.command == "train-yolo-detect":
        run_dir = train_yolo_detection_model(
            dataset_path=args.dataset,
            output_root=args.output,
            model_name=args.model,
            pretrained=args.pretrained,
            amp=args.amp,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
            workers=args.workers,
            dry_run=args.dry_run,
        )
        print(f"Wrote training run metadata to {run_dir}")
        return 0

    if args.command == "train-yolo-classify":
        run_dir = train_yolo_classification_model(
            dataset_path=args.dataset,
            output_root=args.output,
            model_name=args.model,
            pretrained=args.pretrained,
            amp=args.amp,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
            workers=args.workers,
            dry_run=args.dry_run,
        )
        print(f"Wrote classification training run metadata to {run_dir}")
        return 0

    if args.command == "evaluate-yolo-classify":
        run_dir = evaluate_yolo_classification_model(
            dataset_path=args.dataset,
            output_root=args.output,
            model_path=args.model,
            split=args.split,
            dry_run=args.dry_run,
        )
        print(f"Wrote classification evaluation metadata to {run_dir}")
        return 0

    if args.command == "filter-yolo-bundle":
        bundle_dir = filter_ocr_bundle_with_classifier(
            bundle_path=args.bundle,
            output_root=args.output,
            model_path=args.model,
            keep_label=args.keep_label,
            min_confidence=args.min_confidence,
            dry_run=args.dry_run,
        )
        print(f"Wrote filtered OCR bundle metadata to {bundle_dir}")
        return 0

    if args.command == "build-experiment-report":
        report = build_experiment_report(
            output_dir=args.output,
            roots=args.root,
        )
        print(report["summary"])
        return 0

    if args.command == "detect-yolo":
        bundle_dir = predict_yolo_detection_bundle(
            input_path=args.input,
            output_root=args.output,
            model_path=args.model,
            source_id=args.source_id,
            conf=args.conf,
            dry_run=args.dry_run,
        )
        print(f"Wrote YOLO OCR bundle to {bundle_dir}")
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2

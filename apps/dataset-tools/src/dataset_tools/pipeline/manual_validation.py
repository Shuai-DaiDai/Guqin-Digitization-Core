"""Validation helpers for manually prepared metadata and annotation CSV files."""

from __future__ import annotations

from pathlib import Path

from dataset_tools.io_utils import read_csv, write_json


REQUIRED_METADATA_COLUMNS = ["source_id", "piece_title", "source_book", "image_file"]
REQUIRED_ANNOTATION_COLUMNS = ["image_file", "line_index", "glyph_index", "char_guess"]


def validate_manual_csv_package(
    metadata_path: Path,
    annotations_path: Path,
    images_root: Path | None = None,
) -> dict[str, object]:
    """Validate manually prepared metadata and annotation CSV files."""
    metadata_rows = read_csv(metadata_path)
    annotation_rows = read_csv(annotations_path)
    resolved_images_root = images_root if images_root is not None else metadata_path.parent

    errors: list[str] = []
    warnings: list[str] = []

    metadata_columns = metadata_rows[0].keys() if metadata_rows else []
    annotation_columns = annotation_rows[0].keys() if annotation_rows else []

    for column in REQUIRED_METADATA_COLUMNS:
        if column not in metadata_columns:
            errors.append(f"metadata.csv 缺少必填列: {column}")
    for column in REQUIRED_ANNOTATION_COLUMNS:
        if column not in annotation_columns:
            errors.append(f"annotations.csv 缺少必填列: {column}")

    image_files = set()
    for row_index, row in enumerate(metadata_rows, start=1):
        image_file = (row.get("image_file") or "").strip()
        if not image_file:
            errors.append(f"metadata.csv 第 {row_index} 行缺少 image_file")
            continue
        image_files.add(image_file)
        if not (resolved_images_root / image_file).exists():
            warnings.append(f"metadata.csv 第 {row_index} 行引用的图片不存在: {image_file}")

    seen_positions: set[tuple[str, str, str]] = set()
    for row_index, row in enumerate(annotation_rows, start=1):
        image_file = (row.get("image_file") or "").strip()
        if image_file not in image_files:
            errors.append(
                f"annotations.csv 第 {row_index} 行引用的 image_file 未在 metadata.csv 中出现: {image_file}"
            )
        line_index = (row.get("line_index") or "").strip()
        glyph_index = (row.get("glyph_index") or "").strip()
        position_key = (image_file, line_index, glyph_index)
        if position_key in seen_positions:
            warnings.append(
                f"annotations.csv 第 {row_index} 行与前文重复: image_file={image_file}, line_index={line_index}, glyph_index={glyph_index}"
            )
        seen_positions.add(position_key)
        if not (row.get("char_guess") or "").strip():
            warnings.append(f"annotations.csv 第 {row_index} 行缺少 char_guess")

    report = {
        "metadata_path": str(metadata_path),
        "annotations_path": str(annotations_path),
        "metadata_rows": len(metadata_rows),
        "annotation_rows": len(annotation_rows),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "is_valid": len(errors) == 0,
    }
    output_path = metadata_path.parent / "manual_csv_validation_report.json"
    write_json(output_path, report)
    print(f"Manual CSV validation {'passed' if report['is_valid'] else 'failed'}: {output_path}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"- {error}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    return report

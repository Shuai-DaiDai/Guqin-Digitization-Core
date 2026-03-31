"""Training dataset export helpers for OCR experiments."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from ocr_engine.io import copy_file
from ocr_engine.io import ensure_dir
from ocr_engine.io import IMAGE_EXTENSIONS
from ocr_engine.io import read_json
from ocr_engine.io import read_ndjson
from ocr_engine.io import write_json
from ocr_engine.image import crop_grayscale, load_image, write_png


YOLO_CLASS_MAP = {
    "Music": 0,
    "Title": 1,
}


def export_yolo_detection_dataset(
    *,
    bundle_path: Path,
    output_root: Path,
    page_images_root: Path | None = None,
    val_ratio: float = 0.2,
    include_box_types: tuple[str, ...] = ("Music", "Title"),
    min_box_area: int = 0,
    min_box_width: int = 0,
    min_box_height: int = 0,
    min_detection_confidence: float = 0.0,
    min_candidate_confidence: float = 0.0,
    min_primitive_count: int = 0,
) -> Path:
    """Export one dataset-tools bundle into a YOLO-style detection dataset."""
    raw_dir = bundle_path / "raw"
    manifest = read_json(raw_dir / "source_manifest.json")
    pages = read_ndjson(raw_dir / "pages.ndjson")
    glyphs = read_ndjson(raw_dir / "glyphs.ndjson")
    page_image_by_id = _resolve_page_images(page_images_root=page_images_root, pages=pages)

    export_id = f"{bundle_path.name}-yolo-detect"
    dataset_dir = output_root / export_id
    images_train = dataset_dir / "images" / "train"
    images_val = dataset_dir / "images" / "val"
    labels_train = dataset_dir / "labels" / "train"
    labels_val = dataset_dir / "labels" / "val"
    ensure_dir(images_train)
    ensure_dir(images_val)
    ensure_dir(labels_train)
    ensure_dir(labels_val)

    glyphs_by_page: dict[str, list[dict[str, object]]] = {}
    for glyph in glyphs:
        page_id = str(glyph.get("page_id", "")).strip()
        if not page_id:
            continue
        box_type = str(glyph.get("box_type", ""))
        if box_type not in YOLO_CLASS_MAP or box_type not in include_box_types:
            continue
        if glyph.get("is_excluded_from_dataset") is True:
            continue
        notation_bbox = glyph.get("notation_bbox")
        if not _is_valid_bbox(notation_bbox):
            continue
        if not _passes_export_filters(
            glyph=glyph,
            min_box_area=min_box_area,
            min_box_width=min_box_width,
            min_box_height=min_box_height,
            min_detection_confidence=min_detection_confidence,
            min_candidate_confidence=min_candidate_confidence,
            min_primitive_count=min_primitive_count,
        ):
            continue
        glyphs_by_page.setdefault(page_id, []).append(glyph)

    exported_pages = 0
    exported_boxes = 0
    missing_images: list[str] = []
    split_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    ready_pages: list[dict[str, object]] = []

    for page in pages:
        page_id = str(page.get("page_id", "")).strip()
        if not page_id:
            continue
        page_glyphs = glyphs_by_page.get(page_id, [])
        if not page_glyphs:
            continue

        page_id = str(page.get("page_id", "")).strip()
        image_path = page_image_by_id.get(page_id)
        if image_path is None:
            missing_images.append(str(page.get("image_path", "")))
            continue

        width = page.get("width")
        height = page.get("height")
        if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
            missing_images.append(f"{image_path} (missing width/height)")
            continue

        ready_pages.append(
            {
                "page": page,
                "page_id": page_id,
                "page_glyphs": page_glyphs,
                "image_path": image_path,
                "width": width,
                "height": height,
            }
        )

    split_by_page_id = _build_split_map(ready_pages=ready_pages, val_ratio=val_ratio)

    for item in ready_pages:
        page_id = str(item["page_id"])
        page_glyphs = list(item["page_glyphs"])
        image_path = Path(item["image_path"])
        width = int(item["width"])
        height = int(item["height"])
        split = split_by_page_id[page_id]
        split_counts[split] += 1
        image_destination_dir = images_val if split == "val" else images_train
        label_destination_dir = labels_val if split == "val" else labels_train

        image_destination = image_destination_dir / f"{page_id}{image_path.suffix.lower()}"
        label_destination = label_destination_dir / f"{page_id}.txt"
        copy_file(image_path, image_destination)

        label_lines: list[str] = []
        for glyph in sorted(page_glyphs, key=lambda item: int(item.get("order_index", 0))):
            box_type = str(glyph.get("box_type"))
            yolo_class_id = YOLO_CLASS_MAP[box_type]
            bbox = glyph.get("notation_bbox")
            if not isinstance(bbox, list):
                continue
            yolo_row = _bbox_to_yolo_row(bbox=bbox, width=width, height=height, class_id=yolo_class_id)
            if yolo_row is None:
                continue
            label_lines.append(yolo_row)
            exported_boxes += 1
            class_counts[box_type] += 1

        label_destination.write_text("\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8")
        exported_pages += 1

    _write_data_yaml(dataset_dir=dataset_dir)
    report = {
        "source_bundle": str(bundle_path.resolve()),
        "source_id": manifest.get("source_id"),
        "page_count": exported_pages,
        "box_count": exported_boxes,
        "split_counts": dict(split_counts),
        "class_counts": dict(class_counts),
        "missing_images": missing_images,
        "class_map": YOLO_CLASS_MAP,
        "val_ratio": val_ratio,
        "filters": {
            "include_box_types": list(include_box_types),
            "min_box_area": min_box_area,
            "min_box_width": min_box_width,
            "min_box_height": min_box_height,
            "min_detection_confidence": min_detection_confidence,
            "min_candidate_confidence": min_candidate_confidence,
            "min_primitive_count": min_primitive_count,
        },
    }
    write_json(dataset_dir / "export_report.json", report)
    return dataset_dir


def export_reviewed_crop_dataset(
    *,
    bundle_path: Path,
    output_root: Path,
    page_images_root: Path | None = None,
    val_ratio: float = 0.2,
    crop_margin: int = 8,
    include_box_types: tuple[str, ...] = ("Music",),
    include_verdicts: tuple[str, ...] = ("correct", "wrong"),
) -> Path:
    """Export reviewed OCR boxes as positive/negative crop data."""
    raw_dir = bundle_path / "raw"
    manifest = read_json(raw_dir / "source_manifest.json")
    pages = read_ndjson(raw_dir / "pages.ndjson")
    glyphs = read_ndjson(raw_dir / "glyphs.ndjson")

    page_image_by_id = _resolve_page_images(page_images_root=page_images_root, pages=pages)
    page_by_id = {
        str(page.get("page_id", "")): page
        for page in pages
        if str(page.get("page_id", "")).strip()
    }

    reviewed_rows: list[dict[str, object]] = []
    for glyph in glyphs:
        if str(glyph.get("box_type", "")) not in include_box_types:
            continue
        bbox = glyph.get("notation_bbox")
        if not _is_valid_bbox(bbox):
            continue
        metadata = glyph.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        verdict = str(metadata.get("review_verdict", "")).strip().lower()
        if verdict not in include_verdicts:
            continue
        page_id = str(glyph.get("page_id", "")).strip()
        page = page_by_id.get(page_id, {})
        page_image = page_image_by_id.get(page_id)
        if page_image is None:
            continue
        reviewed_rows.append(
            {
                "glyph_id": str(glyph.get("glyph_id", "")).strip(),
                "review_id": f"{glyph.get('glyph_id', '')}-candidate",
                "page_id": page_id,
                "page_index": page.get("page_index"),
                "page_image": page_image,
                "verdict": verdict,
                "bbox": bbox,
                "note": str(metadata.get("review_note", "")).strip(),
                "updated_at": str(metadata.get("review_updated_at", "")).strip(),
                "detection_confidence": metadata.get("detection_confidence"),
            }
        )

    dataset_dir = output_root / f"{bundle_path.name}-reviewed-crops"
    ready_pages: list[dict[str, object]] = []
    seen_page_ids: set[str] = set()
    for row in reviewed_rows:
        page_id = str(row["page_id"])
        if page_id in seen_page_ids:
            continue
        seen_page_ids.add(page_id)
        ready_pages.append(
            {
                "page_id": page_id,
                "image_path": Path(row["page_image"]),
            }
        )
    split_by_page_id = _build_split_map(ready_pages=ready_pages, val_ratio=val_ratio)

    image_cache: dict[Path, object] = {}
    split_counts: Counter[str] = Counter()
    verdict_counts: Counter[str] = Counter()
    missing_pages: list[str] = []
    exported_rows: list[dict[str, object]] = []

    for row in reviewed_rows:
        page_id = str(row["page_id"])
        page_image = Path(row["page_image"])
        if not page_image.exists():
            missing_pages.append(str(page_image))
            continue
        loaded = image_cache.get(page_image)
        if loaded is None:
            loaded = load_image(page_image)
            image_cache[page_image] = loaded
        split = split_by_page_id.get(page_id, "train")
        verdict = str(row["verdict"])
        glyph_id = str(row["glyph_id"])
        crop_bbox = _expand_bbox(
            bbox=row["bbox"],
            width=int(getattr(loaded, "width")),
            height=int(getattr(loaded, "height")),
            margin=crop_margin,
        )
        crop = crop_grayscale(getattr(loaded, "grayscale"), crop_bbox)
        crop_path = dataset_dir / split / verdict / f"{glyph_id}.png"
        write_png(crop_path, crop)
        split_counts.update([split])
        verdict_counts.update([verdict])
        exported_rows.append(
            {
                "glyph_id": glyph_id,
                "review_id": row["review_id"],
                "page_id": page_id,
                "page_index": row["page_index"] if isinstance(row["page_index"], int) else "",
                "verdict": verdict,
                "crop_path": str(crop_path.relative_to(dataset_dir)),
                "page_image": str(page_image),
                "bbox_x1": crop_bbox[0][0],
                "bbox_y1": crop_bbox[0][1],
                "bbox_x2": crop_bbox[1][0],
                "bbox_y2": crop_bbox[1][1],
                "note": row["note"],
                "updated_at": row["updated_at"],
                "detection_confidence": row["detection_confidence"] if row["detection_confidence"] is not None else "",
            }
        )

    write_json(
        dataset_dir / "export_report.json",
        {
            "source_bundle": str(bundle_path.resolve()),
            "source_id": manifest.get("source_id"),
            "reviewed_item_count": len(reviewed_rows),
            "exported_crop_count": len(exported_rows),
            "split_counts": dict(split_counts),
            "verdict_counts": dict(verdict_counts),
            "reviewed_page_count": len(split_by_page_id),
            "missing_pages": missing_pages,
            "crop_margin": crop_margin,
            "include_box_types": list(include_box_types),
            "include_verdicts": list(include_verdicts),
            "val_ratio": val_ratio,
        },
    )
    _write_reviewed_crop_manifest(dataset_dir=dataset_dir, rows=exported_rows)
    return dataset_dir


def _is_valid_bbox(raw_bbox: object) -> bool:
    return (
        isinstance(raw_bbox, list)
        and len(raw_bbox) == 2
        and all(isinstance(point, list) and len(point) == 2 for point in raw_bbox)
        and all(isinstance(value, int) for point in raw_bbox for value in point)
    )


def _resolve_page_images(*, page_images_root: Path | None, pages: list[dict[str, object]]) -> dict[str, Path]:
    by_id: dict[str, Path] = {}
    unresolved: list[str] = []
    for page in pages:
        page_id = str(page.get("page_id", "")).strip()
        if not page_id:
            continue
        raw_image_path = str(page.get("image_path", "")).strip()
        if raw_image_path:
            candidate = Path(raw_image_path)
            if candidate.exists():
                by_id[page_id] = candidate
                continue
        unresolved.append(page_id)

    if page_images_root is None or not unresolved:
        return by_id

    discovered: dict[str, Path] = {}
    for image_path in page_images_root.rglob("*"):
        if not image_path.is_file():
            continue
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        stem = image_path.stem
        if stem in unresolved and stem not in discovered:
            discovered[stem] = image_path

    for page_id in unresolved:
        candidate = discovered.get(page_id)
        if candidate is not None:
            by_id[page_id] = candidate
    return by_id


def _expand_bbox(*, bbox: list[list[int]], width: int, height: int, margin: int) -> list[list[int]]:
    (x1, y1), (x2, y2) = bbox
    return [
        [max(0, x1 - margin), max(0, y1 - margin)],
        [min(width - 1, x2 + margin), min(height - 1, y2 + margin)],
    ]


def _write_reviewed_crop_manifest(*, dataset_dir: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "glyph_id,review_id,page_id,page_index,verdict,crop_path,page_image,bbox_x1,bbox_y1,bbox_x2,bbox_y2,note,updated_at,detection_confidence"
    ]
    for row in rows:
        values = [
            str(row["glyph_id"]),
            str(row["review_id"]),
            str(row["page_id"]),
            str(row["page_index"]),
            str(row["verdict"]),
            str(row["crop_path"]),
            str(row["page_image"]),
            str(row["bbox_x1"]),
            str(row["bbox_y1"]),
            str(row["bbox_x2"]),
            str(row["bbox_y2"]),
            str(row["note"]).replace("\n", " ").replace(",", " "),
            str(row["updated_at"]),
            str(row["detection_confidence"]),
        ]
        lines.append(",".join(values))
    ensure_dir(dataset_dir)
    (dataset_dir / "manifest.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _bbox_to_yolo_row(*, bbox: list[list[int]], width: int, height: int, class_id: int) -> str | None:
    (x1, y1), (x2, y2) = bbox
    box_width = x2 - x1 + 1
    box_height = y2 - y1 + 1
    if box_width <= 0 or box_height <= 0 or width <= 0 or height <= 0:
        return None
    center_x = x1 + box_width / 2.0
    center_y = y1 + box_height / 2.0
    return (
        f"{class_id} "
        f"{center_x / width:.6f} "
        f"{center_y / height:.6f} "
        f"{box_width / width:.6f} "
        f"{box_height / height:.6f}"
    )


def _passes_export_filters(
    *,
    glyph: dict[str, object],
    min_box_area: int,
    min_box_width: int,
    min_box_height: int,
    min_detection_confidence: float,
    min_candidate_confidence: float,
    min_primitive_count: int,
) -> bool:
    notation_bbox = glyph.get("notation_bbox")
    if not isinstance(notation_bbox, list) or len(notation_bbox) != 2:
        return False
    (x1, y1), (x2, y2) = notation_bbox
    box_width = x2 - x1 + 1
    box_height = y2 - y1 + 1
    box_area = box_width * box_height
    if box_area < min_box_area or box_width < min_box_width or box_height < min_box_height:
        return False

    metadata = glyph.get("metadata")
    if isinstance(metadata, dict):
        detection_confidence = metadata.get("detection_confidence")
        primitive_count = metadata.get("primitive_count")
        if isinstance(detection_confidence, (int, float)) and float(detection_confidence) < min_detection_confidence:
            return False
        if isinstance(primitive_count, int) and primitive_count < min_primitive_count:
            return False

    raw_notation_payload = glyph.get("raw_notation_payload")
    if isinstance(raw_notation_payload, dict):
        top_candidate_confidence = raw_notation_payload.get("top_candidate_confidence")
        if isinstance(top_candidate_confidence, (int, float)) and float(top_candidate_confidence) < min_candidate_confidence:
            return False

    return True


def _assign_split(*, page_id: str, val_ratio: float) -> str:
    stable_value = sum(ord(char) for char in page_id)
    return f"{stable_value:08d}-{page_id}"


def _build_split_map(*, ready_pages: list[dict[str, object]], val_ratio: float) -> dict[str, str]:
    page_ids = [str(item["page_id"]) for item in ready_pages]
    if not page_ids:
        return {}
    if val_ratio <= 0 or len(page_ids) == 1:
        return {page_id: "train" for page_id in page_ids}

    ordered_page_ids = [item.split("-", 1)[1] for item in sorted(_assign_split(page_id=page_id, val_ratio=val_ratio) for page_id in page_ids)]
    val_count = max(1, int(round(len(ordered_page_ids) * val_ratio)))
    val_count = min(len(ordered_page_ids) - 1, val_count)
    val_page_ids = set(ordered_page_ids[-val_count:])
    return {
        page_id: ("val" if page_id in val_page_ids else "train")
        for page_id in page_ids
    }


def _write_data_yaml(dataset_dir: Path) -> None:
    payload = "\n".join(
        [
            f"path: {dataset_dir.resolve()}",
            "train: images/train",
            "val: images/val",
            "names:",
            "  0: Music",
            "  1: Title",
            "",
        ]
    )
    (dataset_dir / "data.yaml").write_text(payload, encoding="utf-8")

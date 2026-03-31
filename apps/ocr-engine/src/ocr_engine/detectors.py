"""Baseline detectors for Guqin OCR."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable

from ocr_engine.models import OCRDetection


@dataclass(slots=True)
class DetectionSettings:
    """Heuristic detector settings."""

    min_area: int = 64
    min_width: int = 4
    min_height: int = 4
    max_components: int = 512
    merge_x_gap: int = 12
    merge_y_gap: int = 12
    min_cluster_area: int = 144


@dataclass(slots=True)
class PrimitiveComponent:
    """One primitive connected component before glyph clustering."""

    bbox: list[list[int]]
    area: int
    width: int
    height: int


class BaseGlyphDetector:
    """Abstract detector interface used by the OCR pipeline."""

    name = "base"

    def detect(
        self,
        page_id: str,
        mask: list[list[bool]],
        settings: DetectionSettings,
    ) -> list[OCRDetection]:
        raise NotImplementedError


class HeuristicComponentDetector(BaseGlyphDetector):
    """Cluster nearby connected components into coarse glyph boxes."""

    name = "heuristic-glyph-clusters"

    def detect(
        self,
        page_id: str,
        mask: list[list[bool]],
        settings: DetectionSettings,
    ) -> list[OCRDetection]:
        if not mask or not mask[0]:
            return []

        height = len(mask)
        width = len(mask[0])
        visited = [[False for _ in range(width)] for _ in range(height)]
        primitives: list[PrimitiveComponent] = []

        def neighbors(y: int, x: int) -> Iterable[tuple[int, int]]:
            if y > 0:
                yield y - 1, x
            if y + 1 < height:
                yield y + 1, x
            if x > 0:
                yield y, x - 1
            if x + 1 < width:
                yield y, x + 1

        for start_y in range(height):
            for start_x in range(width):
                if not mask[start_y][start_x] or visited[start_y][start_x]:
                    continue

                stack = [(start_y, start_x)]
                visited[start_y][start_x] = True
                min_y = max_y = start_y
                min_x = max_x = start_x
                area = 0

                while stack:
                    y, x = stack.pop()
                    area += 1
                    if y < min_y:
                        min_y = y
                    if y > max_y:
                        max_y = y
                    if x < min_x:
                        min_x = x
                    if x > max_x:
                        max_x = x

                    for next_y, next_x in neighbors(y, x):
                        if mask[next_y][next_x] and not visited[next_y][next_x]:
                            visited[next_y][next_x] = True
                            stack.append((next_y, next_x))

                box_width = max_x - min_x + 1
                box_height = max_y - min_y + 1
                if area < settings.min_area or box_width < settings.min_width or box_height < settings.min_height:
                    continue

                # Ignore page-frame style detections that swallow almost the entire image.
                if box_width > width * 0.9 and box_height > height * 0.9:
                    continue

                primitives.append(
                    PrimitiveComponent(
                        bbox=[[min_x, min_y], [max_x, max_y]],
                        area=area,
                        width=box_width,
                        height=box_height,
                    )
                )

                if len(primitives) >= settings.max_components:
                    break
            if len(primitives) >= settings.max_components:
                break

        if not primitives:
            return []

        merged_components = _cluster_primitives(
            primitives=primitives,
            settings=settings,
        )
        detections: list[OCRDetection] = []
        for detection_index, merged in enumerate(merged_components, start=1):
            (min_x, min_y), (max_x, max_y) = merged["bbox"]
            box_width = max_x - min_x + 1
            box_height = max_y - min_y + 1
            box_area = box_width * box_height
            primitive_area = int(merged["primitive_area"])
            primitive_count = int(merged["primitive_count"])
            fill_ratio = primitive_area / float(box_area + 1)
            if primitive_area < settings.min_cluster_area:
                continue
            if box_width > width * 0.9 and box_height > height * 0.9:
                continue

            confidence = min(
                0.99,
                0.38
                + min(0.24, fill_ratio * 0.22)
                + min(0.22, primitive_count * 0.018)
                + min(0.08, primitive_area / float(width * height + 1) * 20.0),
            )
            box_type = "Music"
            label = "glyph"
            if box_width > width * 0.5 and box_height < height * 0.18:
                box_type = "Title"
                label = "title"
                confidence = max(confidence, 0.62)

            detections.append(
                OCRDetection(
                    detection_id=f"{page_id}-det-{detection_index:04d}",
                    page_id=page_id,
                    box_type=box_type,
                    bbox=[[min_x, min_y], [max_x, max_y]],
                    confidence=round(confidence, 4),
                    label=label,
                    source_detector=self.name,
                    score_breakdown={
                        "area_ratio": round(primitive_area / float(width * height + 1), 4),
                        "fill_ratio": round(fill_ratio, 4),
                    },
                    metadata={
                        "pixel_area": primitive_area,
                        "width": box_width,
                        "height": box_height,
                        "primitive_count": primitive_count,
                        "box_area": box_area,
                    },
                )
            )

        return detections


def _cluster_primitives(
    *,
    primitives: list[PrimitiveComponent],
    settings: DetectionSettings,
) -> list[dict[str, object]]:
    if not primitives:
        return []

    widths = [component.width for component in primitives]
    heights = [component.height for component in primitives]
    dynamic_x_gap = max(settings.merge_x_gap, int(round(median(widths) * 0.75)))
    dynamic_y_gap = max(settings.merge_y_gap, int(round(median(heights) * 0.75)))

    groups: list[dict[str, object]] = []
    for primitive in sorted(primitives, key=lambda item: (item.bbox[0][1], item.bbox[0][0])):
        primitive_bbox = primitive.bbox
        attached_to_group = False
        for group in groups:
            if _should_merge(
                bbox_a=group["bbox"],
                bbox_b=primitive_bbox,
                max_gap_x=dynamic_x_gap,
                max_gap_y=dynamic_y_gap,
            ):
                group["bbox"] = _union_bbox(group["bbox"], primitive_bbox)
                group["primitive_area"] += primitive.area
                group["primitive_count"] += 1
                attached_to_group = True
                break
        if not attached_to_group:
            groups.append(
                {
                    "bbox": primitive_bbox,
                    "primitive_area": primitive.area,
                    "primitive_count": 1,
                }
            )

    return _merge_touching_groups(
        groups=groups,
        max_gap_x=dynamic_x_gap,
        max_gap_y=dynamic_y_gap,
    )


def _merge_touching_groups(
    *,
    groups: list[dict[str, object]],
    max_gap_x: int,
    max_gap_y: int,
) -> list[dict[str, object]]:
    changed = True
    merged = list(groups)
    while changed:
        changed = False
        next_groups: list[dict[str, object]] = []
        while merged:
            current = merged.pop(0)
            current_bbox = current["bbox"]
            current_area = int(current["primitive_area"])
            current_count = int(current["primitive_count"])
            keep_searching = True
            while keep_searching:
                keep_searching = False
                remaining: list[dict[str, object]] = []
                for candidate in merged:
                    if _should_merge(
                        bbox_a=current_bbox,
                        bbox_b=candidate["bbox"],
                        max_gap_x=max_gap_x,
                        max_gap_y=max_gap_y,
                    ):
                        current_bbox = _union_bbox(current_bbox, candidate["bbox"])
                        current_area += int(candidate["primitive_area"])
                        current_count += int(candidate["primitive_count"])
                        keep_searching = True
                        changed = True
                    else:
                        remaining.append(candidate)
                merged = remaining
            next_groups.append(
                {
                    "bbox": current_bbox,
                    "primitive_area": current_area,
                    "primitive_count": current_count,
                }
            )
        merged = next_groups
    return merged


def _should_merge(
    *,
    bbox_a: list[list[int]],
    bbox_b: list[list[int]],
    max_gap_x: int,
    max_gap_y: int,
) -> bool:
    (ax1, ay1), (ax2, ay2) = bbox_a
    (bx1, by1), (bx2, by2) = bbox_b
    horizontal_gap = max(0, max(ax1, bx1) - min(ax2, bx2) - 1)
    vertical_gap = max(0, max(ay1, by1) - min(ay2, by2) - 1)
    return horizontal_gap <= max_gap_x and vertical_gap <= max_gap_y


def _union_bbox(bbox_a: list[list[int]], bbox_b: list[list[int]]) -> list[list[int]]:
    (ax1, ay1), (ax2, ay2) = bbox_a
    (bx1, by1), (bx2, by2) = bbox_b
    return [
        [min(ax1, bx1), min(ay1, by1)],
        [max(ax2, bx2), max(ay2, by2)],
    ]


class UltralyticsGlyphDetector(BaseGlyphDetector):
    """Optional adapter for a trained Ultralytics detector."""

    name = "ultralytics"

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path
        self._model = None
        try:
            from ultralytics import YOLO  # type: ignore

            self._model = YOLO(model_path) if model_path else None
        except Exception:
            self._model = None

    def detect(
        self,
        page_id: str,
        mask: list[list[bool]],
        settings: DetectionSettings,
    ) -> list[OCRDetection]:
        if self._model is None:
            return HeuristicComponentDetector().detect(page_id=page_id, mask=mask, settings=settings)
        return []

"""Page preprocessing helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PreprocessResult:
    """Normalized image and lightweight metadata for detection."""

    grayscale: list[list[int]]
    foreground_mask: list[list[bool]]
    threshold: int
    metadata: dict[str, object]


def preprocess_page(grayscale: list[list[int]]) -> PreprocessResult:
    """Convert an input page into a grayscale array and a simple foreground mask."""
    flat_pixels = [pixel for row in grayscale for pixel in row]
    if flat_pixels:
        mean_value = sum(flat_pixels) / float(len(flat_pixels))
        variance = sum((pixel - mean_value) ** 2 for pixel in flat_pixels) / float(len(flat_pixels))
        std_value = variance ** 0.5
    else:
        mean_value = 255.0
        std_value = 0.0
    threshold = int(max(32, min(245, mean_value - std_value * 0.35)))
    foreground_mask = [[pixel < threshold for pixel in row] for row in grayscale]
    return PreprocessResult(
        grayscale=grayscale,
        foreground_mask=foreground_mask,
        threshold=threshold,
        metadata={
            "mean": mean_value,
            "std": std_value,
            "mode": "L",
        },
    )

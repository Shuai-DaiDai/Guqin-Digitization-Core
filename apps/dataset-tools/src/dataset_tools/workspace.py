"""Workspace layout helpers."""

from __future__ import annotations

from pathlib import Path

from dataset_tools.io_utils import ensure_dir


def create_bundle_layout(destination: Path) -> dict[str, Path]:
    """Create the standard directory layout for one imported workspace bundle."""
    layout = {
        "raw": destination / "raw",
        "derived": destination / "derived",
        "reports": destination / "reports",
        "logs": destination / "logs",
    }
    for path in layout.values():
        ensure_dir(path)
    ensure_dir(layout["derived"] / "jianzi_code_candidates")
    ensure_dir(layout["derived"] / "normalized_notes")
    ensure_dir(layout["derived"] / "jianzi_code_drafts")
    ensure_dir(layout["derived"] / "review_queue")
    return layout

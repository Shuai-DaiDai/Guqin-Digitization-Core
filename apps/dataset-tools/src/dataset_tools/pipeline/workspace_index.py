"""Workspace-level bundle indexing."""

from __future__ import annotations

from pathlib import Path

from dataset_tools.io_utils import read_json, write_csv, write_json


def build_workspace_index(workspace_root: Path) -> dict[str, object]:
    """Scan one workspace root and build a summary index of all bundles."""
    bundle_rows: list[dict[str, object]] = []

    for bundle_path in sorted(path for path in workspace_root.iterdir() if path.is_dir()):
        raw_manifest = bundle_path / "raw" / "source_manifest.json"
        summary_path = bundle_path / "reports" / "summary.json"
        quality_path = bundle_path / "reports" / "quality_report.json"
        review_path = bundle_path / "derived" / "review_queue" / "review_report.json"

        if not raw_manifest.exists():
            continue

        manifest = read_json(raw_manifest)
        summary = read_json(summary_path) if summary_path.exists() else {}
        quality = read_json(quality_path) if quality_path.exists() else {}
        review = read_json(review_path) if review_path.exists() else {}

        bundle_rows.append(
            {
                "bundle_id": bundle_path.name,
                "source_id": manifest.get("source_id", ""),
                "piece_title": manifest.get("piece_title", ""),
                "source_type": manifest.get("source_type", ""),
                "pages": summary.get("pages", 0),
                "music_boxes": summary.get("music_boxes", 0),
                "missing_images": quality.get("pages_missing_images", 0),
                "review_items": review.get("review_item_count", 0),
                "draft_events": quality.get("draft_events", 0),
            }
        )

    report = {
        "workspace_root": str(workspace_root),
        "bundle_count": len(bundle_rows),
        "total_review_items": sum(int(row.get("review_items", 0) or 0) for row in bundle_rows),
        "total_music_boxes": sum(int(row.get("music_boxes", 0) or 0) for row in bundle_rows),
        "bundles": bundle_rows,
    }

    write_json(workspace_root / "workspace_index.json", report)
    write_csv(
        workspace_root / "workspace_index.csv",
        fieldnames=[
            "bundle_id",
            "source_id",
            "piece_title",
            "source_type",
            "pages",
            "music_boxes",
            "missing_images",
            "review_items",
            "draft_events",
        ],
        rows=bundle_rows,
    )
    print(f"Wrote workspace index to {workspace_root / 'workspace_index.json'}")
    return report

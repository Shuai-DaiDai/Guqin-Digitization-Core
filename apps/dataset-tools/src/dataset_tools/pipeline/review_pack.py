"""Prepare a human-friendly review handoff package."""

from __future__ import annotations

from pathlib import Path

from dataset_tools.io_utils import read_json, write_json


def prepare_review_pack(bundle_path: Path) -> dict[str, object]:
    """Assemble a compact handoff package for human review."""
    raw_dir = bundle_path / "raw"
    derived_dir = bundle_path / "derived"
    reports_dir = bundle_path / "reports"
    handoff_dir = bundle_path / "handoff" / "review_pack"

    manifest = read_json(raw_dir / "source_manifest.json")
    summary = read_json(reports_dir / "summary.json")
    quality = read_json(reports_dir / "quality_report.json")
    review_report = read_json(derived_dir / "review_queue" / "review_report.json")
    document_report = read_json(derived_dir / "jianzi_code_drafts" / "document_draft_report.json")
    batches_summary_path = derived_dir / "review_queue" / "batches" / "batches_summary.json"
    batches_summary = read_json(batches_summary_path) if batches_summary_path.exists() else None

    handoff = {
        "source_id": manifest.get("source_id"),
        "piece_title": manifest.get("piece_title"),
        "source_type": manifest.get("source_type"),
        "source_file": manifest.get("source_file"),
        "quick_status": {
            "pages": summary.get("pages", 0),
            "music_boxes": summary.get("music_boxes", 0),
            "review_items": review_report.get("review_item_count", 0),
            "missing_images": quality.get("pages_missing_images", 0),
            "draft_events": quality.get("draft_events", 0),
        },
        "artifacts": {
            "summary_json": "reports/summary.json",
            "quality_report_json": "reports/quality_report.json",
            "review_queue_csv": "derived/review_queue/items.csv",
            "review_queue_ndjson": "derived/review_queue/items.ndjson",
            "review_batches_summary_json": "derived/review_queue/batches/batches_summary.json" if batches_summary else None,
            "document_draft_json": "derived/jianzi_code_drafts/document_draft.json",
        },
        "notes": [
            "先处理 review_queue/items.csv 中的 high 优先级条目。",
            "document_draft.json 是整曲草稿，不代表已经完成音高层补全。",
            "如需回填，请优先补徽位、分位、左右手技法，再补 acoustic 层。",
        ],
        "document_draft_report": document_report,
        "review_batches_summary": batches_summary,
    }

    markdown = "\n".join(
        [
            f"# Review Pack: {manifest.get('piece_title') or manifest.get('source_id')}",
            "",
            "## Quick Status",
            f"- Pages: {summary.get('pages', 0)}",
            f"- Music boxes: {summary.get('music_boxes', 0)}",
            f"- Review items: {review_report.get('review_item_count', 0)}",
            f"- Missing images: {quality.get('pages_missing_images', 0)}",
            f"- Draft events: {quality.get('draft_events', 0)}",
            "",
            "## Files",
            "- `reports/summary.json`",
            "- `reports/quality_report.json`",
            "- `derived/review_queue/items.csv`",
            "- `derived/review_queue/items.ndjson`",
            "- `derived/review_queue/batches/batches_summary.json`（如果已生成批次）",
            "- `derived/jianzi_code_drafts/document_draft.json`",
            "",
            "## Notes",
            "- 先处理 review_queue/items.csv 中的 high 优先级条目。",
            "- document_draft.json 是整曲草稿，不代表已经完成音高层补全。",
            "- 如需回填，请优先补徽位、分位、左右手技法，再补 acoustic 层。",
            "",
        ]
    )

    write_json(handoff_dir / "review_pack.json", handoff)
    (handoff_dir / "README.md").parent.mkdir(parents=True, exist_ok=True)
    (handoff_dir / "README.md").write_text(markdown, encoding="utf-8")
    print(f"Wrote review handoff pack to {handoff_dir}")
    return {
        "source_id": manifest.get("source_id"),
        "handoff_dir": str(handoff_dir),
        "review_item_count": review_report.get("review_item_count", 0),
    }

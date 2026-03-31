"""Document draft assembly from event drafts."""

from __future__ import annotations

from pathlib import Path

from dataset_tools.io_utils import read_json, read_ndjson, write_json


DEFAULT_TUNING = [
    "C2",
    "D2",
    "F2",
    "G2",
    "A2",
    "C3",
    "D3",
]


def assemble_document_draft(bundle_path: Path) -> dict[str, object]:
    """Assemble a score-level Jianzi-Code document draft from event drafts."""
    raw_dir = bundle_path / "raw"
    derived_dir = bundle_path / "derived"
    draft_dir = derived_dir / "jianzi_code_drafts"

    manifest = read_json(raw_dir / "source_manifest.json")
    drafts = read_ndjson(draft_dir / "event_drafts.ndjson")

    events = [draft.get("event_draft", {}) for draft in drafts if isinstance(draft.get("event_draft"), dict)]
    document = {
        "schema_version": "jianzi-document-v1",
        "piece": {
            "title": manifest.get("piece_title") or manifest.get("source_id") or "未命名曲目",
            "notation_systems": ["jianzipu"],
            "tuning": {
                "label": "待补定弦",
                "strings": DEFAULT_TUNING,
            },
            "source": {
                "edition": manifest.get("source_type", "unknown"),
                "reference_repository": manifest.get("source_file"),
            },
        },
        "sections": [
            {
                "id": "section-01",
                "label": "自动生成草稿",
                "measures": [
                    {
                        "index": 1,
                        "events": events,
                    }
                ],
            }
        ],
    }

    report = {
        "source_id": manifest.get("source_id"),
        "event_count": len(events),
        "document_has_placeholder_tuning": True,
        "document_has_acoustic_gaps": True,
    }

    write_json(draft_dir / "document_draft.json", document)
    write_json(draft_dir / "document_draft_report.json", report)
    print(f"Wrote Jianzi-Code document draft to {draft_dir / 'document_draft.json'}")
    return report

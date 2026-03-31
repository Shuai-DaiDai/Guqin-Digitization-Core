"""Apply online review decisions back into one dataset bundle."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

from dataset_tools.io_utils import read_ndjson, write_csv, write_json, write_ndjson


def _slugify(value: str) -> str:
    chars: list[str] = []
    last_was_dash = False
    for char in value.strip().lower():
        if char.isalnum():
            chars.append(char)
            last_was_dash = False
        elif not last_was_dash:
            chars.append("-")
            last_was_dash = True
    return "".join(chars).strip("-") or "review-site"


def _load_online_decisions(db_path: Path, site_id: str) -> list[dict[str, object]]:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            select site_id, review_id, verdict, note, updated_at
            from decisions
            where site_id = ?
            order by review_id
            """,
            (site_id,),
        ).fetchall()
    finally:
        connection.close()

    return [
        {
            "site_id": str(row["site_id"]),
            "review_id": str(row["review_id"]),
            "verdict": str(row["verdict"]),
            "note": str(row["note"] or ""),
            "updated_at": str(row["updated_at"]),
        }
        for row in rows
    ]


def _load_online_decisions_json(json_path: Path, site_id: str) -> list[dict[str, object]]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload_site = str(((payload or {}).get("site") or {}).get("siteId") or "").strip()
    if payload_site and payload_site != site_id:
        raise ValueError(f"Exported site id {payload_site!r} does not match requested site id {site_id!r}")

    decisions = ((payload or {}).get("decisions") or {})
    if not isinstance(decisions, dict):
        raise ValueError("Exported review JSON has invalid decisions payload")

    rows: list[dict[str, object]] = []
    for review_id, decision in decisions.items():
        if not isinstance(decision, dict):
            continue
        rows.append(
            {
                "site_id": site_id,
                "review_id": str(review_id).strip(),
                "verdict": str(decision.get("verdict", "")).strip(),
                "note": str(decision.get("note", "") or ""),
                "updated_at": str(decision.get("updatedAt", "")).strip(),
            }
        )
    rows.sort(key=lambda item: str(item["review_id"]))
    return rows


def _apply_online_review_rows(
    *,
    bundle_path: Path,
    site_id: str,
    decisions: list[dict[str, object]],
    source_label: str,
    source_ref: str,
) -> dict[str, object]:
    raw_dir = bundle_path / "raw"
    derived_dir = bundle_path / "derived"
    review_dir = derived_dir / "online_review" / _slugify(site_id)

    glyphs = read_ndjson(raw_dir / "glyphs.ndjson")
    pages = read_ndjson(raw_dir / "pages.ndjson")
    decisions_by_review_id = {
        str(row["review_id"]).strip(): row
        for row in decisions
        if str(row["review_id"]).strip()
    }

    page_index_by_id = {
        str(page.get("page_id", "")): page.get("page_index")
        for page in pages
        if str(page.get("page_id", "")).strip()
    }

    applied_rows: list[dict[str, object]] = []
    applied_review_ids: set[str] = set()
    verdict_counts: Counter[str] = Counter()

    for glyph in glyphs:
        glyph_id = str(glyph.get("glyph_id", "")).strip()
        if not glyph_id:
            continue
        review_id = f"{glyph_id}-candidate"
        decision = decisions_by_review_id.get(review_id)
        if decision is None:
            continue

        applied_review_ids.add(review_id)
        verdict = str(decision["verdict"]).strip().lower()
        note = str(decision["note"]).strip()
        updated_at = str(decision["updated_at"]).strip()
        page_id = str(glyph.get("page_id", "")).strip()
        page_index = page_index_by_id.get(page_id)
        bbox = glyph.get("notation_bbox")

        metadata = glyph.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        metadata["review_verdict"] = verdict
        metadata["review_note"] = note
        metadata["review_updated_at"] = updated_at
        metadata["review_site_id"] = site_id
        metadata["review_source"] = source_label
        metadata["human_review"] = {
            "verdict": verdict,
            "note": note,
            "updated_at": updated_at,
            "site_id": site_id,
            "source": source_label,
        }
        glyph["metadata"] = metadata

        if verdict == "wrong":
            glyph["is_excluded_from_dataset"] = True
        elif verdict == "correct":
            glyph["is_excluded_from_dataset"] = False

        applied_rows.append(
            {
                "review_id": review_id,
                "glyph_id": glyph_id,
                "page_id": page_id,
                "page_index": page_index if isinstance(page_index, int) else "",
                "verdict": verdict,
                "note": note,
                "updated_at": updated_at,
                "box_type": glyph.get("box_type", ""),
                "is_excluded_from_dataset": bool(glyph.get("is_excluded_from_dataset") is True),
                "bbox": bbox if isinstance(bbox, list) else None,
            }
        )
        verdict_counts.update([verdict])

    unresolved_review_ids = sorted(set(decisions_by_review_id) - applied_review_ids)
    write_ndjson(raw_dir / "glyphs.ndjson", glyphs)
    write_ndjson(review_dir / "decisions.ndjson", applied_rows)
    write_csv(
        review_dir / "decisions.csv",
        fieldnames=[
            "review_id",
            "glyph_id",
            "page_id",
            "page_index",
            "verdict",
            "note",
            "updated_at",
            "box_type",
            "is_excluded_from_dataset",
        ],
        rows=applied_rows,
    )

    report = {
        "source": source_label,
        "source_ref": source_ref,
        "site_id": site_id,
        "decision_count": len(decisions),
        "applied_count": len(applied_rows),
        "verdict_counts": dict(verdict_counts),
        "reviewed_page_count": len({row["page_id"] for row in applied_rows if row["page_id"]}),
        "excluded_glyph_count": sum(1 for row in applied_rows if row["verdict"] == "wrong"),
        "trusted_glyph_count": sum(1 for row in applied_rows if row["verdict"] == "correct"),
        "unresolved_review_id_count": len(unresolved_review_ids),
        "unresolved_review_ids": unresolved_review_ids[:50],
    }
    write_json(review_dir / "apply_report.json", report)
    return report


def apply_online_review_db(
    *,
    bundle_path: Path,
    db_path: Path,
    site_id: str,
) -> dict[str, object]:
    """Apply review decisions stored in one online SQLite database."""
    decisions = _load_online_decisions(db_path=db_path, site_id=site_id)
    report = _apply_online_review_rows(
        bundle_path=bundle_path,
        site_id=site_id,
        decisions=decisions,
        source_label="online_sqlite",
        source_ref=str(db_path),
    )
    print(f"Applied {report['applied_count']} online review decision(s) from {db_path}")
    return report


def apply_online_review_json(
    *,
    bundle_path: Path,
    json_path: Path,
    site_id: str,
) -> dict[str, object]:
    """Apply review decisions stored in one exported JSON payload."""
    decisions = _load_online_decisions_json(json_path=json_path, site_id=site_id)
    report = _apply_online_review_rows(
        bundle_path=bundle_path,
        site_id=site_id,
        decisions=decisions,
        source_label="online_export_json",
        source_ref=str(json_path),
    )
    print(f"Applied {report['applied_count']} online review decision(s) from {json_path}")
    return report

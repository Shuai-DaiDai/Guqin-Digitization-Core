"""Projection pipeline steps."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from dataset_tools.io_utils import read_json, read_ndjson, write_json, write_ndjson
from dataset_tools.projection import project_candidate


def summarize_bundle(bundle_path: Path) -> dict[str, object]:
    """Build a lightweight report for one workspace bundle."""
    raw_dir = bundle_path / "raw"
    reports_dir = bundle_path / "reports"

    manifest = read_json(raw_dir / "source_manifest.json")
    pages = read_ndjson(raw_dir / "pages.ndjson")
    glyphs = read_ndjson(raw_dir / "glyphs.ndjson")

    box_type_counts = dict(Counter(str(glyph.get("box_type", "Unknown")) for glyph in glyphs))
    notation_kind_counts = dict(
        Counter(
            str(raw_payload.get("type", "Unknown"))
            for glyph in glyphs
            for raw_payload in [glyph.get("raw_notation_payload")]
            if isinstance(raw_payload, dict)
        )
    )
    missing_image_pages = sum(
        1
        for page in pages
        if isinstance(page.get("metadata"), dict)
        and (
            page["metadata"].get("missing_on_disk") is True
            or page["metadata"].get("missing_image_reference") is True
        )
    )
    summary = {
        "source_id": manifest.get("source_id"),
        "source_type": manifest.get("source_type"),
        "notation_type": manifest.get("notation_type"),
        "pages": len(pages),
        "glyphs": len(glyphs),
        "box_type_counts": box_type_counts,
        "notation_kind_counts": notation_kind_counts,
        "music_boxes": sum(1 for glyph in glyphs if glyph.get("box_type") == "Music"),
        "missing_image_pages": missing_image_pages,
    }
    write_json(reports_dir / "summary.json", summary)
    print(f"Wrote summary report to {reports_dir / 'summary.json'}")
    return summary


def project_jianzi_code_candidates(bundle_path: Path) -> dict[str, object]:
    """Project imported glyphs into partial Jianzi-Code candidates."""
    raw_dir = bundle_path / "raw"
    derived_dir = bundle_path / "derived" / "jianzi_code_candidates"

    manifest = read_json(raw_dir / "source_manifest.json")
    glyphs = read_ndjson(raw_dir / "glyphs.ndjson")

    candidates = []
    for glyph in glyphs:
        candidate = project_candidate(glyph, source_id=str(manifest.get("source_id", "")))
        if candidate is not None:
            candidates.append(candidate.to_dict())

    write_ndjson(derived_dir / "candidates.ndjson", candidates)
    candidate_notation_kind_counts = dict(
        Counter(str(candidate.get("provenance", {}).get("notation_kind", "Unknown")) for candidate in candidates)
    )
    report = {
        "source_id": manifest.get("source_id"),
        "candidate_count": len(candidates),
        "music_box_count": sum(1 for glyph in glyphs if glyph.get("box_type") == "Music"),
        "candidate_notation_kind_counts": candidate_notation_kind_counts,
    }
    write_json(derived_dir / "projection_report.json", report)
    print(f"Wrote {len(candidates)} Jianzi-Code candidate(s) to {derived_dir / 'candidates.ndjson'}")
    return report

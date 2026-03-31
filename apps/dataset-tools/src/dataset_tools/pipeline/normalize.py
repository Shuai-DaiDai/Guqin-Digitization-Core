"""Normalization and quality audit steps."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from dataset_tools.io_utils import read_json, read_ndjson, write_json, write_ndjson
from dataset_tools.models.normalized_note import NormalizedNoteRecord


def _build_review_reasons(candidate: dict[str, object]) -> list[str]:
    partial_event = candidate.get("partial_event")
    if not isinstance(partial_event, dict):
        return ["missing_partial_event"]

    visual = partial_event.get("visual")
    physical_guess = partial_event.get("physical_guess")
    review_reasons: list[str] = []

    if not isinstance(visual, dict) or not str(visual.get("char_text", "")).strip():
        review_reasons.append("missing_visual_char_text")

    if not isinstance(physical_guess, dict):
        review_reasons.append("missing_physical_guess")
        return review_reasons

    if physical_guess.get("string") is None:
        review_reasons.append("missing_string_number")

    if str(physical_guess.get("note_type_guess", "unknown")) in {"unknown", ""}:
        review_reasons.append("unknown_note_type")

    return review_reasons


def normalize_bundle(bundle_path: Path) -> dict[str, object]:
    """Normalize projected candidates into a stable intermediate note layer."""
    raw_dir = bundle_path / "raw"
    derived_dir = bundle_path / "derived"
    normalized_dir = derived_dir / "normalized_notes"

    manifest = read_json(raw_dir / "source_manifest.json")
    candidates = read_ndjson(derived_dir / "jianzi_code_candidates" / "candidates.ndjson")

    normalized_notes: list[dict[str, object]] = []
    review_reason_counts: Counter[str] = Counter()

    for candidate in candidates:
        partial_event = candidate.get("partial_event", {})
        visual = partial_event.get("visual", {}) if isinstance(partial_event, dict) else {}
        physical_guess = (
            partial_event.get("physical_guess", {}) if isinstance(partial_event, dict) else {}
        )
        provenance = candidate.get("provenance", {})
        review_reasons = _build_review_reasons(candidate)
        review_reason_counts.update(review_reasons)

        note = NormalizedNoteRecord(
            note_id=str(candidate.get("candidate_id", "")),
            source_id=str(manifest.get("source_id", "")),
            glyph_id=str(candidate.get("glyph_id", "")),
            page_id=str(provenance.get("page_id", "")),
            notation_kind=str(provenance.get("notation_kind")) if provenance.get("notation_kind") is not None else None,
            visual_char_text=str(visual.get("char_text", "")),
            string_number=physical_guess.get("string") if isinstance(physical_guess.get("string"), int) else None,
            note_type_guess=str(physical_guess.get("note_type_guess", "unknown")),
            left_hand_symbols=[
                str(item) for item in physical_guess.get("left_hand_symbols", [])
            ]
            if isinstance(physical_guess, dict)
            and isinstance(physical_guess.get("left_hand_symbols"), list)
            else [],
            candidate_confidence=str(candidate.get("confidence", "low")),
            needs_review=bool(review_reasons),
            review_reasons=review_reasons,
            metadata={
                "candidate_status": candidate.get("candidate_status"),
            },
        )
        normalized_notes.append(note.to_dict())

    write_ndjson(normalized_dir / "notes.ndjson", normalized_notes)
    report = {
        "source_id": manifest.get("source_id"),
        "normalized_note_count": len(normalized_notes),
        "needs_review_count": sum(1 for note in normalized_notes if note["needs_review"]),
        "review_reason_counts": dict(review_reason_counts),
    }
    write_json(normalized_dir / "normalization_report.json", report)
    print(f"Wrote {len(normalized_notes)} normalized note(s) to {normalized_dir / 'notes.ndjson'}")
    return report


def audit_bundle_quality(bundle_path: Path) -> dict[str, object]:
    """Generate a simple quality report for one workspace bundle."""
    raw_dir = bundle_path / "raw"
    derived_dir = bundle_path / "derived"
    reports_dir = bundle_path / "reports"

    pages = read_ndjson(raw_dir / "pages.ndjson")
    glyphs = read_ndjson(raw_dir / "glyphs.ndjson")
    candidates = read_ndjson(derived_dir / "jianzi_code_candidates" / "candidates.ndjson")
    normalized_notes = read_ndjson(derived_dir / "normalized_notes" / "notes.ndjson")
    drafts = read_ndjson(derived_dir / "jianzi_code_drafts" / "event_drafts.ndjson")
    review_items = read_ndjson(derived_dir / "review_queue" / "items.ndjson")
    document_report = read_json(derived_dir / "jianzi_code_drafts" / "document_draft_report.json") if (derived_dir / "jianzi_code_drafts" / "document_draft_report.json").exists() else {}

    music_glyph_ids = {
        str(glyph.get("glyph_id", ""))
        for glyph in glyphs
        if glyph.get("box_type") == "Music"
    }
    candidate_glyph_ids = {str(candidate.get("glyph_id", "")) for candidate in candidates}

    report = {
        "pages_missing_images": sum(
            1
            for page in pages
            if isinstance(page.get("metadata"), dict)
            and (
                page["metadata"].get("missing_on_disk") is True
                or page["metadata"].get("missing_image_reference") is True
            )
        ),
        "excluded_glyphs": sum(1 for glyph in glyphs if glyph.get("is_excluded_from_dataset") is True),
        "line_break_glyphs": sum(1 for glyph in glyphs if glyph.get("is_line_break") is True),
        "music_glyphs_without_candidates": len(music_glyph_ids - candidate_glyph_ids),
        "normalized_notes_needing_review": sum(
            1 for note in normalized_notes if note.get("needs_review") is True
        ),
        "draft_events": len(drafts),
        "draft_events_with_schema_gaps": sum(
            1 for draft in drafts if isinstance(draft.get("schema_gaps"), list) and draft.get("schema_gaps")
        ),
        "review_queue_items": len(review_items),
        "document_draft_events": document_report.get("event_count", 0),
        "raw_music_glyphs": len(music_glyph_ids),
        "projected_candidates": len(candidates),
        "normalized_notes": len(normalized_notes),
    }
    write_json(reports_dir / "quality_report.json", report)
    print(f"Wrote quality report to {reports_dir / 'quality_report.json'}")
    return report


def process_bundle(bundle_path: Path) -> dict[str, object]:
    """Run the derived-data steps in the required order for one bundle."""
    from dataset_tools.pipeline.document import assemble_document_draft
    from dataset_tools.pipeline.enrich import enrich_bundle
    from dataset_tools.pipeline.project import project_jianzi_code_candidates, summarize_bundle
    from dataset_tools.pipeline.review_batches import slice_review_queue
    from dataset_tools.pipeline.review import build_review_queue
    from dataset_tools.pipeline.review_pack import prepare_review_pack

    summary = summarize_bundle(bundle_path=bundle_path)
    projection = project_jianzi_code_candidates(bundle_path=bundle_path)
    normalization = normalize_bundle(bundle_path=bundle_path)
    enrichment = enrich_bundle(bundle_path=bundle_path)
    document = assemble_document_draft(bundle_path=bundle_path)
    review_queue = build_review_queue(bundle_path=bundle_path)
    review_batches = slice_review_queue(bundle_path=bundle_path)
    quality = audit_bundle_quality(bundle_path=bundle_path)
    review_pack = prepare_review_pack(bundle_path=bundle_path)
    return {
        "summary": summary,
        "projection": projection,
        "normalization": normalization,
        "enrichment": enrichment,
        "document": document,
        "review_queue": review_queue,
        "review_batches": review_batches,
        "quality": quality,
        "review_pack": review_pack,
    }

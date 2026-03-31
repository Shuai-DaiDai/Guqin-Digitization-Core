"""Ingest pipeline steps."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from dataset_tools.adapters.gui_tools import load_gui_tools_bundle
from dataset_tools.adapters.kuiscima import load_kuiscima_bundle
from dataset_tools.adapters.manual_csv import load_manual_csv_bundle
from dataset_tools.adapters.ocr_bundle import load_ocr_bundle
from dataset_tools.io_utils import ensure_dir, write_json, write_ndjson
from dataset_tools.models.import_log import ImportLog
from dataset_tools.workspace import create_bundle_layout


def _write_import_bundle(
    *,
    importer_name: str,
    input_path: Path,
    output_root: Path,
    manifest,
    pages,
    glyphs,
    warnings: list[str],
) -> Path:
    imported_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    manifest.imported_at = imported_at

    import_id = f"{importer_name}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    destination = output_root / import_id
    ensure_dir(destination)
    layout = create_bundle_layout(destination)

    write_json(layout["raw"] / "source_manifest.json", manifest.to_dict())
    write_ndjson(layout["raw"] / "pages.ndjson", [page.to_dict() for page in pages])
    write_ndjson(layout["raw"] / "glyphs.ndjson", [glyph.to_dict() for glyph in glyphs])

    box_type_counts = dict(Counter(glyph.box_type for glyph in glyphs))
    summary = {
        "source_id": manifest.source_id,
        "pages": len(pages),
        "glyphs": len(glyphs),
        "box_type_counts": box_type_counts,
    }
    import_log = ImportLog(
        import_id=import_id,
        importer=importer_name,
        input_path=str(input_path.resolve()),
        output_path=str(destination.resolve()),
        imported_at=imported_at,
        summary=summary,
        warnings=warnings,
    )
    write_json(layout["logs"] / "import_log.json", import_log.to_dict())

    print(f"Imported {importer_name} project into {destination}")
    print(f"Pages: {summary['pages']}, glyphs: {summary['glyphs']}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")

    return destination


def import_gui_tools_project(
    input_path: Path,
    output_root: Path,
    images_root: Path | None = None,
) -> Path:
    """Import a gui-tools annotation file into the internal workspace."""
    bundle = load_gui_tools_bundle(input_path=input_path, images_root=images_root)
    return _write_import_bundle(
        importer_name="gui-tools",
        input_path=input_path,
        output_root=output_root,
        manifest=bundle.manifest,
        pages=bundle.pages,
        glyphs=bundle.glyphs,
        warnings=bundle.warnings,
    )


def import_kuiscima_project(
    input_path: Path,
    output_root: Path,
    images_root: Path | None = None,
) -> Path:
    """Import a KuiSCIMA JSON file into the internal workspace."""
    bundle = load_kuiscima_bundle(input_path=input_path, images_root=images_root)
    return _write_import_bundle(
        importer_name="kuiscima",
        input_path=input_path,
        output_root=output_root,
        manifest=bundle.manifest,
        pages=bundle.pages,
        glyphs=bundle.glyphs,
        warnings=bundle.warnings,
    )


def import_manual_csv_project(
    metadata_path: Path,
    annotations_path: Path,
    output_root: Path,
    images_root: Path | None = None,
) -> Path:
    """Import manually prepared metadata and annotation CSV files into the internal workspace."""
    bundle = load_manual_csv_bundle(
        metadata_path=metadata_path,
        annotations_path=annotations_path,
        images_root=images_root,
    )
    return _write_import_bundle(
        importer_name="manual-csv",
        input_path=metadata_path,
        output_root=output_root,
        manifest=bundle.manifest,
        pages=bundle.pages,
        glyphs=bundle.glyphs,
        warnings=bundle.warnings,
    )


def import_ocr_bundle_project(
    input_path: Path,
    output_root: Path,
) -> Path:
    """Import an OCR-engine output bundle into the internal workspace."""
    bundle = load_ocr_bundle(bundle_path=input_path)
    return _write_import_bundle(
        importer_name="ocr-bundle",
        input_path=input_path,
        output_root=output_root,
        manifest=bundle.manifest,
        pages=bundle.pages,
        glyphs=bundle.glyphs,
        warnings=bundle.warnings,
    )

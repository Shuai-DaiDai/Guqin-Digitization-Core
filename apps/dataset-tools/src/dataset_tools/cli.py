"""Command line interface for dataset-tools."""

from __future__ import annotations

import argparse
from pathlib import Path

from dataset_tools.pipeline.ingest import import_gui_tools_project
from dataset_tools.pipeline.ingest import import_kuiscima_project
from dataset_tools.pipeline.ingest import import_manual_csv_project
from dataset_tools.pipeline.ingest import import_ocr_bundle_project
from dataset_tools.pipeline.enrich import enrich_bundle
from dataset_tools.pipeline.document import assemble_document_draft
from dataset_tools.pipeline.manual_validation import validate_manual_csv_package
from dataset_tools.pipeline.pdf_library import inventory_pdf_library
from dataset_tools.pipeline.pdf_library import render_pdf_pages
from dataset_tools.pipeline.normalize import audit_bundle_quality
from dataset_tools.pipeline.normalize import normalize_bundle
from dataset_tools.pipeline.normalize import process_bundle
from dataset_tools.pipeline.project import project_jianzi_code_candidates
from dataset_tools.pipeline.reconcile import apply_review_decisions
from dataset_tools.pipeline.review_decision_templates import export_review_decisions_template
from dataset_tools.pipeline.project import summarize_bundle
from dataset_tools.pipeline.review_batches import slice_review_queue
from dataset_tools.pipeline.review import build_review_queue
from dataset_tools.pipeline.review_pack import prepare_review_pack
from dataset_tools.pipeline.online_review import apply_online_review_db
from dataset_tools.pipeline.online_review import apply_online_review_json
from dataset_tools.pipeline.next_batch import recommend_next_review_batch
from dataset_tools.pipeline.review_impact import evaluate_review_impact
from dataset_tools.pipeline.materialize_next_batch import materialize_next_review_batch
from dataset_tools.pipeline.missing_box_audit import prepare_missing_box_audit
from dataset_tools.pipeline.review_site import export_review_site
from dataset_tools.pipeline.templates import export_manual_templates
from dataset_tools.pipeline.workspace_index import build_workspace_index


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
    parser = argparse.ArgumentParser(
        prog="dataset-tools",
        description="Dataset workspace tools for Guqin Digitization Core.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_gui_tools = subparsers.add_parser(
        "import-gui-tools",
        help="Import a gui-tools jianzipu annotation JSON into the internal workspace.",
    )
    import_gui_tools.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to a gui-tools jianzipu JSON file.",
    )
    import_gui_tools.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory where the internal workspace import bundle will be written.",
    )
    import_gui_tools.add_argument(
        "--images-root",
        type=Path,
        default=None,
        help="Optional base directory for resolving relative image paths.",
    )

    import_kuiscima = subparsers.add_parser(
        "import-kuiscima",
        help="Import a KuiSCIMA-style JSON file into the internal workspace.",
    )
    import_kuiscima.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to a KuiSCIMA JSON file.",
    )
    import_kuiscima.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory where the internal workspace import bundle will be written.",
    )
    import_kuiscima.add_argument(
        "--images-root",
        type=Path,
        default=None,
        help="Optional base directory for resolving relative image paths.",
    )

    import_manual = subparsers.add_parser(
        "import-manual-csv",
        help="Import manually prepared metadata and rough annotation CSV files.",
    )
    import_manual.add_argument(
        "--metadata",
        required=True,
        type=Path,
        help="Path to the metadata CSV file.",
    )
    import_manual.add_argument(
        "--annotations",
        required=True,
        type=Path,
        help="Path to the rough annotation CSV file.",
    )
    import_manual.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory where the internal workspace import bundle will be written.",
    )
    import_manual.add_argument(
        "--images-root",
        type=Path,
        default=None,
        help="Optional base directory for resolving relative image paths.",
    )

    import_ocr_bundle = subparsers.add_parser(
        "import-ocr-bundle",
        help="Import an OCR-engine output bundle into the internal workspace.",
    )
    import_ocr_bundle.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to one OCR bundle directory.",
    )
    import_ocr_bundle.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory where the internal workspace import bundle will be written.",
    )

    inventory_pdfs = subparsers.add_parser(
        "inventory-pdf-library",
        help="Scan one local PDF collection and write a basic inventory report.",
    )
    inventory_pdfs.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Root directory that contains scanned PDF files.",
    )
    inventory_pdfs.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory where the PDF inventory files should be written.",
    )
    inventory_pdfs.add_argument(
        "--include-page-count",
        action="store_true",
        help="Also try to read total page counts for each PDF. This can be slow on large collections.",
    )

    render_pdfs = subparsers.add_parser(
        "render-pdf-pages",
        help="Render one scanned PDF into page images using PyMuPDF.",
    )
    render_pdfs.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to one scanned PDF file.",
    )
    render_pdfs.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory where rendered page images should be written.",
    )
    render_pdfs.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Rasterization DPI used for page rendering.",
    )
    render_pdfs.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="First page number to render, using 1-based page numbering.",
    )
    render_pdfs.add_argument(
        "--end-page",
        type=int,
        default=None,
        help="Optional last page number to render, using 1-based page numbering.",
    )

    validate_manual = subparsers.add_parser(
        "validate-manual-csv",
        help="Validate manually prepared metadata and annotation CSV files.",
    )
    validate_manual.add_argument(
        "--metadata",
        required=True,
        type=Path,
        help="Path to the metadata CSV file.",
    )
    validate_manual.add_argument(
        "--annotations",
        required=True,
        type=Path,
        help="Path to the rough annotation CSV file.",
    )
    validate_manual.add_argument(
        "--images-root",
        type=Path,
        default=None,
        help="Optional base directory for resolving relative image paths.",
    )

    summarize = subparsers.add_parser(
        "summarize-bundle",
        help="Build a basic summary report for one imported workspace bundle.",
    )
    summarize.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )

    project_candidates = subparsers.add_parser(
        "project-jianzi-code",
        help="Project imported music boxes into partial Jianzi-Code candidates.",
    )
    project_candidates.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )

    normalize = subparsers.add_parser(
        "normalize-bundle",
        help="Normalize projected candidates into a stable intermediate note layer.",
    )
    normalize.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )

    audit = subparsers.add_parser(
        "audit-bundle",
        help="Generate a simple quality audit report for one workspace bundle.",
    )
    audit.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )

    enrich = subparsers.add_parser(
        "enrich-bundle",
        help="Apply rule-based field mapping to build Jianzi-Code draft events.",
    )
    enrich.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )

    process = subparsers.add_parser(
        "process-bundle",
        help="Run summary, projection, normalization, and quality audit in order.",
    )
    process.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )

    review = subparsers.add_parser(
        "build-review-queue",
        help="Build a human review queue from draft events that still have gaps.",
    )
    review.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )

    review_batches = subparsers.add_parser(
        "slice-review-queue",
        help="Split one large review queue into smaller human-review batches.",
    )
    review_batches.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )
    review_batches.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Maximum item count per review batch.",
    )
    review_batches.add_argument(
        "--max-per-page",
        type=int,
        default=20,
        help="Maximum items from the same page in one batch.",
    )

    review_template = subparsers.add_parser(
        "export-review-decisions-template",
        help="Export a blank CSV template for human review decisions.",
    )
    review_template.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )
    review_template.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path where the blank review-decision template CSV should be written.",
    )
    review_template.add_argument(
        "--batch-id",
        default=None,
        help="Optional review batch id, for example batch_001.",
    )

    review_site = subparsers.add_parser(
        "export-review-site",
        help="Export a static OCR review site for one batch or full review queue.",
    )
    review_site.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )
    review_site.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory where the static review site should be written.",
    )
    review_site.add_argument(
        "--page-images-root",
        required=True,
        type=Path,
        help="Root directory that contains exported page images named like <page-id>.png.",
    )
    review_site.add_argument(
        "--batch-id",
        default=None,
        help="Optional review batch id, for example batch_001.",
    )
    review_site.add_argument(
        "--site-title",
        default=None,
        help="Optional page title shown in the review site.",
    )
    review_site.add_argument(
        "--api-base-url",
        default=None,
        help="Optional API base URL used by the review page for dynamic result submission.",
    )
    review_site.add_argument(
        "--require-token",
        action="store_true",
        help="Require a shared token before the page can submit review decisions.",
    )

    document = subparsers.add_parser(
        "assemble-document",
        help="Assemble a score-level Jianzi-Code document draft from event drafts.",
    )
    document.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )

    review_pack = subparsers.add_parser(
        "prepare-review-pack",
        help="Prepare a compact handoff package for human review.",
    )
    review_pack.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )

    apply_decisions = subparsers.add_parser(
        "apply-review-decisions",
        help="Apply a CSV of human review decisions back into draft events.",
    )
    apply_decisions.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )
    apply_decisions.add_argument(
        "--decisions",
        required=True,
        type=Path,
        help="Path to the review decisions CSV file.",
    )

    apply_online_review = subparsers.add_parser(
        "apply-online-review-db",
        help="Apply online box-review decisions from one SQLite database back into a bundle.",
    )
    apply_online_review.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )
    apply_online_review.add_argument(
        "--db",
        required=True,
        type=Path,
        help="Path to the online review SQLite database file.",
    )
    apply_online_review.add_argument(
        "--site-id",
        required=True,
        help="Review site id, for example source-id::batch_001.",
    )
    apply_online_review.add_argument(
        "--skip-rebuild",
        action="store_true",
        help="Only write verdicts back to raw glyphs and skip rebuilding derived outputs.",
    )

    apply_online_review_json_parser = subparsers.add_parser(
        "apply-online-review-json",
        help="Apply online box-review decisions from one exported JSON file back into a bundle.",
    )
    apply_online_review_json_parser.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )
    apply_online_review_json_parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to one exported review-decisions JSON file.",
    )
    apply_online_review_json_parser.add_argument(
        "--site-id",
        required=True,
        help="Review site id, for example source-id::batch_001.",
    )
    apply_online_review_json_parser.add_argument(
        "--skip-rebuild",
        action="store_true",
        help="Only write verdicts back to raw glyphs and skip rebuilding derived outputs.",
    )

    review_impact = subparsers.add_parser(
        "evaluate-review-impact",
        help="Summarize how human review changed one bundle.",
    )
    review_impact.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )
    review_impact.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output directory for the generated review-impact report.",
    )

    next_batch = subparsers.add_parser(
        "recommend-next-batch",
        help="Recommend the next high-value review batch from one bundle.",
    )
    next_batch.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )
    next_batch.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output directory for the next-batch recommendation.",
    )
    next_batch.add_argument(
        "--target-item-count",
        type=int,
        default=200,
        help="Soft target for how many review items the next recommendation should include.",
    )
    next_batch.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional hard cap on how many pages may be selected.",
    )
    next_batch.add_argument(
        "--include-partial-pages",
        action="store_true",
        help="Also allow partially reviewed pages to be recommended.",
    )

    materialize_next_batch = subparsers.add_parser(
        "materialize-next-batch",
        help="Turn one next-batch recommendation into a concrete review batch directory.",
    )
    materialize_next_batch.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )
    materialize_next_batch.add_argument(
        "--batch-id",
        required=True,
        help="Target batch id, for example batch_002.",
    )
    materialize_next_batch.add_argument(
        "--recommendation-dir",
        type=Path,
        default=None,
        help="Optional recommendation directory. Defaults to derived/next_batch under the bundle.",
    )
    materialize_next_batch.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional cap for how many recommended pages should be materialized into the batch.",
    )

    missing_box_audit = subparsers.add_parser(
        "prepare-missing-box-audit",
        help="Prepare one lightweight page pack for manual missing-box inspection.",
    )
    missing_box_audit.add_argument(
        "--bundle",
        required=True,
        type=Path,
        help="Path to one imported workspace bundle.",
    )
    missing_box_audit.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory where the missing-box audit pack should be written.",
    )
    missing_box_audit.add_argument(
        "--page-images-root",
        required=True,
        type=Path,
        help="Root directory that contains exported page images named like <page-id>.png.",
    )
    missing_box_audit.add_argument(
        "--page-id",
        action="append",
        default=None,
        help="Optional page id to include. Repeatable.",
    )
    missing_box_audit.add_argument(
        "--only-reviewed-pages",
        action="store_true",
        help="When page ids are not provided, only include pages that already have reviewed music boxes.",
    )
    missing_box_audit.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional cap for how many pages to include when page ids are not provided.",
    )

    workspace_index = subparsers.add_parser(
        "build-workspace-index",
        help="Build a workspace-level index for all bundles under one root directory.",
    )
    workspace_index.add_argument(
        "--workspace",
        required=True,
        type=Path,
        help="Path to a workspace root containing imported bundles.",
    )

    export_templates = subparsers.add_parser(
        "export-manual-templates",
        help="Export blank CSV templates for manual preparation and review workflows.",
    )
    export_templates.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory where the blank templates will be written.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the dataset-tools CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "import-gui-tools":
        import_gui_tools_project(
            input_path=args.input,
            output_root=args.output,
            images_root=args.images_root,
        )
        return 0

    if args.command == "import-kuiscima":
        import_kuiscima_project(
            input_path=args.input,
            output_root=args.output,
            images_root=args.images_root,
        )
        return 0

    if args.command == "import-manual-csv":
        import_manual_csv_project(
            metadata_path=args.metadata,
            annotations_path=args.annotations,
            output_root=args.output,
            images_root=args.images_root,
        )
        return 0

    if args.command == "import-ocr-bundle":
        import_ocr_bundle_project(
            input_path=args.input,
            output_root=args.output,
        )
        return 0

    if args.command == "inventory-pdf-library":
        inventory_pdf_library(
            input_root=args.input,
            output_dir=args.output,
            include_page_count=args.include_page_count,
        )
        return 0

    if args.command == "render-pdf-pages":
        render_pdf_pages(
            input_pdf=args.input,
            output_dir=args.output,
            dpi=args.dpi,
            start_page=args.start_page,
            end_page=args.end_page,
        )
        return 0

    if args.command == "validate-manual-csv":
        validate_manual_csv_package(
            metadata_path=args.metadata,
            annotations_path=args.annotations,
            images_root=args.images_root,
        )
        return 0

    if args.command == "summarize-bundle":
        summarize_bundle(bundle_path=args.bundle)
        return 0

    if args.command == "project-jianzi-code":
        project_jianzi_code_candidates(bundle_path=args.bundle)
        return 0

    if args.command == "normalize-bundle":
        normalize_bundle(bundle_path=args.bundle)
        return 0

    if args.command == "audit-bundle":
        audit_bundle_quality(bundle_path=args.bundle)
        return 0

    if args.command == "enrich-bundle":
        enrich_bundle(bundle_path=args.bundle)
        return 0

    if args.command == "process-bundle":
        process_bundle(bundle_path=args.bundle)
        return 0

    if args.command == "build-review-queue":
        build_review_queue(bundle_path=args.bundle)
        return 0

    if args.command == "slice-review-queue":
        slice_review_queue(
            bundle_path=args.bundle,
            batch_size=args.batch_size,
            max_per_page=args.max_per_page,
        )
        return 0

    if args.command == "export-review-decisions-template":
        export_review_decisions_template(
            bundle_path=args.bundle,
            output_path=args.output,
            batch_id=args.batch_id,
        )
        return 0

    if args.command == "export-review-site":
        export_review_site(
            bundle_path=args.bundle,
            output_dir=args.output,
            page_images_root=args.page_images_root,
            batch_id=args.batch_id,
            site_title=args.site_title,
            api_base_url=args.api_base_url,
            require_token=args.require_token,
        )
        return 0

    if args.command == "assemble-document":
        assemble_document_draft(bundle_path=args.bundle)
        return 0

    if args.command == "prepare-review-pack":
        prepare_review_pack(bundle_path=args.bundle)
        return 0

    if args.command == "apply-review-decisions":
        apply_review_decisions(bundle_path=args.bundle, decisions_path=args.decisions)
        return 0

    if args.command == "apply-online-review-db":
        result = {
            "review_apply": apply_online_review_db(
                bundle_path=args.bundle,
                db_path=args.db,
                site_id=args.site_id,
            )
        }
        if not args.skip_rebuild:
            result["rebuild"] = process_bundle(bundle_path=args.bundle)
        return 0

    if args.command == "apply-online-review-json":
        result = {
            "review_apply": apply_online_review_json(
                bundle_path=args.bundle,
                json_path=args.input,
                site_id=args.site_id,
            )
        }
        if not args.skip_rebuild:
            result["rebuild"] = process_bundle(bundle_path=args.bundle)
        return 0

    if args.command == "evaluate-review-impact":
        evaluate_review_impact(bundle_path=args.bundle, output_dir=args.output)
        return 0

    if args.command == "recommend-next-batch":
        recommend_next_review_batch(
            bundle_path=args.bundle,
            output_dir=args.output,
            target_item_count=args.target_item_count,
            max_pages=args.max_pages,
            include_partial_pages=args.include_partial_pages,
        )
        return 0

    if args.command == "materialize-next-batch":
        materialize_next_review_batch(
            bundle_path=args.bundle,
            batch_id=args.batch_id,
            recommendation_dir=args.recommendation_dir,
            max_pages=args.max_pages,
        )
        return 0

    if args.command == "prepare-missing-box-audit":
        prepare_missing_box_audit(
            bundle_path=args.bundle,
            output_dir=args.output,
            page_images_root=args.page_images_root,
            page_ids=args.page_id,
            only_reviewed_pages=args.only_reviewed_pages,
            max_pages=args.max_pages,
        )
        return 0

    if args.command == "build-workspace-index":
        build_workspace_index(workspace_root=args.workspace)
        return 0

    if args.command == "export-manual-templates":
        export_manual_templates(output_dir=args.output)
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2

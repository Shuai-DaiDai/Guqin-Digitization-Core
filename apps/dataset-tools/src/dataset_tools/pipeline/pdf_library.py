"""PDF inventory and rasterization helpers for scanned score collections."""

from __future__ import annotations

import csv
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dataset_tools.io_utils import ensure_dir, write_json


def inventory_pdf_library(
    *,
    input_root: Path,
    output_dir: Path,
    include_page_count: bool = False,
) -> dict[str, Any]:
    """Scan one directory tree and write a basic PDF inventory."""
    pdf_paths = sorted(path for path in input_root.rglob("*.pdf") if path.is_file())
    ensure_dir(output_dir)

    records: list[dict[str, Any]] = []
    for pdf_path in pdf_paths:
        relative_path = pdf_path.relative_to(input_root)
        records.append(
            {
                "relative_path": str(relative_path),
                "filename": pdf_path.name,
                "stem": pdf_path.stem,
                "size_bytes": pdf_path.stat().st_size,
                "page_count": _read_pdf_page_count(pdf_path) if include_page_count else None,
            }
        )

    summary = {
        "input_root": str(input_root.resolve()),
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "pdf_count": len(records),
        "include_page_count": include_page_count,
        "known_page_counts": sum(1 for record in records if isinstance(record.get("page_count"), int)),
        "records": records,
    }
    write_json(output_dir / "pdf_inventory.json", summary)
    _write_inventory_csv(records=records, output_path=output_dir / "pdf_inventory.csv")
    print(f"Wrote PDF inventory to {output_dir}")
    print(f"PDF files: {len(records)}")
    return summary


def render_pdf_pages(
    *,
    input_pdf: Path,
    output_dir: Path,
    dpi: int = 200,
    start_page: int = 1,
    end_page: int | None = None,
) -> dict[str, Any]:
    """Render one PDF page range into PNG page images."""
    fitz = _require_pymupdf()
    ensure_dir(output_dir)

    with fitz.open(input_pdf) as document:
        page_count = int(document.page_count)
        first_page = max(1, start_page)
        last_page = min(page_count, end_page if end_page is not None else page_count)
        if first_page > last_page:
            raise ValueError(
                f"Invalid page range for {input_pdf}: start_page={start_page}, end_page={end_page}, page_count={page_count}"
            )

        slug = _slugify_text(input_pdf.stem)
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        rendered_pages: list[dict[str, Any]] = []

        for page_number in range(first_page, last_page + 1):
            page = document.load_page(page_number - 1)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            output_path = output_dir / f"{slug}-p{page_number:04d}.png"
            pixmap.save(str(output_path))
            rendered_pages.append(
                {
                    "page_number": page_number,
                    "image_path": str(output_path.resolve()),
                    "width": int(pixmap.width),
                    "height": int(pixmap.height),
                }
            )

    manifest = {
        "input_pdf": str(input_pdf.resolve()),
        "output_dir": str(output_dir.resolve()),
        "dpi": dpi,
        "page_count": page_count,
        "rendered_page_count": len(rendered_pages),
        "start_page": first_page,
        "end_page": last_page,
        "pages": rendered_pages,
    }
    write_json(output_dir / "render_manifest.json", manifest)
    print(f"Rendered {len(rendered_pages)} page image(s) to {output_dir}")
    return manifest


def _write_inventory_csv(*, records: list[dict[str, Any]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "relative_path",
                "filename",
                "stem",
                "size_bytes",
                "page_count",
            ],
        )
        writer.writeheader()
        writer.writerows(records)


def _read_pdf_page_count(pdf_path: Path) -> int | None:
    try:
        fitz = _import_pymupdf()
        if fitz is not None:
            with fitz.open(pdf_path) as document:
                return int(document.page_count)
    except Exception:
        pass

    if subprocess.run(["which", "mdls"], capture_output=True, text=True).returncode == 0:
        result = subprocess.run(
            ["mdls", "-raw", "-name", "kMDItemNumberOfPages", str(pdf_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            value = result.stdout.strip()
            if value.isdigit():
                return int(value)

    return None


def _import_pymupdf():
    try:
        import fitz  # type: ignore

        return fitz
    except Exception:
        return None


def _require_pymupdf():
    fitz = _import_pymupdf()
    if fitz is None:
        raise RuntimeError(
            "PyMuPDF is required for render-pdf-pages. Install pymupdf in the active Python environment first."
        )
    return fitz


def _slugify_text(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", value).strip("-").lower()
    return slug or "pdf"

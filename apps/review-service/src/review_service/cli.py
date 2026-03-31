"""CLI entry point for review-service."""

from __future__ import annotations

import argparse
from pathlib import Path

from review_service.server import ReviewServiceConfig, run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="review-service",
        description="Serve a token-protected OCR review site with result collection.",
    )
    parser.add_argument("--site-root", required=True, type=Path, help="Static review site directory.")
    parser.add_argument("--db", required=True, type=Path, help="SQLite file used to store review results.")
    parser.add_argument("--token", required=True, help="Shared token required for result submission.")
    parser.add_argument("--host", default="0.0.0.0", help="Listen host.")
    parser.add_argument("--port", default=8787, type=int, help="Listen port.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = ReviewServiceConfig(
        host=args.host,
        port=args.port,
        site_root=args.site_root,
        db_path=args.db,
        shared_token=args.token,
    )
    run_server(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

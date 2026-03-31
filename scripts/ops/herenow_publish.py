#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import time
import subprocess
from pathlib import Path
from typing import Any


API_BASE = "https://here.now/api/v1/publish"
CLIENT_NAME = "codex/guqin-review"
HTTP_TIMEOUT_SECONDS = 300
FINALIZE_RETRIES = 3


def sha256_hex(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(site_dir: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in sorted(site_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(site_dir).as_posix()
        content_type, _ = mimetypes.guess_type(str(path))
        files.append(
            {
                "path": rel,
                "size": path.stat().st_size,
                "contentType": content_type or "application/octet-stream",
                "hash": sha256_hex(path),
            }
        )
    return files


def curl_json_request(
    url: str,
    method: str,
    payload: dict[str, Any],
    api_key: str | None,
) -> dict[str, Any]:
    command = [
        "curl",
        "-sS",
        "--connect-timeout",
        str(HTTP_TIMEOUT_SECONDS),
        "--max-time",
        str(HTTP_TIMEOUT_SECONDS),
        "-X",
        method,
        url,
        "-H",
        "Content-Type: application/json",
        "-H",
        f"X-HereNow-Client: {CLIENT_NAME}",
        "--data-binary",
        json.dumps(payload),
    ]
    if api_key:
        command.extend(["-H", f"Authorization: Bearer {api_key}"])
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def put_file(upload_url: str, headers: dict[str, str], file_path: Path) -> None:
    command = ["curl", "-sS", "-X", "PUT", upload_url]
    for name, value in headers.items():
        command.extend(["-H", f"{name}: {value}"])
    command.extend(["--data-binary", f"@{file_path}"])
    subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a static site directory to here.now.")
    parser.add_argument("site_dir", help="Directory containing the site files.")
    parser.add_argument("--title", default=None, help="Viewer title metadata.")
    parser.add_argument("--description", default=None, help="Viewer description metadata.")
    parser.add_argument("--slug", default=None, help="Existing site slug to update.")
    args = parser.parse_args()

    site_dir = Path(args.site_dir).resolve()
    if not site_dir.is_dir():
        raise SystemExit(f"Site directory not found: {site_dir}")

    api_key = os.environ.get("HERENOW_API_KEY")
    files = iter_files(site_dir)
    if not files:
        raise SystemExit(f"No files found under: {site_dir}")

    payload: dict[str, Any] = {"files": files}
    viewer: dict[str, str] = {}
    if args.title:
        viewer["title"] = args.title
    if args.description:
        viewer["description"] = args.description
    if viewer:
        payload["viewer"] = viewer

    if args.slug:
        init = curl_json_request(f"{API_BASE}/{args.slug}", "PUT", payload, api_key)
    else:
        init = curl_json_request(API_BASE, "POST", payload, api_key)

    print(
        json.dumps(
            {
                "stage": "created",
                "slug": init["slug"],
                "siteUrl": init["siteUrl"],
                "uploads": len(init["upload"]["uploads"]),
                "skipped": len(init["upload"].get("skipped", [])),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    for upload in init["upload"]["uploads"]:
        local_path = site_dir / upload["path"]
        print(
            json.dumps(
                {"stage": "uploading", "path": upload["path"], "size": local_path.stat().st_size},
                ensure_ascii=False,
            ),
            flush=True,
        )
        put_file(upload["url"], upload.get("headers", {}), local_path)
        print(json.dumps({"stage": "uploaded", "path": upload["path"]}, ensure_ascii=False), flush=True)

    finalize_url = init["upload"]["finalizeUrl"]
    finalize_payload = {"versionId": init["upload"]["versionId"]}
    finalized = None
    for attempt in range(1, FINALIZE_RETRIES + 1):
        try:
            finalized = curl_json_request(finalize_url, "POST", finalize_payload, api_key)
            break
        except subprocess.CalledProcessError:
            if attempt >= FINALIZE_RETRIES:
                raise
            print(
                json.dumps(
                    {"stage": "finalize_retry", "attempt": attempt + 1, "slug": init["slug"]},
                    ensure_ascii=False,
                ),
                flush=True,
            )
            time.sleep(3)

    if finalized is None:
        raise SystemExit("Failed to finalize here.now publish.")

    print(json.dumps({"slug": finalized["slug"], "siteUrl": finalized["siteUrl"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

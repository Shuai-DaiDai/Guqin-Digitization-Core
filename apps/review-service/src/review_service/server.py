"""Small token-protected review result service."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ReviewServiceConfig:
    host: str
    port: int
    site_root: Path
    db_path: Path
    shared_token: str


class DecisionStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists decisions (
                  site_id text not null,
                  review_id text not null,
                  verdict text not null,
                  note text not null default '',
                  updated_at text not null,
                  primary key (site_id, review_id)
                )
                """
            )
            conn.execute(
                """
                create table if not exists page_notes (
                  site_id text not null,
                  page_id text not null,
                  has_missing_boxes integer,
                  note text not null default '',
                  updated_at text not null,
                  primary key (site_id, page_id)
                )
                """
            )
            conn.commit()

    def list_decisions(self, site_id: str) -> dict[str, dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                "select review_id, verdict, note, updated_at from decisions where site_id = ?",
                (site_id,),
            ).fetchall()
        return {
            str(review_id): {
                "verdict": verdict,
                "note": note,
                "updatedAt": updated_at,
            }
            for review_id, verdict, note, updated_at in rows
        }

    def save_decision(self, site_id: str, review_id: str, verdict: str, note: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into decisions(site_id, review_id, verdict, note, updated_at)
                values (?, ?, ?, ?, ?)
                on conflict(site_id, review_id)
                do update set verdict=excluded.verdict, note=excluded.note, updated_at=excluded.updated_at
                """,
                (site_id, review_id, verdict, note, utc_now()),
            )
            conn.commit()

    def list_page_notes(self, site_id: str) -> dict[str, dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                "select page_id, has_missing_boxes, note, updated_at from page_notes where site_id = ?",
                (site_id,),
            ).fetchall()
        return {
            str(page_id): {
                "hasMissingBoxes": None if has_missing_boxes is None else bool(has_missing_boxes),
                "note": note,
                "updatedAt": updated_at,
            }
            for page_id, has_missing_boxes, note, updated_at in rows
        }

    def save_page_note(self, site_id: str, page_id: str, has_missing_boxes: bool | None, note: str) -> None:
        encoded = None if has_missing_boxes is None else int(bool(has_missing_boxes))
        with self._connect() as conn:
            conn.execute(
                """
                insert into page_notes(site_id, page_id, has_missing_boxes, note, updated_at)
                values (?, ?, ?, ?, ?)
                on conflict(site_id, page_id)
                do update set has_missing_boxes=excluded.has_missing_boxes, note=excluded.note, updated_at=excluded.updated_at
                """,
                (site_id, page_id, encoded, note, utc_now()),
            )
            conn.commit()


class ReviewServiceApp:
    def __init__(self, config: ReviewServiceConfig) -> None:
        self.config = config
        self.store = DecisionStore(config.db_path)
        self.review_data = json.loads((config.site_root / "data" / "review-data.json").read_text(encoding="utf-8"))
        self.site_id = str(self.review_data.get("site", {}).get("siteId", ""))
        self.item_by_review_id = {
            str(item.get("reviewId", "")): item
            for item in self.review_data.get("items", [])
            if str(item.get("reviewId", ""))
        }
        self.page_totals = {}
        for item in self.review_data.get("items", []):
            page_id = str(item.get("pageId", ""))
            self.page_totals[page_id] = self.page_totals.get(page_id, 0) + 1

    def is_authorized(self, token: str) -> bool:
        return bool(token) and token == self.config.shared_token

    def progress_by_page(self, decisions: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
        reviewed_by_page: dict[str, int] = {}
        for review_id, decision in decisions.items():
            item = self.item_by_review_id.get(review_id)
            if not item:
                continue
            verdict = str(decision.get("verdict", "undecided"))
            if verdict == "undecided":
                continue
            page_id = str(item.get("pageId", ""))
            reviewed_by_page[page_id] = reviewed_by_page.get(page_id, 0) + 1

        progress = {}
        for page_id, total in self.page_totals.items():
            reviewed = reviewed_by_page.get(page_id, 0)
            progress[page_id] = {
                "reviewed": reviewed,
                "total": total,
                "completed": reviewed >= total and total > 0,
            }
        return progress

    def auth_response(self) -> dict[str, object]:
        return {
            "ok": True,
            "siteId": self.site_id,
            "siteTitle": self.review_data.get("site", {}).get("title", ""),
        }

    def bootstrap_response(self, site_id: str) -> dict[str, object]:
        decisions = self.store.list_decisions(site_id)
        page_notes = self.store.list_page_notes(site_id)
        return {
            "siteId": site_id,
            "decisions": decisions,
            "progressByPage": self.progress_by_page(decisions),
            "pageNotes": page_notes,
        }

    def save_and_report(self, site_id: str, review_id: str, verdict: str, note: str) -> dict[str, object]:
        self.store.save_decision(site_id, review_id, verdict, note)
        decisions = self.store.list_decisions(site_id)
        page_notes = self.store.list_page_notes(site_id)
        return {
            "ok": True,
            "siteId": site_id,
            "reviewId": review_id,
            "progressByPage": self.progress_by_page(decisions),
            "pageNotes": page_notes,
        }

    def save_page_note_and_report(
        self,
        site_id: str,
        page_id: str,
        has_missing_boxes: bool | None,
        note: str,
    ) -> dict[str, object]:
        self.store.save_page_note(site_id, page_id, has_missing_boxes, note)
        decisions = self.store.list_decisions(site_id)
        page_notes = self.store.list_page_notes(site_id)
        return {
            "ok": True,
            "siteId": site_id,
            "pageId": page_id,
            "progressByPage": self.progress_by_page(decisions),
            "pageNotes": page_notes,
        }


def build_handler(app: ReviewServiceApp):
    class ReviewHandler(BaseHTTPRequestHandler):
        server_version = "GuqinReviewService/0.1"

        def _token(self) -> str:
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                return auth[7:].strip()
            return self.headers.get("X-Review-Token", "").strip()

        def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Review-Token")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict[str, object]:
            length = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(length) if length > 0 else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")

        def _require_auth(self) -> bool:
            if app.is_authorized(self._token()):
                return True
            self._send_json({"ok": False, "error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
            return False

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Review-Token")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/healthz":
                self._send_json({"ok": True, "time": utc_now()})
                return
            if parsed.path == "/api/bootstrap":
                if not self._require_auth():
                    return
                query = parse_qs(parsed.query)
                site_id = str(query.get("siteId", [app.site_id])[0])
                self._send_json(app.bootstrap_response(site_id))
                return
            self._serve_static(parsed.path)

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/api/auth":
                if not self._require_auth():
                    return
                self._send_json(app.auth_response())
                return
            if self.path == "/api/decision":
                if not self._require_auth():
                    return
                payload = self._read_json()
                site_id = str(payload.get("siteId", "")).strip()
                review_id = str(payload.get("reviewId", "")).strip()
                verdict = str(payload.get("verdict", "undecided")).strip()
                note = str(payload.get("note", "")).strip()
                if site_id != app.site_id:
                    self._send_json({"ok": False, "error": "invalid_site"}, status=HTTPStatus.BAD_REQUEST)
                    return
                if review_id not in app.item_by_review_id:
                    self._send_json({"ok": False, "error": "unknown_review_id"}, status=HTTPStatus.BAD_REQUEST)
                    return
                if verdict not in {"undecided", "correct", "wrong", "skipped"}:
                    self._send_json({"ok": False, "error": "invalid_verdict"}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(app.save_and_report(site_id, review_id, verdict, note))
                return
            if self.path == "/api/page-note":
                if not self._require_auth():
                    return
                payload = self._read_json()
                site_id = str(payload.get("siteId", "")).strip()
                page_id = str(payload.get("pageId", "")).strip()
                note = str(payload.get("note", "")).strip()
                raw_missing = payload.get("hasMissingBoxes")
                if site_id != app.site_id:
                    self._send_json({"ok": False, "error": "invalid_site"}, status=HTTPStatus.BAD_REQUEST)
                    return
                if page_id not in app.page_totals:
                    self._send_json({"ok": False, "error": "unknown_page_id"}, status=HTTPStatus.BAD_REQUEST)
                    return
                if raw_missing not in {None, True, False}:
                    self._send_json({"ok": False, "error": "invalid_missing_box_flag"}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(app.save_page_note_and_report(site_id, page_id, raw_missing, note))
                return
            self._send_json({"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def _serve_static(self, request_path: str) -> None:
            safe_path = request_path.lstrip("/") or "index.html"
            target = (app.config.site_root / safe_path).resolve()
            try:
                target.relative_to(app.config.site_root.resolve())
            except ValueError:
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content_type = "text/plain; charset=utf-8"
            if target.suffix == ".html":
                content_type = "text/html; charset=utf-8"
            elif target.suffix == ".css":
                content_type = "text/css; charset=utf-8"
            elif target.suffix == ".js":
                content_type = "text/javascript; charset=utf-8"
            elif target.suffix == ".json":
                content_type = "application/json; charset=utf-8"
            elif target.suffix == ".png":
                content_type = "image/png"
            elif target.suffix in {".jpg", ".jpeg"}:
                content_type = "image/jpeg"
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ReviewHandler


def run_server(config: ReviewServiceConfig) -> None:
    app = ReviewServiceApp(config)
    server = ThreadingHTTPServer((config.host, config.port), build_handler(app))
    print(
        json.dumps(
            {
                "host": config.host,
                "port": config.port,
                "site_root": str(config.site_root),
                "db_path": str(config.db_path),
                "site_id": app.site_id,
            },
            ensure_ascii=False,
        )
    )
    server.serve_forever()

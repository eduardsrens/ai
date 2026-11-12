"""Run with python server.py. Uses only the Python standard library."""

from __future__ import annotations

import argparse
import gzip
import json
import mimetypes
import secrets
import sqlite3
import sys
import threading
import webbrowser
from contextlib import contextmanager
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import game  # noqa: E402

LOCK = threading.Lock()
DB = ROOT / "saves.sqlite3"
STATIC_DIR = ROOT / "static"
GZIP_TYPES = (
    ".html",
    ".css",
    ".js",
    ".mjs",
    ".json",
    ".svg",
    ".txt",
)


@contextmanager
def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    try:
        with db:
            db.execute("CREATE TABLE IF NOT EXISTS games (id TEXT PRIMARY KEY, state TEXT NOT NULL)")
            yield db
    finally:
        db.close()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self):
        path = urlsplit(self.path).path
        if path.startswith("/vendor/"):
            self.send_header("Cache-Control", "public, max-age=86400")
        elif not path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def _session_id(self) -> str:
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            pass
        if "pocket_party_session" in cookie:
            return cookie["pocket_party_session"].value
        if "life_session" in cookie:
            return cookie["life_session"].value
        return secrets.token_urlsafe(24)

    def _accepts_gzip(self) -> bool:
        return "gzip" in self.headers.get("Accept-Encoding", "").lower()

    def _send_bytes(self, status: int, content_type: str, raw: bytes, extra_headers: dict[str, str] | None = None, compress: bool = True):
        use_gzip = compress and len(raw) >= 512 and self._accepts_gzip()
        payload = gzip.compress(raw, compresslevel=5) if use_gzip else raw
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        if use_gzip:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def api(self, action: str | None = None):
        session = self._session_id()
        try:
            with LOCK, connect() as db:
                row = db.execute("SELECT state FROM games WHERE id=?", (session,)).fetchone()
                state = json.loads(row[0]) if row else game.new_game()
                if state.get("version") != game.VERSION:
                    state = game.new_game()
                if action:
                    length = int(self.headers.get("Content-Length", 0))
                    if not 0 <= length <= 8192:
                        raise ValueError("Request too large.")
                    body = json.loads(self.rfile.read(length) or "{}")
                    if not isinstance(body, dict):
                        raise ValueError("Expected a JSON object.")
                    if action == "start":
                        rounds = body.get("rounds", 8)
                        game.start(state, body.get("names"), rounds)
                    elif action == "spin":
                        game.spin(state)
                    elif action == "choice":
                        game.choose(state, body.get("option"))
                    elif action == "ready":
                        game.ready(state)
                    elif action == "item":
                        game.use_item(state, body.get("item"), body.get("target"))
                    elif action == "endturn":
                        game.end_turn(state)
                    elif action == "minigame":
                        game.minigame(state, body)
                    elif action == "next":
                        game.next_round(state)
                    elif action == "reset":
                        state = game.new_game()
                    else:
                        raise ValueError("Unknown action.")
                db.execute("INSERT OR REPLACE INTO games VALUES (?, ?)", (session, json.dumps(state)))
            self.reply(200, {"game": state, "tiles": game.TYPES, "items": game.ITEMS}, session)
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            self.reply(400, {"error": str(exc)}, session)

    def reply(self, status: int, data: dict, session: str):
        content = json.dumps(data).encode("utf-8")
        self._send_bytes(
            status,
            "application/json; charset=utf-8",
            content,
            extra_headers={
                "Cache-Control": "no-store",
                "Set-Cookie": f"pocket_party_session={session}; Path=/; HttpOnly; SameSite=Lax",
            },
            compress=True,
        )

    def _serve_static(self, rel_path: str):
        if rel_path == "/" or rel_path == "":
            rel_path = "/index.html"
        safe_rel = rel_path.lstrip("/")
        try:
            target = (STATIC_DIR / safe_rel).resolve()
            target.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self.send_error(403)
            return
        if not target.is_file():
            self.send_error(404)
            return
        suffix = target.suffix.lower()
        ctype, _ = mimetypes.guess_type(str(target))
        if suffix in (".js", ".mjs"):
            ctype = "application/javascript; charset=utf-8"
        elif suffix == ".css":
            ctype = "text/css; charset=utf-8"
        elif suffix == ".html":
            ctype = "text/html; charset=utf-8"
        elif suffix == ".svg":
            ctype = "image/svg+xml"
        elif not ctype:
            ctype = "application/octet-stream"
        raw = target.read_bytes()
        self._send_bytes(200, ctype, raw, compress=(suffix in GZIP_TYPES))

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/game":
            self.api()
        else:
            self._serve_static(path)

    def do_POST(self):
        path = urlsplit(self.path).path
        if path.startswith("/api/"):
            self.api(path[5:])
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        # Keep console output crisp unless running verbosely; still log errors.
        if args and len(args) >= 2 and str(args[1]).startswith(("4", "5")):
            super().log_message(format, *args)


def main(argv=None):
    global DB
    parser = argparse.ArgumentParser(description="Play Pocket Party in your browser.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: local device only)")
    parser.add_argument("--port", type=int, default=3000, help="HTTP port (default: 3000)")
    parser.add_argument("--open", action="store_true", help="Open the game in your default browser")
    parser.add_argument("--data-dir", type=Path, help="Optional directory for saved games")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("Port must be between 0 and 65535.")
    if args.data_dir is not None:
        DB = args.data_dir.expanduser().resolve() / "saves.sqlite3"
    try:
        httpd = ThreadingHTTPServer((args.host, args.port), Handler)
        with connect():
            pass
    except (OSError, sqlite3.Error) as exc:
        parser.exit(1, f"Could not start Pocket Party: {exc}. Try --port 3001 or a writable --data-dir.\n")
    host = "127.0.0.1" if args.host in ("0.0.0.0", "::") else args.host
    url = f"http://{host}:{httpd.server_port}"
    print(f"Pocket Party is ready at {url}\nPress Ctrl+C to stop.", flush=True)
    if args.open:
        browser = threading.Timer(0.4, webbrowser.open, args=(url,))
        browser.daemon = True
        browser.start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()

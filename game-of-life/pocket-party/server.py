"""Run with python server.py. No Python dependencies required."""
import argparse
import json
import secrets
import sqlite3
import threading
import webbrowser
from contextlib import contextmanager
from urllib.parse import urlsplit
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import game

ROOT = Path(__file__).resolve().parent
LOCK = threading.Lock()
DB = ROOT / 'saves.sqlite3'

@contextmanager
def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    try:
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS games (id TEXT PRIMARY KEY, state TEXT NOT NULL)')
            yield db
    finally:
        db.close()

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'static'), **kwargs)

    def api(self, action=None):
        cookie = SimpleCookie()
        try: cookie.load(self.headers.get('Cookie', ''))
        except Exception: pass
        session = cookie['life_session'].value if 'life_session' in cookie else secrets.token_urlsafe(24)
        try:
            with LOCK, connect() as db:
                row = db.execute('SELECT state FROM games WHERE id=?', (session,)).fetchone()
                state = json.loads(row[0]) if row else game.new_game()
                if state.get('version') != game.VERSION: state = game.new_game()
                if action:
                    length = int(self.headers.get('Content-Length', 0))
                    if not 0 <= length <= 4096: raise ValueError('Request too large.')
                    body = json.loads(self.rfile.read(length) or '{}')
                    if not isinstance(body, dict): raise ValueError('Expected a JSON object.')
                    if action == 'start': game.start(state, body.get('names'))
                    elif action == 'spin': game.spin(state)
                    elif action == 'choice': game.choose(state, body.get('option'))
                    elif action == 'ready': game.ready(state)
                    elif action == 'item': game.use_item(state, body.get('item'), body.get('target'))
                    elif action == 'endturn': game.end_turn(state)
                    elif action == 'minigame': game.minigame(state, body)
                    elif action == 'next': game.next_round(state)
                    elif action == 'reset': state = game.new_game()
                    else: raise ValueError('Unknown action.')
                db.execute('INSERT OR REPLACE INTO games VALUES (?, ?)', (session, json.dumps(state)))
            self.reply(200, {'game':state, 'tiles':game.TYPES, 'items':game.ITEMS}, session)
        except (ValueError, TypeError, KeyError) as exc:
            self.reply(400, {'error': str(exc)}, session)

    def reply(self, status, data, session):
        content = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Set-Cookie', f'life_session={session}; Path=/; HttpOnly; SameSite=Lax')
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if urlsplit(self.path).path == '/api/game': self.api()
        else: super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path.startswith('/api/'): self.api(urlsplit(self.path).path[5:])
        else: self.send_error(404)

def main(argv=None):
    global DB
    parser = argparse.ArgumentParser(description='Play Pocket Party in your browser.')
    parser.add_argument('--host', default='127.0.0.1', help='Bind address (default: local device only)')
    parser.add_argument('--port', type=int, default=3000, help='HTTP port (default: 3000)')
    parser.add_argument('--open', action='store_true', help='Open the game in your default browser')
    parser.add_argument('--data-dir', type=Path, help='Optional directory for saved games')
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error('Port must be between 0 and 65535.')
    if args.data_dir is not None:
        DB = args.data_dir.expanduser().resolve() / 'saves.sqlite3'
    try:
        httpd = ThreadingHTTPServer((args.host, args.port), Handler)
        with connect():
            pass
    except (OSError, sqlite3.Error) as exc:
        parser.exit(1, f'Could not start Pocket Party: {exc}. Try --port 3001 or a writable --data-dir.\n')
    host = '127.0.0.1' if args.host in ('0.0.0.0', '::') else args.host
    url = f'http://{host}:{httpd.server_port}'
    print(f'Pocket Party is ready at {url}\nPress Ctrl+C to stop.', flush=True)
    if args.open:
        browser = threading.Timer(.4, webbrowser.open, args=(url,))
        browser.daemon = True
        browser.start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == '__main__':
    main()

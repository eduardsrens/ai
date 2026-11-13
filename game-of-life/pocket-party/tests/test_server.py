import gzip
import http.client
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server  # noqa: E402


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(server, "DB", Path(self.temp.name) / "data" / "saves.sqlite3")
        self.db_patch.start()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.cookie = None

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()
        self.db_patch.stop()
        self.temp.cleanup()

    def request(self, method, path, body=None, accept_gzip=False):
        connection = http.client.HTTPConnection("127.0.0.1", self.httpd.server_port, timeout=5)
        headers = {}
        if self.cookie:
            headers["Cookie"] = self.cookie
        if accept_gzip:
            headers["Accept-Encoding"] = "gzip"
        if body is not None:
            body = json.dumps(body)
            headers["Content-Type"] = "application/json"
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        content = response.read()
        encoding = response.getheader("Content-Encoding")
        if encoding == "gzip":
            content = gzip.decompress(content)
        cookie = response.getheader("Set-Cookie")
        if cookie:
            self.cookie = cookie.split(";")[0]
        result = (response.status, content, dict(response.getheaders()))
        connection.close()
        return result

    def test_browser_assets_and_query_routes(self):
        for path, content in [
            ("/", b"POCKET"),
            ("/app.js", b"PartyWorld"),
            ("/scene.js", b"PartyWorld"),
            ("/audio.js", b"PartyAudio"),
            ("/minigames.js", b"launchMinigame"),
            ("/vendor/three.module.js", b"WebGLRenderer"),
        ]:
            status, data, headers = self.request("GET", path, accept_gzip=True)
            self.assertEqual(status, 200, path)
            self.assertIn(content, data, path)
            self.assertEqual(headers.get("Content-Encoding"), "gzip", path)
        status, data, _ = self.request("GET", "/api/game?check=1")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["game"]["phase"], "setup")

    def test_saved_party_and_session_isolation(self):
        status, _, _ = self.request("POST", "/api/start", {"names": ["Sunny", "River"], "rounds": 5})
        self.assertEqual(status, 200)
        original_cookie = self.cookie
        self.assertTrue(server.DB.exists())
        status, data, _ = self.request("GET", "/api/game")
        parsed = json.loads(data)["game"]
        self.assertEqual(parsed["players"][0]["name"], "Sunny")
        self.assertEqual(parsed["max_rounds"], 5)
        self.cookie = None
        _, data, _ = self.request("GET", "/api/game")
        self.assertEqual(json.loads(data)["game"]["phase"], "setup")
        self.assertNotEqual(self.cookie, original_cookie)

    def test_invalid_body_and_early_move_do_not_change_state(self):
        for body in [[], "wrong", None]:
            status, _, _ = self.request("POST", "/api/spin", body)
            self.assertEqual(status, 400)
        _, data, _ = self.request("GET", "/api/game")
        self.assertEqual(json.loads(data)["game"]["phase"], "setup")

    def test_path_traversal_blocked(self):
        status, _, _ = self.request("GET", "/../server.py")
        self.assertIn(status, (403, 404))

    def test_launch_from_other_working_directory(self):
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        result = subprocess.run(
            [sys.executable, str(server.ROOT / "server.py"), "--help"],
            cwd=self.temp.name,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--open", result.stdout)
        self.assertIn("--data-dir", result.stdout)


if __name__ == "__main__":
    unittest.main()

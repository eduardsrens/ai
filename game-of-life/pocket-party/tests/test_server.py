import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer

import server


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(server, 'DB', Path(self.temp.name) / 'data' / 'saves.sqlite3')
        self.db_patch.start()
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.cookie = None

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()
        self.db_patch.stop()
        self.temp.cleanup()

    def request(self, method, path, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.httpd.server_port, timeout=5)
        headers = {}
        if self.cookie:
            headers['Cookie'] = self.cookie
        if body is not None:
            body = json.dumps(body)
            headers['Content-Type'] = 'application/json'
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        content = response.read()
        cookie = response.getheader('Set-Cookie')
        if cookie:
            self.cookie = cookie.split(';')[0]
        result = (response.status, content)
        connection.close()
        return result

    def test_browser_assets_and_query_routes(self):
        for path, content in [('/', b'POCKET'), ('/app.js', b'PartyWorld'), ('/vendor/three.module.js', b'WebGLRenderer')]:
            status, data = self.request('GET', path)
            self.assertEqual(status, 200)
            self.assertIn(content, data)
        status, data = self.request('GET', '/api/game?check=1')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)['game']['phase'], 'setup')

    def test_saved_party_and_session_isolation(self):
        status, _ = self.request('POST', '/api/start', {'names': ['Sunny', 'River']})
        self.assertEqual(status, 200)
        original_cookie = self.cookie
        self.assertTrue(server.DB.exists())
        status, data = self.request('GET', '/api/game')
        self.assertEqual(json.loads(data)['game']['players'][0]['name'], 'Sunny')
        self.cookie = None
        _, data = self.request('GET', '/api/game')
        self.assertEqual(json.loads(data)['game']['phase'], 'setup')
        self.assertNotEqual(self.cookie, original_cookie)

    def test_invalid_body_and_early_move_do_not_change_state(self):
        for body in [[], 'wrong', None]:
            status, _ = self.request('POST', '/api/spin', body)
            self.assertEqual(status, 400)
        _, data = self.request('GET', '/api/game')
        self.assertEqual(json.loads(data)['game']['phase'], 'setup')

    def test_launch_from_other_working_directory(self):
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        result = subprocess.run([sys.executable, str(server.ROOT / 'server.py'), '--help'], cwd=self.temp.name, env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--open', result.stdout)
        self.assertIn('--data-dir', result.stdout)


if __name__ == '__main__':
    unittest.main()

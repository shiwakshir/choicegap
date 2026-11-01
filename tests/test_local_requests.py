"""Reject browser cross-origin writes and DNS rebinding before any model call or data read."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from choicegap.server import Handler


class LocalRequestTests(unittest.TestCase):
    def handler(self, **headers):
        handler = object.__new__(Handler)
        handler.server = SimpleNamespace(server_port=8000)
        handler.headers = {'Host': '127.0.0.1:8000', 'Content-Type': 'application/json', **headers}
        handler._json = Mock()
        return handler

    def test_local_browser_and_command_line_requests_allowed(self):
        for host in ('127.0.0.1:8000', 'localhost:8000'):
            for origin in (None, 'http://' + host):
                headers = {'Host': host}
                if origin is not None:
                    headers['Origin'] = origin
                self.assertTrue(self.handler(**headers)._local_request(write=True))

    def test_cross_origin_and_rebinding_requests_rejected(self):
        for headers in ({'Host': 'attacker.example:8000'}, {'Origin': 'https://attacker.example'},
                        {'Origin': 'null'}, {'Sec-Fetch-Site': 'cross-site'}, {'Host': '127.0.0.1:9000'}):
            with self.subTest(headers=headers):
                handler = self.handler(**headers)
                handler._body = Mock(side_effect=AssertionError('Must not read the body'))
                handler.do_POST()
                self.assertEqual(handler._json.call_args.args[0], 403)
                handler._body.assert_not_called()
        handler = self.handler(Host='attacker.example:8000')
        handler.do_GET()
        self.assertEqual(handler._json.call_args.args[0], 403)

    def test_simple_form_and_text_requests_rejected(self):
        for content_type in ('text/plain', 'application/x-www-form-urlencoded', ''):
            handler = self.handler(**{'Content-Type': content_type})
            self.assertFalse(handler._local_request(write=True))
            self.assertEqual(handler._json.call_args.args[0], 415)

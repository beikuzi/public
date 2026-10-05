import io
import json
import socket
import unittest
from unittest.mock import patch
from image_source_tool.network import Transport, TransportError, MAX_RESPONSE, multipart, safe_link

class Response:
    def __init__(self, status=200, data=b'{"result": []}', content_type="application/json"):
        self.status, self.content_type = status, content_type
        self.data = io.BytesIO(data)
    def getheader(self, name, default=None):
        return self.content_type if name == "Content-Type" else default
    def read1(self, count):
        return self.data.read(count)

class Connection:
    response = None
    calls = []
    def __init__(self, host, address, timeout):
        self.sock = None
        self.closed = False
    def request(self, method, path, body, headers):
        self.calls.append((method, path, body, headers))
    def getresponse(self):
        return self.response
    def close(self):
        self.closed = True

class NetworkTests(unittest.TestCase):
    def setUp(self):
        Connection.calls = []
        self.patches = [
            patch("image_source_tool.network.socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('1.1.1.1',443))]),
            patch("image_source_tool.network.PinnedHTTPSConnection", Connection),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def run_response(self, response):
        Connection.response = response
        return Transport().post("trace_moe", b"pixels")

    def test_success_fixed_route(self):
        self.assertEqual(self.run_response(Response()), {"result": []})
        method, path, body, headers = Connection.calls[0]
        self.assertEqual((method, path), ("POST", "/search?anilistInfo"))
        self.assertIn(b'filename="image.png"', body)
        self.assertIn(b'name="image"', body)
        self.assertNotIn("Authorization", headers)

    def test_quotas_block_redirect_and_errors(self):
        for status, expected in [(402,"rate_limited"),(429,"rate_limited"),(401,"blocked"),(403,"blocked"),(301,"blocked"),(307,"blocked"),(413,"input_rejected"),(500,"service_error")]:
            with self.subTest(status=status):
                before = len(Connection.calls)
                with self.assertRaises(TransportError) as exc:
                    self.run_response(Response(status=status))
                self.assertEqual(exc.exception.status, expected)
                self.assertEqual(len(Connection.calls), before + 1, "must not retry or follow redirects")

    def test_json_type_size_and_shape_bounds(self):
        for response in [Response(data=b'<html>challenge</html>', content_type="text/html"), Response(data=b'not json'), Response(data=b'[]'), Response(data=b'{"a":NaN}'), Response(data=b'X' * (MAX_RESPONSE + 1))]:
            with self.assertRaises(TransportError) as exc:
                self.run_response(response)
            self.assertEqual(exc.exception.status, "invalid_response")

    def test_model_list_has_no_upload(self):
        Connection.response = Response(data=b'{"code":0,"data":[]}')
        Transport().get_models()
        method, path, body, headers = Connection.calls[0]
        self.assertEqual((method, path, body), ("GET", "/v1/model/list", None))

    def test_unsupported_provider_no_request(self):
        with self.assertRaises(TransportError):
            Transport().post("http://localhost", b"pixels")
        with self.assertRaises(TransportError):
            Transport().post("animetrace_models", b"pixels")
        self.assertEqual(Connection.calls, [])

    def test_known_secret_urls_omitted(self):
        for key in ("api_key", "access_token", "X-Amz-Signature", "session_id", "authorization", "auth", "key", "code"):
            self.assertIsNone(safe_link("https://example.com/a?"+key+"=private"))
        self.assertEqual(safe_link("https://example.com/a?id=123"), "https://example.com/a?id=123")

if __name__ == '__main__':
    unittest.main()

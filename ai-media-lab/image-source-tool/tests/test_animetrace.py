import unittest
from image_source_tool.network import TransportError
from image_source_tool.providers import choose_animetrace_model, parse_animetrace, run_provider
from image_source_tool.imaging import PreparedImage

class FakeTransport:
    def __init__(self):
        self.calls = []
        self.models = {"code": 0, "data": [{"id": "dynamic-v4", "enabled": True, "default": True}]}
    def get_models(self):
        self.calls.append("models")
        return self.models
    def post(self, provider, image, fields):
        self.calls.append((provider, image, fields))
        return {"code": 0, "data": [{"box": [0, 0, 1, 1], "not_confident": True, "character": [{"work": "Synthetic work", "character": "Synthetic character"}]}]}

class AnimeTraceTests(unittest.TestCase):
    def test_no_network_without_consent(self):
        transport = FakeTransport()
        row = run_provider("animetrace", PreparedImage({}, b'pixels'), ["animetrace"], [], transport)
        self.assertEqual(row["status"], "consent_required")
        self.assertEqual(transport.calls, [])

    def test_dynamic_enabled_default_model_and_no_ai_detection(self):
        transport = FakeTransport()
        row = run_provider("animetrace", PreparedImage({}, b'pixels'), ["animetrace"], ["animetrace"], transport)
        self.assertEqual(row["status"], "matches")
        self.assertEqual(transport.calls[0], "models")
        self.assertEqual(transport.calls[1][2], {"model": "dynamic-v4", "is_multi": "1", "ai_detect": "0"})
        candidate = row["candidates"][0]
        self.assertIsNone(candidate["native_score"]["value"])
        self.assertTrue(candidate["provider_not_confident"])
        self.assertNotIn("ai", candidate)

    def test_missing_disabled_or_unsafe_default_no_upload(self):
        for model in [{"id":"x","enabled":False,"default":True}, {"id":"x","enabled":True,"default":False}, {"id":"a\r\ninjection","enabled":True,"default":True}]:
            transport = FakeTransport()
            transport.models["data"] = [model]
            row = run_provider("animetrace", PreparedImage({}, b'pixels'), ["animetrace"], ["animetrace"], transport)
            self.assertIn(row["status"], {"service_error", "invalid_response"})
            self.assertEqual(transport.calls, ["models"])

    def test_documented_success_codes_and_error(self):
        for code in (0, 200, 17720):
            self.assertEqual(parse_animetrace({"code":code,"data":[]}, "x")["status"], "no_match")
        self.assertEqual(parse_animetrace({"code": 500}, "x")["status"], "service_error")
        self.assertEqual(parse_animetrace({"code":0,"data":"bad"}, "x")["status"], "invalid_response")

if __name__ == '__main__':
    unittest.main()

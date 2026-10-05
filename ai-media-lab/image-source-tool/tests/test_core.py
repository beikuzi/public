import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image, PngImagePlugin
from image_source_tool.imaging import InputError, prepare_image
from image_source_tool.network import Transport, TransportError, canonical_link, safe_link
from image_source_tool.providers import parse_trace, parse_saucenao, run_provider
from image_source_tool.report import build_report, render_html, write_reports
from image_source_tool.cli import main


class FakeTransport:
    def __init__(self, response=None, error=None):
        self.calls = []
        self.response = response or {"result": []}
        self.error = error
    def post(self, provider, image, fields):
        self.calls.append((provider, image, fields))
        if self.error:
            raise self.error
        return self.response


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "private-name.png"
        image = Image.new("RGB", (32, 24), "red")
        meta = PngImagePlugin.PngInfo()
        meta.add_text("private-location", "sensitive marker")
        image.save(self.path, pnginfo=meta)
        self.prepared = prepare_image(self.path)

    def test_strips_metadata_and_filename(self):
        result = self.prepared
        self.assertTrue(result.info["metadata_present"])
        self.assertNotIn(b"sensitive", result.upload)
        self.assertNotIn(b"private-name", result.upload)
        with Image.open(io.BytesIO(result.upload)) as image:
            self.assertEqual(image.info, {})
            self.assertEqual(len(image.getexif()), 0)
        self.assertEqual(len(result.info["sha256"]), 64)

    def test_no_network_by_default_or_without_consent(self):
        transport = FakeTransport()
        self.assertEqual(run_provider("trace_moe", self.prepared, [], [], transport)["status"], "not_requested")
        self.assertEqual(run_provider("trace_moe", self.prepared, ["trace_moe"], [], transport)["status"], "consent_required")
        self.assertEqual(transport.calls, [])

    def test_consent_is_provider_specific(self):
        transport = FakeTransport()
        result = run_provider("saucenao", self.prepared, ["saucenao"], ["trace_moe"], transport)
        self.assertEqual(result["status"], "consent_required")
        self.assertEqual(transport.calls, [])

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_key(self):
        transport = FakeTransport()
        result = run_provider("saucenao", self.prepared, ["saucenao"], ["saucenao"], transport)
        self.assertEqual(result["status"], "missing_credentials")
        self.assertEqual(transport.calls, [])

    def test_upload_is_sanitized(self):
        transport = FakeTransport()
        result = run_provider("trace_moe", self.prepared, ["trace_moe"], ["trace_moe"], transport)
        self.assertEqual(result["status"], "no_match")
        self.assertEqual(transport.calls[0][1], self.prepared.upload)
        self.assertNotEqual(transport.calls[0][1], self.path.read_bytes())

    def test_failure_status_preserved(self):
        for state in ("blocked", "rate_limited", "network_error", "service_error"):
            t = FakeTransport(error=TransportError(state, "bounded error"))
            self.assertEqual(run_provider("trace_moe", self.prepared, ["trace_moe"], ["trace_moe"], t)["status"], state)

    def test_trace_native_score_and_no_artist_claim(self):
        row = parse_trace({"result": [{"anilist": {"id": 1, "title": {"romaji": "Example"}}, "similarity": .89, "episode": 2, "from": 12.0}]})
        candidate = row["candidates"][0]
        self.assertEqual(candidate["native_score"]["range"], [0, 1])
        self.assertIn("usually wrong", candidate["caution"])
        self.assertNotIn("reported_artist", candidate)
        report = build_report(self.prepared, [row])
        self.assertTrue(all(v["status"] == "unresolved" for v in report["conclusions"].values()))

    def test_sauce_source_fields_and_bad_links(self):
        row = parse_saucenao({"header": {"status": 0, "short_remaining": 2}, "results": [{"header": {"similarity": "93.2", "index_name": "test index"}, "data": {"member_name": "Artist?", "ext_urls": ["javascript:alert(1)", "http://127.0.0.1/test", "https://www.pixiv.net/artworks/123"], "pixiv_id": 123}}]})
        candidate = row["candidates"][0]
        self.assertEqual(candidate["native_score"]["range"], [0, 100])
        self.assertEqual(candidate["links"], ["https://www.pixiv.net/artworks/123"])
        self.assertEqual(candidate["evidence_status"], "unverified_candidate")

    def test_malformed_payloads(self):
        self.assertEqual(parse_trace({})["status"], "invalid_response")
        self.assertEqual(parse_trace({"result": [{}]})["status"], "invalid_response")
        self.assertEqual(parse_trace({"error": "internal error"})["status"], "service_error")
        self.assertEqual(parse_saucenao({})["status"], "invalid_response")
        self.assertEqual(parse_saucenao({"header": {"status": -1, "long_remaining": 0}})["status"], "rate_limited")
        row = parse_trace({"result": [{"anilist": 1, "similarity": float("nan")}]})
        self.assertIsNone(row["candidates"][0]["native_score"]["value"])
        json.dumps(row, allow_nan=False)
        huge = 10 ** 400
        extreme = parse_trace({"result": [{"anilist": 1, "similarity": huge, "from": huge}]})
        self.assertIsNone(extreme["candidates"][0]["native_score"]["value"])
        self.assertEqual(extreme["candidates"][0]["time_seconds"], {})

    def test_url_validation(self):
        bad = ["file:///etc/passwd", "javascript:alert(1)", "https://user:secret@example.com", "http://localhost/", "http://127.0.0.1/", "http://127.1/", "http://2130706433/", "http://[::1]/", "https://example.com:444/", "https://example.com\\@127.0.0.1/", "https://example.com/\nfoo", "http://192.168.1.2/"]
        for link in bad:
            self.assertIsNone(safe_link(link), link)
        self.assertEqual(canonical_link("https://example.com/a?utm_source=x&id=1#test"), "https://example.com/a?id=1")

    def test_report_escapes_and_private_permissions(self):
        row = parse_trace({"result": [{"anilist": {"id": 1, "title": {"romaji": "<script>alert('x')</script>"}}, "similarity": .91}]})
        report = build_report(self.prepared, [row])
        html = render_html(report)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<img", html)
        self.assertNotIn("private-name", html)
        output = Path(self.tmp.name) / "out"
        write_reports(report, output)
        if os.name == "posix":
            self.assertEqual((output / "report.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads((output / "report.json").read_text())["schema_version"], "1.0")

    def test_duplicate_link_is_single_lead(self):
        row = parse_trace({"result": [{"anilist": 1, "similarity": .95}, {"anilist": 1, "similarity": .96}]})
        report = build_report(self.prepared, [row])
        self.assertEqual(len(report["lead_groups"]), 1)
        self.assertEqual(len(report["lead_groups"][0]["candidate_ids"]), 2)

    def test_invalid_animated_and_oversized_inputs(self):
        path = Path(self.tmp.name) / "bad.jpg"
        path.write_text("not a picture")
        with self.assertRaises(InputError):
            prepare_image(path)
        with self.assertRaises(InputError):
            prepare_image(self.path, 9999)
        animated = Path(self.tmp.name) / "animated.png"
        Image.new("RGB", (8, 8), "red").save(animated, save_all=True, append_images=[Image.new("RGB", (8, 8), "blue")])
        with self.assertRaises(InputError):
            prepare_image(animated)
        with patch("image_source_tool.imaging.MAX_FILE_BYTES", 1):
            with self.assertRaises(InputError):
                prepare_image(self.path)

    @patch("image_source_tool.network.socket.getaddrinfo", return_value=[(None,None,None,None,("127.0.0.1",443))])
    def test_transport_rejects_private_dns(self, _):
        with self.assertRaises(TransportError) as caught:
            Transport().post("trace_moe", b"safe")
        self.assertEqual(caught.exception.status, "blocked")

    @unittest.skipUnless(os.name == "posix", "POSIX mode and symlink test; Windows requires user directory ACLs")
    def test_private_output_directory_and_symlinks(self):
        report = build_report(self.prepared, [])
        output = Path(self.tmp.name) / "shared"
        output.mkdir(mode=0o755)
        output.chmod(0o755)
        with self.assertRaises(OSError):
            write_reports(report, output)
        target = Path(self.tmp.name) / "private-target"
        target.mkdir(mode=0o700)
        link = Path(self.tmp.name) / "symlink"
        link.symlink_to(target)
        with self.assertRaises(OSError):
            write_reports(report, link)
        self.assertFalse((target / "report.json").exists())

    @patch.dict(os.environ, {"SAUCENAO_API_KEY": "TEST_ONLY_NOT_A_REAL_KEY"})
    def test_echoed_key_redacted(self):
        transport = FakeTransport({"header": {"status": 0}, "results": [{"header": {"similarity": "90"}, "data": {"member_name": "TEST_ONLY_NOT_A_REAL_KEY", "ext_urls": ["https://example.com/TEST_ONLY_NOT_A_REAL_KEY"]}}]})
        row = run_provider("saucenao", self.prepared, ["saucenao"], ["saucenao"], transport)
        self.assertNotIn("TEST_ONLY_NOT_A_REAL_KEY", json.dumps(row))

    def test_cli_offline(self):
        with patch("image_source_tool.network.Transport.post", side_effect=AssertionError("unexpected network")):
            self.assertEqual(main([str(self.path), "--output", str(Path(self.tmp.name) / "cli")]), 0)
            self.assertEqual(main([str(self.path), "--providers", "trace_moe", "--output", str(Path(self.tmp.name) / "consent")]), 1)

if __name__ == "__main__":
    unittest.main()

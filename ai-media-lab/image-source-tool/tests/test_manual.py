import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from image_source_tool.cli import main
from image_source_tool.imaging import InputError, prepare_image
from image_source_tool.manual import load_manual_records, parse_manual_records
from image_source_tool.report import build_report, render_html

HASH = "a" * 64

def sample(provider="ascii2d", method="color", status="matches"):
    return {"schema_version": "1.0", "image_sha256": HASH, "searches": [{
        "provider": provider, "method": method, "status": status,
        "searched_at": "2026-10-05T00:00:00+00:00", "upload_state": "submitted",
        "candidates": [{"title": "Synthetic example", "reported_artist": "Unverified name", "links": ["https://example.com/art/123"], "rank": 1}] if status == "matches" else [],
    }]}

class ManualTests(unittest.TestCase):
    def test_ascii_rank_is_not_probability(self):
        rows = parse_manual_records(sample(), HASH)
        row, candidate = rows[0], rows[0]["candidates"][0]
        self.assertEqual(row["execution_mode"], "manual_record")
        self.assertEqual(candidate["native_rank"], 1)
        self.assertIsNone(candidate["native_score"]["value"])
        self.assertEqual(candidate["evidence_status"], "unverified_manual_candidate")
        self.assertIn("No upload", row["message"])

    def test_sauce_similarity_is_native_only(self):
        payload = sample("saucenao", "browser")
        payload["searches"][0]["candidates"][0]["similarity"] = "94.3"
        candidate = parse_manual_records(payload, HASH)[0]["candidates"][0]
        self.assertEqual(candidate["native_score"]["value"], 94.3)
        self.assertEqual(candidate["native_score"]["range"], [0,100])
        payload["searches"][0]["candidates"][0]["similarity"] = 10 ** 400
        with self.assertRaises(InputError):
            parse_manual_records(payload, HASH)

    def test_hash_binding(self):
        with self.assertRaises(InputError):
            parse_manual_records(sample(), "b" * 64)

    def test_blocked_not_submitted_is_not_no_match(self):
        payload = sample(status="blocked")
        payload["searches"][0]["upload_state"] = "not_submitted"
        row = parse_manual_records(payload, HASH)[0]
        self.assertEqual(row["status"], "blocked")
        self.assertEqual(row["upload_state"], "not_submitted")
        self.assertEqual(row["candidates"], [])

    def test_rejects_inconsistent_outcomes(self):
        payloads = []
        p = sample(); p["searches"][0]["candidates"] = []; payloads.append(p)
        p = sample(status="no_match"); p["searches"][0]["upload_state"] = "unknown"; payloads.append(p)
        p = sample(); p["searches"][0]["status"] = "blocked"; payloads.append(p)
        p = sample(); p["searches"].append(copy.deepcopy(p["searches"][0])); payloads.append(p)
        for payload in payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(InputError):
                    parse_manual_records(payload,HASH)

    def test_rejects_unsafe_urls_and_fake_ascii_scores(self):
        for bad in ("http://127.0.0.1/", "javascript:alert(1)", "https://example.com/?token=SECRET"):
            payload = sample(); payload["searches"][0]["candidates"][0]["links"] = [bad]
            with self.assertRaises(InputError):
                parse_manual_records(payload,HASH)
        payload=sample(); payload["searches"][0]["candidates"][0]["similarity"]=99
        with self.assertRaises(InputError):
            parse_manual_records(payload,HASH)

    def test_schema_strictness_and_bounds(self):
        payloads=[]
        p=sample(); p["raw_html"]="private"; payloads.append(p)
        p=sample(); p["searches"][0]["searched_at"]="2026-10-05T00:00:00"; payloads.append(p)
        p=sample(); p["searches"][0]["provider"]=[]; payloads.append(p)
        p=sample(); p["searches"][0]["candidates"][0]["title"]="x"*501; payloads.append(p)
        p=sample(); p["searches"][0]["candidates"][0]["rank"]=True; payloads.append(p)
        for payload in payloads:
            with self.assertRaises(InputError):
                parse_manual_records(payload,HASH)

    def test_all_failure_states_preserved(self):
        for status in ("blocked","rate_limited","network_error","service_error","no_match"):
            row=parse_manual_records(sample(status=status),HASH)[0]
            self.assertEqual(row["status"],status)

    def test_local_file_limits_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"records.json"
            path.write_text('{"schema_version":"1.0","schema_version":"1.0"}')
            with self.assertRaises(InputError):
                load_manual_records(path,HASH)
            path.write_text("x"*(256*1024+1))
            with self.assertRaises(InputError):
                load_manual_records(path,HASH)

    def test_report_marks_import_and_keeps_conclusions_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            image=Path(tmp)/"synthetic.png";Image.new("RGB",(8,8),"blue").save(image)
            prepared=prepare_image(image)
            payload=sample();payload["image_sha256"]=prepared.info["sha256"]
            payload["searches"][0]["candidates"][0]["title"]="<script>unsafe()</script>"
            report=build_report(prepared,parse_manual_records(payload,prepared.info["sha256"]))
            html=render_html(report)
            self.assertIn("ascii2d · manual color",html)
            self.assertIn("manual_record_imported",html)
            self.assertIn("Recorded upload: submitted",html)
            self.assertIn("Searched at:",html)
            self.assertNotIn("<script>",html)
            self.assertTrue(all(v["status"]=="unresolved" for v in report["conclusions"].values()))

    def test_cli_import_does_not_call_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);image=root/"synthetic.png";Image.new("RGB",(8,8),"blue").save(image)
            payload=sample();payload["image_sha256"]=prepare_image(image).info["sha256"]
            record=root/"record.json";record.write_text(json.dumps(payload))
            with patch("image_source_tool.network.Transport.post",side_effect=AssertionError("network must stay off")):
                self.assertEqual(main([str(image),"--manual-results",str(record),"--output",str(root/"out")]),0)
                # Wrong-image records must fail before even an explicitly requested API upload.
                payload["image_sha256"]=HASH;record.write_text(json.dumps(payload))
                self.assertEqual(main([str(image),"--manual-results",str(record),"--providers","trace_moe","--allow-upload","trace_moe","--output",str(root/"bad")]),2)

if __name__ == '__main__':
    unittest.main()

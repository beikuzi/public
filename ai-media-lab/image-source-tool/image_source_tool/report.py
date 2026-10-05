"""Static, escaped, script-free private report. Never loads remote assets."""
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import tempfile
from .network import canonical_link, safe_link

MANUAL_ROUTES = [
    {"provider": "SauceNAO", "url": "https://saucenao.com/", "purpose": "Manual reverse-image search when a browser flow is preferred", "status": "manual_not_searched"},
    {"provider": "AnimeTrace", "url": "https://www.animetrace.com/", "purpose": "Character/work candidate identification; does not prove image authorship", "status": "manual_not_searched"},
    {"provider": "IQDB", "url": "https://iqdb.org/", "purpose": "Indexed illustration matches; often reposts", "status": "manual_not_searched"},
    {"provider": "ascii2d", "url": "https://ascii2d.net/", "purpose": "Visual illustration candidates", "status": "manual_not_searched"},
    {"provider": "Google Lens", "url": "https://lens.google/", "purpose": "Broad web visual candidates", "status": "manual_not_searched"},
    {"provider": "TinEye", "url": "https://tineye.com/", "purpose": "Duplicate/crop variants and indexed page leads", "status": "manual_not_searched"},
]


def build_report(prepared, providers):
    leads = {}
    for provider in providers:
        for candidate in provider["candidates"]:
            for link in candidate["links"]:
                canonical = canonical_link(link)
                if canonical:
                    group = leads.setdefault(canonical, {"url": canonical, "candidate_ids": [], "note": "Shared URL is one lead, not independent corroboration. Different URLs may also be reposts of the same source."})
                    if candidate["id"] not in group["candidate_ids"]:
                        group["candidate_ids"].append(candidate["id"])
    return {
        "schema_version": "1.0", "created_at": datetime.now(timezone.utc).isoformat(),
        "input": prepared.info,
        "privacy": {"original_path_stored": False, "original_image_embedded": False,
                    "metadata_stripped_before_upload": None if any(p.get("execution_mode") == "manual_record" for p in providers) else True,
                    "metadata_stripped_before_api_upload": True, "visible_content_anonymized": False,
                    "provider_response_cache": False, "remote_assets_in_report": False,
                    "manual_upload_metadata_stripping": "not_verified_by_importer"},
        "conclusions": {key: {"status": "unresolved", "reason": reason} for key, reason in {
            "character": "Character-recognition results are candidates; identity requires independent verification.",
            "work": "Provider frame or index matches are candidates, requiring visual verification.",
            "exact_image": "A first-party original post and exact-image comparison have not been verified.",
            "original_artist": "A repost or index-reported name does not establish original authorship.",
        }.items()},
        "providers": providers, "lead_groups": list(leads.values()),
        "manual_routes": [dict(route, status="manual_record_imported" if any(p.get("execution_mode") == "manual_record" and p["provider"] == route["provider"].lower() for p in providers) else route["status"]) for route in MANUAL_ROUTES],
    }


def e(value):
    return escape(str(value), quote=True)


def anchor(url, label=None):
    url = safe_link(url)
    if not url:
        return ""
    return f'<a href="{e(url)}" rel="noreferrer noopener" target="_blank">{e(label or url)}</a>'


def render_html(report):
    cards = []
    for provider in report["providers"]:
        rows = []
        for candidate in provider["candidates"]:
            score = candidate["native_score"]
            details = []
            for key in ("character", "work", "title", "episode", "reported_artist", "index"):
                if candidate.get(key):
                    details.append(f'<dt>{e(key.replace("_", " "))}</dt><dd>{e(candidate[key])}</dd>')
            if candidate.get("native_rank"):
                details.append(f'<dt>Native result rank</dt><dd>{e(candidate["native_rank"])} (not a score)</dd>')
            if candidate.get("time_seconds"):
                details.append(f'<dt>Time (seconds)</dt><dd>{e(json.dumps(candidate["time_seconds"]))}</dd>')
            score_label = f'Native similarity {score["value"]} / {score["range"][1]}' if score["range"] else "No numerical score supplied"
            rows.append(f'<article class="candidate"><div class="row"><strong>{e(candidate["kind"])}</strong><span>{e(score_label)}</span></div><dl>{"".join(details)}</dl><p class="muted">{e(candidate["caution"])}</p><div class="links">{"".join(anchor(link) for link in candidate["links"]) or "No safe source link returned"}</div></article>')
        label = provider["provider"] + (f' · manual {provider["method"]}' if provider.get("execution_mode") == "manual_record" else "")
        recorded = f'<p class="muted">Recorded upload: {e(provider["upload_state"])} · Recorded attempt/checkpoint: {e(provider["searched_at"])}</p>' if provider.get("execution_mode") == "manual_record" else ""
        cards.append(f'<section><div class="row"><h2>{e(label)}</h2><span class="badge">{e(provider["status"])}</span></div><p>{e(provider["message"])}</p>{recorded}{"".join(rows)}</section>')
    conclusions = "".join(f'<div><small>{e(key.replace("_", " "))}</small><strong>{e(value["status"])}</strong><p>{e(value["reason"])}</p></div>' for key, value in report["conclusions"].items())
    routes = "".join(f'<li>{anchor(route["url"], route["provider"])} · {e(route["purpose"])} <span class="muted">[{e(route["status"])}]</span></li>' for route in report["manual_routes"])
    groups = "".join(f'<li>{anchor(group["url"])} <span class="muted">{e(", ".join(group["candidate_ids"]))}</span></li>' for group in report["lead_groups"])
    info = report["input"]
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; base-uri 'none'; form-action 'none'"><meta name="referrer" content="no-referrer"><title>Image source investigation</title><style>
:root{{font-family:system-ui,sans-serif;color:#e7edf5;background:#10151d;line-height:1.5}}body{{max-width:1060px;margin:0 auto;padding:32px 24px}}h1{{font-size:32px;line-height:1.1;margin:8px 0 16px}}h2{{font-size:20px;margin:0}}a{{color:#8dc7ff;overflow-wrap:anywhere}}p{{margin:8px 0}}small,.muted{{color:#a5b4c8}}.eyebrow{{letter-spacing:2px;font-size:12px;color:#89d8bd}}.row{{display:flex;justify-content:space-between;gap:16px;align-items:baseline;flex-wrap:wrap}}section,.summary{{background:#19222e;border:1px solid #344153;border-radius:12px;padding:20px;margin:20px 0}}.summary{{display:grid;grid-template-columns:repeat(2,1fr);gap:24px}}.summary strong,.summary small{{display:block}}.summary strong{{color:#f4c87b;text-transform:uppercase;letter-spacing:1px;font-size:14px}}.summary p{{font-size:13px}}.candidate{{border-top:1px solid #344153;margin-top:18px;padding-top:16px}}.badge{{font-size:12px;padding:4px 10px;border:1px solid #71829a;border-radius:20px}}dl{{display:grid;grid-template-columns:130px 1fr;gap:4px 16px}}dt{{color:#a5b4c8}}dd{{margin:0;overflow-wrap:anywhere}}.links a{{display:block}}li{{margin:10px 0}}.hash{{font:12px ui-monospace,monospace;overflow-wrap:anywhere}}footer{{font-size:12px;color:#a5b4c8;padding:12px 0}}@media(max-width:600px){{body{{padding:20px 14px}}.summary{{grid-template-columns:1fr}}dl{{grid-template-columns:1fr}}h1{{font-size:26px}}}}
</style></head><body><header><div class="eyebrow">LOCAL RESEARCH · 图片溯源</div><h1>Evidence before attribution.</h1><p>Character / work identity and exact-image / artist provenance are different questions.</p><p class="muted">{e(info["format"])} · {info["width"]} × {info["height"]} · {info["bytes"]:,} bytes · {e(report["created_at"])}</p><p class="hash">Local file SHA-256: {e(info["sha256"])}</p></header><div class="summary">{conclusions}</div>{"".join(cards)}<section><h2>Source leads</h2><p class="muted">Repeated links are grouped once. Repost chains are not independent corroboration. Native scores cannot be compared across providers.</p><ul>{groups or "<li>No source leads returned.</li>"}</ul></section><section><h2>Continue manually</h2><p>These links are manual entry points, not automated searches. Any imported browser record is labeled separately and does not mean this tool performed or verified the search.</p><ul>{routes}</ul></section><section><h2>Verification checklist</h2><ol><li>Compare the exact crop, line work, composition and edits, not only the character.</li><li>Open the candidate post; verify the account belongs to the artist and the work is credited as theirs.</li><li>Follow repost credits back to a first-party post. Earlier indexing alone does not establish authorship.</li><li>Record the original post URL and relevant evidence; leave unresolved claims unresolved.</li></ol></section><footer>The tool does not embed the original image, local filename, EXIF values, scripts or remote assets. API uploads require explicit provider permission. Imported text and prior browser uploads remain your responsibility; review reports before sharing. Provider candidates are not verified conclusions.</footer></body></html>'''


def write_private(path, content):
    path = Path(path)
    # Reject symlink output paths before writing; do not silently write elsewhere.
    for part in (path, *path.parents):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise OSError("Symlink report paths are not supported")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix" and path.parent.stat().st_mode & 0o077:
        raise OSError("Output directory must be private (mode 0700); choose a fresh directory")
    fd, name = tempfile.mkstemp(prefix=".report-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_reports(report, directory):
    directory = Path(directory)
    write_private(directory / "report.json", json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    write_private(directory / "report.html", render_html(report))

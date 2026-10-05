"""Import bounded local browser-search records; never fetch or upload anything."""
from datetime import datetime
import json
from pathlib import Path
from .imaging import InputError
from .network import safe_link
from .providers import clean_text, native_score, result

MAX_MANUAL_BYTES = 256 * 1024
ALLOWED_STATUS = {"matches", "no_match", "blocked", "rate_limited", "network_error", "service_error"}
METHODS = {"ascii2d": {"color", "bovw", "browser"}, "saucenao": {"browser"}}


def _strict_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON field")
        value[key] = item
    return value


def _keys(value, allowed, required):
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - allowed:
        raise InputError("Manual record has missing or unsupported fields; see docs/manual-results.md")


def _text(value):
    if not isinstance(value, str) or len(value) > 500:
        raise InputError("Manual candidate text must be a string of at most 500 characters")
    return clean_text(value)


def parse_manual_records(payload, image_sha256):
    _keys(payload, {"schema_version", "image_sha256", "searches"}, {"schema_version", "image_sha256", "searches"})
    if payload["schema_version"] != "1.0" or payload["image_sha256"] != image_sha256:
        raise InputError("Manual record version or image SHA-256 does not match this input")
    searches = payload["searches"]
    if not isinstance(searches, list) or not 1 <= len(searches) <= 6:
        raise InputError("Manual records require 1–6 search entries")
    rows, seen = [], set()
    for search in searches:
        fields = {"provider", "method", "status", "searched_at", "upload_state", "candidates"}
        _keys(search, fields, fields)
        provider, method, status = search["provider"], search["method"], search["status"]
        if not isinstance(provider, str) or provider not in METHODS or not isinstance(method, str) or method not in METHODS[provider]:
            raise InputError("Only Ascii2D color/bovw/browser and SauceNAO browser records are supported")
        if not isinstance(status, str) or status not in ALLOWED_STATUS:
            raise InputError("Unsupported manual search status")
        if (provider, method) in seen:
            raise InputError("Duplicate manual provider/method record")
        seen.add((provider, method))
        upload = search["upload_state"]
        if not isinstance(upload, str) or upload not in {"not_submitted", "submitted", "unknown"}:
            raise InputError("Manual record must state whether an image was submitted")
        if status in {"matches", "no_match"} and upload != "submitted":
            raise InputError("A completed manual search requires upload_state submitted")
        timestamp = search["searched_at"]
        try:
            if not isinstance(timestamp, str) or len(timestamp) > 64:
                raise ValueError()
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError()
        except ValueError as exc:
            raise InputError("Manual searched_at must be an ISO timestamp with timezone") from exc
        candidates = search["candidates"]
        if not isinstance(candidates, list) or len(candidates) > 20:
            raise InputError("Manual search supports at most 20 candidates")
        if (status == "matches") != bool(candidates):
            raise InputError("Only matches records may contain candidates, and matches requires at least one")
        normalized = []
        for index, item in enumerate(candidates):
            _keys(item, {"title", "work", "reported_artist", "links", "similarity", "rank"}, {"links"})
            links = item["links"]
            if not isinstance(links, list) or not 1 <= len(links) <= 10:
                raise InputError("Each manual candidate requires 1–10 public source links")
            safe_links = [safe_link(link) for link in links]
            if not all(safe_links):
                raise InputError("Manual source link is unsafe or contains a known credential parameter")
            score = {"value": None, "range": None, "meaning": "No numerical similarity supplied; manual ranking is not an attribution probability"}
            if "similarity" in item:
                if provider != "saucenao" or isinstance(item["similarity"], bool):
                    raise InputError("Only SauceNAO records accept its native 0–100 similarity")
                score = native_score(item["similarity"], 100)
                if score["value"] is None:
                    raise InputError("SauceNAO similarity must be a finite number between 0 and 100")
            candidate = {
                "id": f"{provider}:manual:{method}:{index+1}",
                "kind": "indexed_image_source", "evidence_status": "unverified_manual_candidate",
                "native_score": score, "links": list(dict.fromkeys(safe_links)),
                "caution": "Manually recorded browser result, not independently verified by this tool. A repost or index name does not prove original authorship.",
            }
            for key in ("title", "work", "reported_artist"):
                if key in item:
                    candidate[key] = _text(item[key])
            if "rank" in item:
                rank = item["rank"]
                if not isinstance(rank, int) or isinstance(rank, bool) or not 1 <= rank <= 1000:
                    raise InputError("Manual native rank must be an integer from 1 to 1000")
                candidate["native_rank"] = rank
            normalized.append(candidate)
        rows.append(result(provider, status,
            "Imported local browser-search record; not independently verified by this tool. No upload or link fetch occurred during import.",
            normalized, execution_mode="manual_record", method=method,
            searched_at=parsed.isoformat(), upload_state=upload,
            record_origin="user_supplied_local_file"))
    return rows


def load_manual_records(path, image_sha256):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_MANUAL_BYTES:
        raise InputError("Manual records must be a local JSON file of at most 256 KiB")
    with path.open("rb") as handle:
        data = handle.read(MAX_MANUAL_BYTES + 1)
    if len(data) > MAX_MANUAL_BYTES:
        raise InputError("Manual records exceed 256 KiB")
    try:
        payload = json.loads(data, object_pairs_hook=_strict_object,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InputError("Manual records contain invalid JSON") from exc
    return parse_manual_records(payload, image_sha256)

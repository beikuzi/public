"""Normalize provider evidence without promoting candidates into attribution."""
import math
import os
from .network import Transport, TransportError, safe_link

PROVIDERS = ("trace_moe", "saucenao", "animetrace")


def clean_text(value, limit=500):
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return "".join(c for c in str(value) if c.isprintable())[:limit]
    if isinstance(value, list):
        return "; ".join(filter(None, (clean_text(v, 100) for v in value[:10])))[:limit]
    return ""


def native_score(value, scale):
    if isinstance(value, bool):
        value = None
    try:
        value = float(value)
        if math.isfinite(value) and 0 <= value <= scale:
            return {"value": value, "range": [0, scale], "meaning": "provider similarity, not attribution probability"}
    except (TypeError, ValueError, OverflowError):
        pass
    return {"value": None, "range": [0, scale], "meaning": "score absent or invalid"}


def finite_number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def result(provider, status, message, candidates=None, **extra):
    return dict(provider=provider, status=status, message=message, candidates=candidates or [], **extra)


def parse_trace(payload):
    if payload.get("error"):
        return result("trace_moe", "service_error", "trace.moe reported an error; raw server text omitted")
    if not isinstance(payload.get("result"), list):
        return result("trace_moe", "invalid_response", "Missing trace.moe result list")
    candidates = []
    for item in payload["result"][:20]:
        if not isinstance(item, dict):
            continue
        anime = item.get("anilist")
        anime = anime if isinstance(anime, dict) else {"id": anime}
        title = anime.get("title") if isinstance(anime.get("title"), dict) else {}
        identifier = anime.get("id")
        links = []
        if isinstance(identifier, int) and not isinstance(identifier, bool) and identifier > 0:
            links.append(f"https://anilist.co/anime/{identifier}")
        if not links:
            continue
        score = native_score(item.get("similarity"), 1)
        candidates.append({
            "id": f"trace_moe:{len(candidates)+1}", "kind": "anime_frame_work",
            "evidence_status": "unverified_candidate", "native_score": score,
            "work": clean_text(title.get("english") or title.get("romaji") or title.get("native")),
            "episode": clean_text(item.get("episode")),
            "time_seconds": {k: v for k in ("from", "to", "at") if finite_number(v := item.get(k)) and v >= 0},
            "links": links,
            "caution": "Anime frame match only; does not establish character or original illustration artist."
                       + (" Official guidance warns similarities below 0.9 are usually wrong." if score["value"] is not None and score["value"] < 0.9 else ""),
        })
    if payload["result"] and not candidates:
        return result("trace_moe", "invalid_response", "Provider returned candidates without a valid work identifier")
    return result("trace_moe", "matches" if candidates else "no_match", "Candidate anime frames; verify visually and against the work" if candidates else "Provider returned no candidates", candidates)


def parse_saucenao(payload):
    header = payload.get("header")
    if not isinstance(header, dict):
        return result("saucenao", "invalid_response", "Missing SauceNAO header")
    try:
        status = int(header.get("status", -999))
    except (ValueError, TypeError):
        status = -999
    quota = {key: value for key in ("short_remaining", "long_remaining")
             if finite_number(value := header.get(key))}
    if status != 0:
        limited = any(value <= 0 for value in quota.values())
        return result("saucenao", "rate_limited" if limited else "service_error", "SauceNAO reported a quota or service error; raw server text omitted", quota=quota)
    if not isinstance(payload.get("results"), list):
        return result("saucenao", "invalid_response", "Missing SauceNAO results list", quota=quota)
    candidates = []
    for item in payload["results"][:20]:
        if not isinstance(item, dict) or not isinstance(item.get("header"), dict) or not isinstance(item.get("data"), dict):
            continue
        h, data = item["header"], item["data"]
        links = list(dict.fromkeys(link for value in (data.get("ext_urls") if isinstance(data.get("ext_urls"), list) else [])[:20] if (link := safe_link(value))))
        pixiv = str(data.get("pixiv_id", ""))
        if pixiv.isdigit() and 0 < len(pixiv) <= 20:
            link = f"https://www.pixiv.net/artworks/{pixiv}"
            if link not in links:
                links.append(link)
        artist = next((clean_text(data.get(k)) for k in ("author", "member_name", "creator", "twitter_user_handle", "author_name", "artist") if clean_text(data.get(k))), "")
        candidates.append({
            "id": f"saucenao:{len(candidates)+1}", "kind": "indexed_image_source",
            "evidence_status": "unverified_candidate", "native_score": native_score(h.get("similarity"), 100),
            "title": clean_text(data.get("title")), "work": clean_text(data.get("material")),
            "reported_artist": artist, "index": clean_text(h.get("index_name")),
            "links": links, "caution": "Index attribution may name an uploader or repost. Verify first-party authorship and exact pixels.",
        })
    return result("saucenao", "matches" if candidates else "no_match", "Indexed-image candidates; verify original posts and author identity" if candidates else "Provider returned no candidates", candidates, quota=quota)


def choose_animetrace_model(payload):
    if isinstance(payload.get("code"), bool) or payload.get("code") not in (0, 200, 17720) or not isinstance(payload.get("data"), list):
        raise TransportError("invalid_response", "AnimeTrace model list is unavailable or malformed; no image uploaded")
    enabled = [item for item in payload["data"][:100] if isinstance(item, dict) and item.get("enabled") is True]
    default = next((item for item in enabled if item.get("default") is True), None)
    if not default:
        raise TransportError("service_error", "AnimeTrace has no enabled default model; no image uploaded")
    identifier = default.get("id")
    if not isinstance(identifier, (str, int)) or isinstance(identifier, bool):
        raise TransportError("invalid_response", "AnimeTrace returned an invalid model identifier; no image uploaded")
    identifier = str(identifier)
    if not identifier or len(identifier) > 100 or not all(c.isascii() and (c.isalnum() or c in "_-.:") for c in identifier):
        raise TransportError("invalid_response", "AnimeTrace returned an unsafe model identifier; no image uploaded")
    return identifier


def parse_animetrace(payload, model):
    if isinstance(payload.get("code"), bool) or payload.get("code") not in (0, 200, 17720):
        return result("animetrace", "service_error", "AnimeTrace reported a service error; raw server text omitted", model=model)
    if not isinstance(payload.get("data"), list):
        return result("animetrace", "invalid_response", "Missing AnimeTrace data list", model=model)
    candidates = []
    for region in payload["data"][:20]:
        if not isinstance(region, dict) or not isinstance(region.get("character"), list):
            continue
        box = region.get("box")
        box = box if isinstance(box, list) and len(box) == 4 and all(finite_number(v) for v in box) else None
        for character in region["character"][:10]:
            if not isinstance(character, dict):
                continue
            name, work = clean_text(character.get("character")), clean_text(character.get("work"))
            if not name and not work:
                continue
            candidates.append({
                "id": f"animetrace:{len(candidates)+1}", "kind": "character_work",
                "evidence_status": "unverified_candidate",
                "native_score": {"value": None, "range": None, "meaning": "Provider does not return a calibrated numerical score"},
                "character": name, "work": work, "region_box": box,
                "provider_not_confident": region.get("not_confident") if isinstance(region.get("not_confident"), bool) else None,
                "links": [],
                "caution": "Character/work recognition only. Does not identify the image's original creator."
                           + (" Provider explicitly marked this region not confident." if region.get("not_confident") is True else ""),
            })
    return result("animetrace", "matches" if candidates else "no_match", "Experimental character/work candidates; verify identity visually" if candidates else "Provider returned no character candidates", candidates, model=model)


def run_provider(provider, prepared, requested, consent, transport=None):
    if provider not in requested:
        return result(provider, "not_requested", "No network request made")
    if provider not in consent:
        return result(provider, "consent_required", f"Add --allow-upload {provider} to permit sanitized image upload to this provider")
    fields = {}
    if provider == "saucenao":
        key = os.environ.get("SAUCENAO_API_KEY", "").strip()
        if not key:
            return result(provider, "missing_credentials", "Set an existing SAUCENAO_API_KEY in your environment; no request made")
        if len(key) > 512 or any(c in key for c in "\r\n"):
            return result(provider, "missing_credentials", "SAUCENAO_API_KEY has an invalid format; no request made")
        fields = {"api_key": key, "output_type": "2", "db": "999", "numres": "10"}
    try:
        transport = transport or Transport()
        if provider == "animetrace":
            model = choose_animetrace_model(transport.get_models())
            payload = transport.post(provider, prepared.upload, {"model": model, "is_multi": "1", "ai_detect": "0"})
            return parse_animetrace(payload, model)
        payload = transport.post(provider, prepared.upload, fields)
        parsed = (parse_trace if provider == "trace_moe" else parse_saucenao)(payload)
        # Defense in depth: even a provider that echoed a credential cannot write it to a report.
        if provider == "saucenao":
            parsed = redact_secret(parsed, key)
        return parsed
    except TransportError as exc:
        return result(provider, exc.status, exc.message)


def redact_secret(value, secret):
    if isinstance(value, str):
        return value.replace(secret, "[redacted]")
    if isinstance(value, list):
        return [redact_secret(item, secret) for item in value]
    if isinstance(value, dict):
        return {key: redact_secret(item, secret) for key, item in value.items()}
    return value

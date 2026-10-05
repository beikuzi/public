import hashlib
import json
import re
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from .providers import TranslationError
from .storage import private_dir, private_file

# Common UE format fields, printf fields, rich text tags, escapes and real line breaks.
# Nested ICU/plural expressions are unsupported and conservatively skipped below.
PROTECTED = re.compile(r"\{[^{}\r\n]*\}|%(?:\d+\$)?[-+#0 ]*\d*(?:\.\d+)?[hlL]*[diuoxXfFeEgGaAcspn%]|<[^>\r\n]+>|\\[nrt]|\r\n|\r|\n")
TOKEN = re.compile(r"ZXQKEEP[0-9a-f]+N\d+QXZ")


def protect(text):
    nonce = secrets.token_hex(6)
    values = []
    def replace(match):
        values.append(match.group())
        return f"ZXQKEEP{nonce}N{len(values)-1}QXZ"
    return PROTECTED.sub(replace, text), values, nonce


def restore(text, values, nonce):
    expected = [f"ZXQKEEP{nonce}N{i}QXZ" for i in range(len(values))]
    if TOKEN.findall(text) != expected:
        raise TranslationError("Provider changed protected tokens; original text retained")
    for token, value in zip(expected, values):
        text = text.replace(token, value)
    return text


def skippable(text):
    residue = PROTECTED.sub("", text)
    return not any(c.isalpha() for c in residue) or "ZXQKEEP" in text or "{" in residue or "}" in residue


class Engine:
    def __init__(self, config, provider, runtime, allow_remote=False):
        self.config, self.provider = config, provider
        self.allow_remote = allow_remote
        self.source = config.get("source", "auto")
        self.target = config.get("target", "zh")
        for name in ("source", "target"):
            if not isinstance(getattr(self, name), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,30}", getattr(self, name)):
                raise TranslationError("Invalid language identifier")
        self.max_chars = self.limit("max_chars_per_text", 1000, 1, 10000)
        if self.target == "auto":
            raise TranslationError("Target language cannot be auto")
        self.cache = {}
        self.daily_chars = self.limit("daily_character_limit", 10000, 1, 1000000)
        self.daily_calls = self.limit("daily_request_limit", 100, 1, 10000)
        self.interval = self.limit("request_interval_seconds", 1.1, 1.0, 60)
        private_dir(runtime)
        budget_path = private_file(Path(runtime) / "usage.sqlite3")
        self.db = sqlite3.connect(str(budget_path))
        private_file(budget_path)
        
        self.db.execute("CREATE TABLE IF NOT EXISTS budget (day TEXT PRIMARY KEY, chars INTEGER, calls INTEGER)")
        self.last_call = 0

    def limit(self, name, default, low, high):
        value = self.config.get(name, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise TranslationError("Invalid bounded setting: " + name)
        return value

    def close(self):
        self.db.close()

    def reserve(self, count):
        day = datetime.now(timezone.utc).date().isoformat()
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO budget VALUES (?,0,0)", (day,))
            cursor = self.db.execute("UPDATE budget SET chars=chars+?, calls=calls+1 WHERE day=? AND chars+?<=? AND calls+1<=?",
                (count, day, count, self.daily_chars, self.daily_calls))
            if cursor.rowcount != 1:
                raise TranslationError("Local daily budget exhausted; original text retained")

    def translate(self, text):
        if not isinstance(text, str) or len(text) > self.max_chars:
            raise TranslationError("Text is invalid or exceeds configured character limit")
        if skippable(text):
            return text, "skipped"
        key = hashlib.sha256(json.dumps([self.provider.namespace, self.source, self.target, text], ensure_ascii=False).encode()).hexdigest()
        if key in self.cache:
            return self.cache[key], "cache"
        if self.provider.remote and not self.allow_remote:
            raise TranslationError("Remote translation disabled; pass --allow-remote after reviewing data and cost")
        stripped = text.strip()
        start = len(text) - len(text.lstrip())
        end = len(text.rstrip())
        masked, values, nonce = protect(stripped)
        if len(masked.encode("utf-8")) > 5500:
            raise TranslationError("Protected request exceeds safe provider byte limit")
        if self.provider.remote:
            # Count masked payload, not original text. Reservations include failed requests.
            self.reserve(len(masked))
            time.sleep(max(0, self.interval - (time.monotonic() - self.last_call)))
            self.last_call = time.monotonic()
        translated = self.provider.translate(masked, self.source, self.target)
        if not isinstance(translated, str) or not translated.strip() or len(translated) > 20000:
            raise TranslationError("Provider returned invalid text")
        result = text[:start] + restore(translated.strip(), values, nonce) + text[end:]
        # Any additional unprotected line break or format field is suspicious.
        if PROTECTED.findall(result) != PROTECTED.findall(text):
            raise TranslationError("Provider changed formatting; original text retained")
        if len(self.cache) >= 10000:
            self.cache.clear()
        self.cache[key] = result
        return result, "translated"

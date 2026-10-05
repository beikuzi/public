import argparse
import hashlib
import json
import os
import re
import secrets
import sys
import time
from pathlib import Path
from .core import Engine
from .providers import TranslationError, make_provider, BaiduProvider
from .storage import private_dir, private_file

MAX_FILE_BYTES = 262144
ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


def atomic_json(path, data):
    private_file(path)
    temporary = private_file(path.with_suffix(".tmp"))
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    private_file(temporary)
    os.replace(temporary, path)


def process_request(engine, request):
    if not isinstance(request, dict) or request.get("version") != 1:
        raise TranslationError("Invalid protocol version")
    texts = request.get("texts")
    if not isinstance(texts, list) or not 1 <= len(texts) <= 64:
        raise TranslationError("Expected 1..64 texts")
    rows, seen, ids = [], {}, set()
    for item in texts:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not ID.fullmatch(item["id"]) or item["id"] in ids or not isinstance(item.get("text"), str):
            raise TranslationError("Invalid or duplicate text id")
        ids.add(item["id"])
    for item in texts:
        original = item["text"]
        if original not in seen:
            try:
                text, status = engine.translate(original)
                seen[original] = {"text": text, "status": status}
            except TranslationError as exc:
                seen[original] = {"text": original, "status": "error", "error": str(exc)}
        rows.append({"id": item["id"], "original_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(), **seen[original]})
    return {"version": 1, "results": rows}


def drain(engine, runtime):
    if isinstance(engine.provider, BaiduProvider):
        raise TranslationError("Baidu file-queue output is disabled pending service retention terms review; use an approved memory-only client")
    inbox, outbox = runtime / "inbox", runtime / "outbox"
    private_dir(inbox)
    private_dir(outbox)
    count = 0
    for file in sorted(inbox.glob("*.json"))[:100]:
        if file.is_symlink() or not ID.fullmatch(file.stem):
            continue
        destination = outbox / file.name
        try:
            if file.stat().st_size > MAX_FILE_BYTES:
                raise TranslationError("Request file too large")
            request = json.loads(file.read_text(encoding="utf-8"))
            result = process_request(engine, request)
        except (UnicodeError, ValueError, TranslationError):
            result = {"version": 1, "error": "Invalid request; no translation performed"}
        atomic_json(destination, result)
        file.unlink()
        count += 1
    return count


def serve(engine, runtime, port):
    from http.server import BaseHTTPRequestHandler, HTTPServer
    token = secrets.token_urlsafe(32)
    token_file = private_file(runtime / "local-token.txt")
    fd = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(token)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.connection.settimeout(20)
            if self.path != "/v1/chat/completions" or self.headers.get("Origin"):
                self.reply(404, {"error": "Unsupported request"})
                return
            auth = self.headers.get("Authorization", "")
            if not secrets.compare_digest(auth, "Bearer " + token):
                self.reply(401, {"error": "Unauthorized"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 1 <= size <= MAX_FILE_BYTES:
                    raise ValueError()
                body = json.loads(self.rfile.read(size))
                messages = body["messages"]
                users = [m["content"] for m in messages if m.get("role") == "user"]
                if len(users) != 1 or not isinstance(users[0], str):
                    raise ValueError()
                text = users[0]
                prefix = "\n\nText to translate:\n"
                if text.startswith("Translate the following text ") and prefix in text:
                    wrapper, text = text.split(prefix, 1)
                    if not wrapper.endswith(". Preserve any formatting, special characters, and placeholders like {0}, %s, etc. Only output the translation, nothing else."):
                        raise ValueError()
                translated, _ = engine.translate(text)
                self.reply(200, {"choices": [{"message": {"role": "assistant", "content": translated}, "finish_reason": "stop"}]})
            except (ValueError, TypeError, KeyError, AttributeError, TranslationError):
                self.reply(422, {"error": "Translation unavailable; keep original text"})

        def reply(self, code, body):
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"Local adapter: http://127.0.0.1:{port}/v1/chat/completions")
    print("Session token written to runtime/local-token.txt. Treat it as private; expires when process exits.")
    try:
        server.serve_forever()
    finally:
        server.server_close()
        token_file.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Experimental Unreal translation bridge; no game injection")
    parser.add_argument("--config", default="config.example.json")
    parser.add_argument("--runtime", default="runtime")
    parser.add_argument("--allow-remote", action="store_true", help="Allow game text to leave this computer and incur provider usage charges")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Process current file queue and exit")
    mode.add_argument("--serve", action="store_true", help="Opt-in authenticated 127.0.0.1 HTTP adapter")
    parser.add_argument("--port", type=int, default=18765)
    args = parser.parse_args()
    runtime = private_dir(args.runtime)
    lock = runtime / "worker.lock"
    acquired = False
    engine = None
    try:
        lock.mkdir()
        acquired = True
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        if not isinstance(config, dict) or any("key" in key.lower() or "secret" in key.lower() for key in config):
            raise TranslationError("Configuration must be an object without credential fields")
        provider = make_provider(config)
        engine = Engine(config, provider, runtime, args.allow_remote)
        if args.serve:
            serve(engine, runtime, args.port)
        else:
            while True:
                processed = drain(engine, runtime)
                if args.once:
                    print(f"Processed {processed} request file(s)")
                    break
                time.sleep(0.25)
    except FileExistsError:
        print("Worker already active, or stale runtime/worker.lock. Verify no worker is running before removing lock.", file=sys.stderr)
        return 2
    except (OSError, ValueError, TranslationError) as exc:
        # Never print raw OS paths/URLs or third-party responses.
        print(str(exc) if isinstance(exc, TranslationError) else "Bridge stopped: check configuration and runtime access", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        pass
    finally:
        if engine:
            engine.close()
        if acquired:
            lock.rmdir()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Small fixed-endpoint HTTPS transport. No redirects, proxy env or arbitrary URL fetch."""
import http.client
import ipaddress
import re
import json
import socket
import ssl
import uuid
import time
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

MAX_RESPONSE = 2 * 1024 * 1024
TIMEOUT = 20
ENDPOINTS = {
    "trace_moe": ("api.trace.moe", "/search?anilistInfo"),
    "saucenao": ("saucenao.com", "/search.php"),
    "animetrace": ("api.animetrace.com", "/v1/search"),
    "animetrace_models": ("api.animetrace.com", "/v1/model/list"),
}

class TransportError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


def public_ip(value):
    try:
        addr = ipaddress.ip_address(value)
        return addr.is_global and not addr.is_multicast
    except ValueError:
        return False


def safe_link(value):
    """Sanitize a displayed link, not permission to fetch it. DNS is not resolved here."""
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 33 for c in value):
        return None
    try:
        u = urlsplit(value)
        if u.scheme not in {"http", "https"} or not u.hostname or u.username or u.password:
            return None
        host = u.hostname.lower().rstrip(".")
        if u.port not in {None, 80, 443} or "\\" in value:
            return None
        if host == "localhost" or "." not in host or host.endswith((".local", ".localhost", ".internal", ".test", ".invalid")):
            return None
        try:
            ipaddress.ip_address(host)
            if not public_ip(host):
                return None
        except ValueError:
            # Numeric alternative encodings such as 2130706433/127.1 are not links.
            if host.replace(".", "").isdigit() or not all(c.isalnum() or c in ".-" for c in host):
                return None
        for key, _ in parse_qsl(u.query, keep_blank_values=True):
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if any(part in normalized for part in ("token", "secret", "password", "passwd", "credential", "signature", "apikey", "authorization", "session", "jwt")) or normalized in {"key", "auth", "sig", "code"} or normalized.startswith(("xamz", "xgoog")):
                return None
        return urlunsplit((u.scheme, u.netloc, u.path, u.query, ""))
    except (ValueError, UnicodeError):
        return None


def canonical_link(value):
    cleaned = safe_link(value)
    if not cleaned:
        return None
    u = urlsplit(cleaned)
    query = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
    return urlunsplit((u.scheme, u.netloc.lower(), u.path, urlencode(query), ""))


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a prevalidated public IP while retaining original TLS hostname."""
    def __init__(self, host, address, timeout):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def multipart(fields, image_field, data):
    boundary = "image-source-" + uuid.uuid4().hex
    chunks = []
    for key, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    chunks.extend([
        f'--{boundary}\r\nContent-Disposition: form-data; name="{image_field}"; filename="image.png"\r\nContent-Type: image/png\r\n\r\n'.encode(),
        data, f'\r\n--{boundary}--\r\n'.encode(),
    ])
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


class Transport:
    def post(self, provider, image, fields=None):
        if provider not in {"trace_moe", "saucenao", "animetrace"}:
            raise TransportError("blocked", "Unknown upload provider endpoint")
        body, content_type = multipart(fields or {}, "image" if provider == "trace_moe" else "file", image)
        return self._request(provider, "POST", body, content_type)

    def get_models(self):
        return self._request("animetrace_models", "GET", None, None)

    def _request(self, provider, method, body, content_type):
        if provider not in ENDPOINTS:
            raise TransportError("blocked", "Unknown provider endpoint")
        host, path = ENDPOINTS[provider]
        conn = None
        try:
            records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            addresses = list(dict.fromkeys(record[4][0] for record in records))
            if not addresses or any(not public_ip(address) for address in addresses):
                raise TransportError("blocked", "Provider resolved to a non-public network address")
            # No fallback/retry after upload: a response might be lost after quota consumption.
            conn = PinnedHTTPSConnection(host, addresses[0], TIMEOUT)
            headers = {"Accept": "application/json", "User-Agent": "image-source-tool/0.1 (+local privacy-first research)"}
            if content_type:
                headers["Content-Type"] = content_type
            deadline = time.monotonic() + TIMEOUT
            conn.request(method, path, body=body, headers=headers)
            response = conn.getresponse()
            status = response.status
            if status in {402, 429}:
                raise TransportError("rate_limited", f"Provider quota/concurrency limit (HTTP {status}); no retry performed")
            if status in {401, 403}:
                raise TransportError("blocked", f"Provider denied this request (HTTP {status})")
            if 300 <= status < 400:
                raise TransportError("blocked", "Provider redirect rejected; no image sent to another host")
            if status == 413:
                raise TransportError("input_rejected", "Provider rejected image size")
            if status != 200:
                raise TransportError("service_error", f"Provider returned HTTP {status}")
            if response.getheader("Content-Type", "").split(";", 1)[0].strip().lower() not in {"application/json", "text/json"}:
                raise TransportError("invalid_response", "Provider returned non-JSON content")
            chunks, size = [], 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TransportError("network_error", "Provider response exceeded time limit")
                if conn.sock:
                    conn.sock.settimeout(remaining)
                chunk = response.read1(min(65536, MAX_RESPONSE + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > MAX_RESPONSE:
                    raise TransportError("invalid_response", "Provider response exceeded size limit")
            data = b"".join(chunks)
            try:
                result = json.loads(data, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            except (ValueError, UnicodeError, RecursionError) as exc:
                raise TransportError("invalid_response", "Provider returned invalid JSON") from exc
            if not isinstance(result, dict):
                raise TransportError("invalid_response", "Provider returned an unexpected JSON shape")
            return result
        except TransportError:
            raise
        except (OSError, http.client.HTTPException, ValueError) as exc:
            # Never persist raw exceptions, URLs, request fields or secrets.
            raise TransportError("network_error", "Secure provider request failed; check connectivity and retry explicitly") from exc
        finally:
            if conn:
                conn.close()

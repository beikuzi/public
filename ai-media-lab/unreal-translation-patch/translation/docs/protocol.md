# Local bridge protocol v1

Producer writes `runtime/inbox/<request-id>.tmp`, flushes/closes, then atomically renames to `.json`. IDs match `[A-Za-z0-9_-]{1,64}`; use a fresh random request ID, never reuse one until its outbox file is consumed/deleted. One worker per runtime directory. Queue files must be private, local, non-symlink paths. Maximum request file: 256 KiB; 1–64 unique per-text IDs. No arbitrary filesystem paths in payloads.

```json
{"version":1,"texts":[{"id":"widget_1","text":"Hello {PlayerName}"}]}
```

Worker atomically writes matching outbox JSON, then removes the input. This is at-least-once processing on crash, not exactly-once billing; memory cache is lost on restart. Do not auto-retry paid jobs after ambiguous completion without checking output and provider usage.

```json
{"version":1,"results":[{"id":"widget_1","original_sha256":"sha256-of-original-UTF8","text":"你好 {PlayerName}","status":"translated"}]}
```

Statuses: translated, cache, skipped, error. Error rows retain original text, plus a redacted error. Invalid whole requests return a top-level error. Input order and IDs preserved; duplicate strings deduplicated within a batch, including failures. Request-level source/target fields are intentionally unsupported; use explicit bridge config for a language pair. Strings exceeding limits fail closed; nested brace formats conservatively skip.

Game-side adapter requirements (not implemented by file queue itself): capture text safely; enqueue without any network call on game thread; render original while pending; poll completed results without blocking; apply only on the game thread to a still-live object whose current original UTF-8 SHA-256 matches original_sha256; discard stale results; prevent translated text re-capture loops; maintain bounded outstanding requests and backpressure. Never keep unvalidated raw UObject/widget pointers across frames. The candidate upstream mod has its own behavior and has not been certified against these requirements.

HTTP adapter is an optional compatibility surface for the pinned runtime. POST `/v1/chat/completions`, Bearer ephemeral local token, exactly one user message. Raw text or the documented pinned upstream prompt wrapper only. Response has `choices[0].message.content`. The upstream wrapper does not carry a source hash: its own lifecycle/stale-writeback safeguards must be validated separately. No streaming, tools, remote binding, or model dispatch.

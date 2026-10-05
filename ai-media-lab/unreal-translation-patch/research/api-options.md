# Translation provider options

Verified against official public documentation on 2026-10-05. Research only: no account setup, credentials, paid API calls, or external-agent runs were performed. Implementation recommendations below are design proposals, not claims of tested service behavior.

## Baidu: supported text-translation API

POST `https://fanyi-api.baidu.com/api/trans/vip/translate` with UTF-8 `application/x-www-form-urlencoded` fields `q`, `from`, `to`, `appid`, `salt`, `sign`. Compute lowercase hexadecimal MD5 over UTF-8 `appid + raw_q + salt + secret`; encode the form afterward. Never sign percent-encoded text. Source `auto` is valid; target `auto` is not. Codes include English `en`, simplified Chinese `zh`, traditional Chinese `cht`, Japanese `jp`, Korean `kor`, French `fra`, Spanish `spa`. Newlines separate multiple result segments. Results contain `trans_result` entries with `src` and `dst`; errors contain `error_code` and `error_msg`. The technical page recommends at most 6000 UTF-8 bytes.

Error meanings: 52001 timeout; 52002 system; 52003 unauthorized; 54000 missing parameters; 54001 signature; 54003 rate; 54004 balance; 54005 frequent long queries (wait three seconds); 58000 IP; 58001 language; 58002 disabled; 58003 IP risk-control block; 90107 certification. Official sample: appid `2015063000000001`, q `apple`, salt `1435660288`, dummy secret `12345678` yields `f89f9594663708c1605f3d736d01d2d4`.

Source: [Baidu technical documentation](https://fanyi-api.baidu.com/doc_bd/21). This official page's indexed text was readable; direct page retrieval sometimes returned only its dynamic shell. The public counterpart is [doc/21](https://api.fanyi.baidu.com/doc/21).

### Quotas, pricing, and unresolved release terms

The [current onboarding page](https://fanyi-api.baidu.com/doc/13) lists Standard: 50,000 free characters/month, 1 QPS, 1000 characters/request; Advanced: 1,000,000, 10 QPS, 6000 characters/request; Premium: 2,000,000, 100 QPS, 6000 characters/request. Advanced requires personal verification; Premium requires enterprise verification. The [service activation page](https://fanyi-api.baidu.com/access/0/1) lists Standard/Advanced overage at RMB 49 per million characters. These are public offers, not a verified entitlement for a particular account; the account console and accepted service terms govern actual billing.

Engineering choice: enforce both a conservative 1000-character limit and 6000-byte UTF-8 limit until the user verifies their tier; use one request/second by default. Do not present free allowance as a hard spending ceiling or silently increase rate/cost limits. Legacy documentation contains materially different free-tier claims and is unsuitable for current pricing.

An [older official service agreement](https://api.fanyi.baidu.com/api/trans/product/apidoc/) contains restrictions concerning client caching and onward distribution of translation data. The [currently linked agreement](https://api.fanyi.baidu.com/doc/6) rendered only a dynamic shell in this research. Consequently, permission for persistent translation storage and redistribution in a downloadable game patch remains unverified. Before releasing Baidu-generated game assets, inspect the actual current agreement accepted by the account and obtain clarification/permission where needed. This is an unresolved release prerequisite, not a conclusion that every localization use is forbidden. Research did not accept any agreement.

## Cursor account key: an official agent route, not raw chat completions

The [official TypeScript SDK](https://cursor.com/docs/sdk/typescript) supports user and service-account API keys, but not Team Admin keys. `@cursor/sdk` requires Node.js 22.13+. `CURSOR_API_KEY` supplies authentication. `Agent.prompt()` returns a run result; alternatively `Agent.create()`, `agent.send()`, and `run.wait()` yield final text in `result.result`. Check `status` before consuming it. Local mode hosts the agent loop locally; inference still uses Cursor-hosted models. Runs use normal Cursor plan billing and privacy rules.

For local agents, `tools: []` removes built-in tools; `disallowedTools: ["mcp", "task"]` removes MCP/custom tools and subagents. Reapply controls on resume. Set `local.settingSources: []`, `mcpServers: {}`, and `agents: {}`. Defaults permit tool execution. Credential resolution falls back to saved SDK login if no explicit/environment key is present. Available models/parameters can be discovered with `Cursor.models.list()`. The SDK is explicitly an agent SDK rather than standalone model inference/chat completions; no raw Router endpoint is documented.

### Recommended Cursor adapter design (not yet live-tested)

An opt-in, offline translation adapter can submit a tightly bounded batch to the official SDK, request a JSON array of stable IDs and translated strings, and validate the final text locally. This is a plausible agent-based translation workflow, not a guaranteed translation product. Do not call it direct OpenAI-compatible Cursor support.

- Run in a dedicated empty workspace outside the game/repository; disable tools as above and do not attach MCP, custom tools, plugins, or private files. Review any loaded settings/rules and disable unintended integrations.
- Require a nonempty explicit `CURSOR_API_KEY`; never invoke login or fall back to a different saved account. Reject unexpected backend/website URL overrides so the key cannot be redirected. Do not put secrets in the model prompt.
- Keep only the explicitly selected strings in each prompt. Do not send a whole installation, chat history, account data, or unrelated source files.
- Use a fresh agent per independent batch to avoid cross-batch context contamination. Fail closed if controls are unsupported by the installed SDK; never retry by enabling unrestricted tools.
- Pin and test the SDK version during installation. Documentation establishes API shape, not compatibility with an arbitrary installed release.
- Request JSON with stable IDs; require exactly the requested IDs, no duplicates, strings only, no prose/fences, and exact placeholder preservation. Invalid output remains untranslated for manual review.
- No frame-time runtime dependency: latency, throughput, and account-specific quotas were not measured or guaranteed. Use offline generation with a review step. Any retained output or distribution still needs suitable account terms and rights to the game content.
- Observe run cancellation and finite timeout. Treat retries as potentially billable; stop on authentication failures and usage caps. Do not promise subscription-funded unlimited translation.

Official [CLI authentication](https://docs.cursor.com/en/cli/reference/authentication) also accepts account API keys. Official [headless CLI](https://cursor.com/docs/cli/headless) and [output formats](https://cursor.com/docs/cli/reference/output-format) exist, but the SDK is preferable here because tool restrictions and typed completion/cancellation are explicit. Cloud Agents API is an agent-control interface; spawning repository agents is unnecessary for simple text translation.

Never use browser session cookies, undocumented endpoints, reverse-engineered proxies, credential extraction, TLS bypasses, or a billing workaround. Cursor account keys must not silently be replaced with unrelated generic model-provider keys.

## Provider-neutral contract (proposed)

Input: provider ID; source/target language; ordered entries `{id, text, context?}`; request character/byte ceiling; deadline; maximum paid attempts; cancellation signal. Credentials are injected separately and never serialized with entries.

Output: one ordered result per input ID with `{id, original, translated, status, provider, diagnostics_code?}`. Status is `translated`, `unchanged`, `skipped`, or `error`; never silently mark a failed source-text fallback as translated. Preserve original identifiers, namespaces, keys, and source hashes. Transport code does not edit Unreal packages.

Start with single-string Baidu requests. Embedded multiline entries should be segmented with an explicit reconstruction map or rejected for review; never assume output array length matches original entry count. Preserve empty lines and whitespace deliberately. Oversized entries fail validation rather than being arbitrarily cut through Unicode or format syntax.

Separate transport, rate limiting, placeholder protection, validation, and file writing. Write output atomically only after validation. Do not modify original files or overwrite reviewed translations without explicit selection. Persistent translation-cache policy must be provider-aware and disabled for Baidu until current storage permission is verified.

Error classes: configuration/authentication, permanent input rejection, quota/balance, temporary service/rate failure, malformed response, cancellation. Retry only temporary failures with bounded exponential backoff and jitter; respect provider retry hints. Never retry balance/auth/signature errors in a tight loop.

## Secret handling (design requirements)

- A distributed game client cannot safely hold a shared provider secret. Do not embed keys in `.ini`, assets, pak files, executables, examples, source control, telemetry, or crash reports.
- Prefer a user-run offline tool reading environment variables or an OS credential store. Examples use dummy values only. Do not pass secrets on the command line.
- For a production online system, use an explicitly authorized private backend with its own authorization, rate limits, and per-user spend controls. Do not build an open credential-bearing translation proxy.
- Use verified HTTPS endpoints, certificate verification, timeouts, and a restrictive redirect policy. Never forward authorization to a redirected origin.
- Redact secret values, signatures, authorization headers, entire request bodies, and server error echoes. Expose only sanitized error codes and concise remediation.
- Keep keys distinct: Baidu appid/secret, Cursor user key, and an unrelated LLM provider key are not interchangeable.

## Suggested tests (offline/mocked)

1. Official Baidu signing vector above; lowercase digest, salt preserved, raw UTF-8 before encoding.
2. Chinese, emoji, combining marks, plus, ampersand, percent, equals, newline and CRLF round-trip through form encoding exactly once.
3. Byte and character boundaries tested independently; no partial UTF-8 or split placeholders.
4. HTTP success containing provider error; numeric/string error codes; bad JSON; missing or wrongly typed results; duplicate/missing IDs; empty result.
5. Retry 52001/52002/54003 with a fake clock; 54005 delay at least three seconds; no retries for 54001/54004/58003; finite maximum attempts and cancellation.
6. Fake transport proves dry-run invokes neither network nor credential lookup and cost display makes no free-tier guarantee.
7. Exact preservation of `{Name}`, `{0}`, `%s`, `%d`, escaped braces, rich-text tags, tabs, line breaks and engine-specific format constructs; reject uncertain syntax rather than corrupting it.
8. Logs/exceptions/output fixtures cannot contain configured secrets, signatures, prompts, or response echoes.
9. Cursor fake SDK asserts tools are disabled, no MCP/subagents attached, fresh isolated workspace, status validation, timeout/cancel/cleanup, and JSON-only result parsing.
10. Verify generic OpenAI-compatible settings cannot accept a Cursor-branded preset or silently reuse `CURSOR_API_KEY`.
11. Round-trip original metadata unchanged, atomic output on failure, originals untouched, reviewed existing strings preserved, provider storage restrictions enforced.

No provider credentials are needed for these unit tests. Live smoke tests, account setup, license acceptance, paid usage, and game compatibility tests remain separate explicit steps.

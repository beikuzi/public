# Missing-like-count audit fix

Changes apply to current source only; frozen release-v2 and historical real data/results were not changed.

The documented importer→aggregator chain now accepts absent/null likes without int(None). Missing/null/blank values stay unknown. Explicit0 is observed0. Nonnegative integers and ASCII digit strings are accepted; bools, negative/fractional/float/malformed values remain invalid with canonical likes=null and likes_status=invalid. Invalid imported values remain invalid during aggregation.

Schema2.0 adds included-comment like coverage (observed/unknown/invalid counts and percentage), partial observed subtotals, complete totals only when valid, and an explicit like_share_status. Any incomplete coverage suppresses all like-share percentages. Zero-total or insufficient sample also suppresses them. Comment-count shares have their independent existing denominator/gate. All-unknown is different from all-observed-zero. First occurrence wins deduplication; later snapshots are not silently used to impute likes. Excluded comments do not enter coverage; exclusion_reason now survives import.

20tests pass:16analysis/integration tests plus4existing importer tests. Integration tests invoke both CLIs on synthetic JSON and JSONL exports. Malformed edges include bools, negative integers, floats, NaN/Inf, non-integer/comma/scientific-notation strings, containers and oversized digit strings. No external service, real comments or model files needed. The exact audit normalized-null reproduction also succeeds and preserves unknown status.

Consumers must distinguish likes_received (complete per-stance total or null) from observed_likes_received (partial known subtotal or null), and honor global like_share_status before rendering shares. Schema and command examples are in analysis/ANALYSIS_PROTOCOL.md. Include shared root module comment_likes.py in source bundles; the allowlist names all necessary modified/dependent files.

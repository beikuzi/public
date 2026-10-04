# 澄镜 · 六平台讨论观察

Static observatory with four distinct layouts. Each includes six platform pages and one summary:28 workspaces plus chooser.

Serve `dist/` as the public root. No application runtime dependencies, backend or API keys. `python build_data.py --check` verifies local evidence inputs; `python build_data.py` performs an atomic data-only compilation. See `docs/PROVENANCE.md` for provenance and update rules.

## Initial sample and temporal observations

The versioned initial dataset contains90 records,88 counted coverage records,3 official snapshot sources and5 bounded qualitative synthesis groups. X03 is historical official background rather than an X post; X13 is a weak undated lead. Both remain outside coverage metrics.

Later Bilibili, Weibo and Douyin ranking observations are separate. Compact panels compare only matched items and metrics, with original and subsequent capture times. Top10 interval entrants are not called new platform-wide trends. Weibo's incomplete initial selection cannot establish exhaustive new entries. Browser-observed changes do not prove cache or server freshness.

## Interaction and export

Keyword, domain, source and content-date filters act on the initial sample. Evidence dialogs preserve roles, source grade, content/capture dates, original links, AI disclosures and separate detail metrics. Manual evidence comparison and CSV/JSON sample exports are supported. Temporal panels have an independent JSON export.

CSV neutralizes spreadsheet formula prefixes after whitespace/control characters; JSON keeps original records. Missing values remain null. There are no audience/opinion percentages or inferred demographics. Role panels retain public self-descriptions or explicit publication/discussion relationships, with evidence and unknown identities.

## QA limitations

DOM and source checks are not full browser, mobile rendering or accessibility validation. This release does not claim those checks. The optional browser helper requires explicitly authorized sandboxed browser execution; it was syntax-checked only.

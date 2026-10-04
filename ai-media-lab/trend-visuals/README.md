# 澄镜 · 六平台讨论观察

A static, owner-private research snapshot dated 2026-10-04. Four distinct layouts each expose six platform routes and a cross-platform overview (28 workspaces plus a chooser).

Serve `dist/` as the public root. No build, runtime dependencies, API keys, accounts or backend required. All application data is in `dist/data.json`. Edit that compact evidence file to update research manually; `build_data.py` is the original local ingestion helper and expects the sibling research workspace.

## Routes
- `/` chooser
- `/{editorial,transit,console,atlas}/{summary,bilibili,xiaohongshu,weibo,douyin,x,wechat}/`

## Evidence rules
76 retained evidence records, of which X03 (historical official background, not X post) and X13 (weak undated fashion lead) are excluded from platform coverage counts. Other historical and undated material is labeled and can be filtered. Ten official Douyin ranked entries were added from a single 2026-10-04 22:41:58 UTC+8 browser snapshot. Twelve selected Weibo technology-category ranked entries were added from a 22:44:52 UTC+8 snapshot of 30 entries; category ranks are not general ranks. Clicking Weibo topic results requires login; no topic comments were read. No verified official rankings for the other four platforms, total audience estimates, opinion percentages, or inferred demographic identities. Sources are primarily secondary reports and search indexes. Missing engagement is kept null, not zero. WeChat dates belong to visible republications unless separately known.

## Interactions
URL-backed keyword, domain, source and date filters; evidence dialogs; selected-record comparison; current-filter JSON and CSV downloads; layout switching preserving platform and query; responsive navigation; keyboard search shortcut; semantic dialogs and focus states.

## Limitations
Static snapshot with no automatic refresh. All platform counts are retrieval coverage only. Source links may be blocked or require login. Shared-source republications are not independent corroboration. No attempt is made to circumvent platform access restrictions. Fonts have local fallbacks.

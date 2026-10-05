# 澄镜 · 六平台讨论观察

A static discussion observatory with four distinct reading layouts. Each has six platform pages plus a cross-platform summary:28 workspaces and one chooser.

## Run

Serve `dist/` as the website root. No application dependencies, backend, credentials or API keys are required. For example: `python -m http.server 8000 --directory dist`.

To validate local data inputs: `python build_data.py --check`.
To compile them: `python build_data.py`.

## Contents

-90 initial evidence records;88 counted coverage records
-Five bounded cross-platform synthesis groups
-Four observation points and selectable same-item temporal comparisons
-Keyword, domain, source and content-date filters
-Evidence/role drawers, source links and side-by-side comparison
-Separate initial-sample and temporal JSON exports; spreadsheet-safe CSV

See `docs/DATA.md` for evidence boundaries, chronology and update rules. Initial sample records are preserved; later observations do not increase initial coverage counts. Unknown ranks and metrics stay null. No representative opinion percentages or inferred demographic profiles are supplied.

## Tests

The source package's `qa/` folder contains DOM/data tests. Install its development dependency with `npm install --prefix qa`, then run the documented scripts. These checks are not browser visual, mobile or accessibility validation. Browser rendering has not been verified in the execution environment. Any optional browser helper keeps sandboxing enabled and must only be used where its preview access is permitted.

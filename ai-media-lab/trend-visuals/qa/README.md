# Regression checks

Install development test dependency: npm install --prefix qa.

Run from the source root:
- node qa/dom-test.cjs
- node qa/morning-test.cjs
- node qa/final-refresh-test.cjs
- python qa/build-test.py
- python build_data.py --check

The checks cover28 routes, preserved initial records, snapshot/date boundaries, historical comparison selection, JSON/CSV exports, unknown values and deterministic fail-closed input compilation. They use DOM/data simulations and are not browser visual, mobile or accessibility validation.

The optional test.cjs browser helper requires separately installed Playwright and an explicitly authorized preview URL. It keeps Chromium sandboxing enabled. It was syntax-checked only for this release; browser QA was not performed. Do not disable sandboxing or work around denied access.

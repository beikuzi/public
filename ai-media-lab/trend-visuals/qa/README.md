# Portable QA

From this source root:
- `python build_data.py --check`
- `python qa/build-test.py`
- `npm install --prefix qa`
- `node qa/dom-test.cjs`

DOM tests cover28routes,16temporal panels, unchanged90/88initial records,5synthesis groups, filters, dialogs, export metadata and CSV formula safety. Build checks cover missing inputs, bad hashes, semantic mismatch and deterministic compilation. They use disposable copies.

These are DOM/source checks, not full browser rendering or accessibility QA. `test.cjs` is an optional sandbox-required browser helper and has only been syntax-checked for this release. No generated screenshots or browser-success claims are included.

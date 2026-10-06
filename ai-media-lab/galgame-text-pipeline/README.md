# Version-pinned visual-novel corpus prerequisite

This workspace keeps game text private. Do not publish `private/`, downloaded game files, or full scripts to GitHub, Sites, or Library.

## Gate contract

1. Identify engine/build/language and exact distribution checksum.
2. Verify lawful access. Stop for encrypted/protected/unavailable content rather than bypassing it.
3. Inventory every script/archive; extract text and structural metadata with a supported adapter.
4. Report per-file/per-language coverage and all unsupported scripts, dynamic expressions, missing archives, and ambiguous asset links. A demo never satisfies the full-game gate.
5. Select a non-explicit scene only after the chosen edition's corpus scope is clear. Pin its location ID, source hash, label, line, preconditions, target dialogue, and expected visible assets.
6. Run A (asset reconstruction), B (engine save edit/load), C (normal play/checkpoint save) separately against exactly that edition.
7. Audit rendered frames and provenance. Record successes and failures per game/build and denominator; do not assign universal route probabilities.

## Implemented adapter

`tools/index_corpus.py` uses a strict non-executing inert Ren'Py legacy RPYC/RPA parser included in this source distribution. No pickle execution, imports of game classes, or game Python evaluation. It creates private corpus JSONL, source checksums, stable version-scoped IDs, label index, menu choices, conditions, visual commands, asset inventory and coverage. Python is opaque. It is not a universal extractor or complete Ren'Py control-flow evaluator.

Current validation: Katawa Shoujo **Act 1 v5 demo**. All 63 story scripts were structurally parsed (7 days × 9 languages). Four engine/UI scripts are unsupported. See `reports/demo-coverage.json`. Speaker identifiers are not an authoritative character-name glossary. Menu records preserve choices, but this edition uses custom Python/imachine routing, so a complete route graph is not yet recovered. Image commands contain symbolic references; image-to-file resolution and asset dependency closure are still pending.

## Output schema

- coverage.json: exact edition/scope/distribution/parser/pipeline hashes, file counts, class counts, limitations and errors
- files.json: every script's hash/status/node count/language hint
- corpus.jsonl: per-node ID, source/hash/ordinal, line/label/structural branch path; Say who/what; visual imspec; Menu choices and conditions; If conditions; opaque-code flags
- labels.json: label names to version-scoped locations
- assets.json: archive/member names and byte lengths, not copied copyrighted assets

No route may silently combine the Chinese demo corpus with the full edition's engine, save IDs, asset hashes, or scene labels.

## Full edition research

Current official website offers Katawa Shoujo v1.3.2 for English, French, Spanish and Japanese. Its Linux file is labeled x86 and listed at 481 MB on official itch. Actual architecture is unverified. Full website download invokes explicit adult-age confirmation; no gate has been submitted or bypassed and no full package downloaded. Official itch states Steam base edition excludes adult content; a public account-free base download has not been established.

- https://www.katawa-shoujo.com/download
- https://4leafstudios.itch.io/katawa-shoujo

A separate low-friction baseline is **The Question**, a complete short branching example VN distributed with full source and assets in the vendor's Ren'Py SDK. It must be described as a small baseline, not a commercial-length game or evidence that all engines work. Official SDK 8.5.3 Linux tar.bz2 is 146 MiB. No fallback runtime downloaded yet.

- https://www.renpy.org/latest.html
- https://www.renpy.org/dev-doc/html/thequestion.html

## Verified complete control baseline

The official SDK 8.5.3 has now been downloaded and unpacked under `vendor/`. Actual archive size is 153,611,590 bytes; SHA256 `eb0a9be7f0fb13632fe25ceade9a8bed5a1b4d6b6e83bd19eeeb29e1a1bb4a45` matches the vendor's HTTPS checksum file. PGP signature was not independently verified. Linux runtime is an x86-64 ELF binary. The common vendor base is logically immutable: route workers must use separate writable game/profile copies.

`tools/index_question.py` preserves every supplied source line privately, with per-file hashes and version-scoped location IDs. Coverage: 52 source files, 26,161 lines, no compiled-only scripts; English narrative has 252 source lines, six labels, two menus/four choices, two endings and one Boolean-dependent extra line. Translation source presence does not certify translation quality/completeness. See `reports/the-question-coverage.json` and `reports/the-question-scene-contract.json`. This adapter is explicitly source-format-specific, not a general Ren'Py parser.

The common non-explicit target is a proposal scene at English `marry`, source line 188. Expected backdrop and sprite are pinned by file SHA256. Route A/B/C must establish actual frame results independently; source coverage alone proves neither engine compatibility nor visual equivalence.


## Public closeout snapshot · 2026-10-06

This is an archive of already-completed experimental source. Only source, licences and limited technical coverage/QA records are published. Videos, screenshots, game assets, full scripts and scene-text mappings are excluded. Historical verification claims retain their original scope; closeout checked source syntax, JSON validity and publication boundaries only, without rerunning games or adding features. Paths referring to private inputs must be prepared separately from legally obtained matching editions.

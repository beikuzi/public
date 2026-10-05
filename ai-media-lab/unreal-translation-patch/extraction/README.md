# Unreal text extraction: real resource verification

Current result: **17/17 entries match independent source references exactly**, across five real compiled `.locres` files from two author-published MIT Unreal sample projects. This is an extraction tool, independent of the translation subsystem.

This proves decoding of **loose localization resource binaries**, not unpacking a shipped game's PAK/IoStore containers and not capture of visible runtime text. Neither game executable nor third-party program was executed. No encryption keys, DRM bypass, anti-cheat modification, or memory injection are involved.

## Run

Python 3.9+; standard library only. From this folder:

```sh
python fetch_samples.py
python -m unittest -v
python verify_samples.py
python locres.py fixtures/video-example/Content/Localization/Game/fr-FR/Game.locres --json results/export.json --csv results/export.csv
```

`fetch_samples.py` downloads only a few small localization/project/license data files from immutable commit URLs and checks every SHA-256 against `samples.json`. It downloads no executables or full game assets. Fixtures and full extracted strings are excluded from source synchronization; recreate them with the command above. Tests require fetched samples, rather than silently skipping the real-resource verification.

The CLI emits UTF-8 JSON and optional CSV. `text` is the string stored in the selected language resource, **not necessarily original/native text**. Namespace, key, source hash, namespace hash, key hash, and string pool index are retained. Entries are a list: duplicate text and duplicate identities are not silently collapsed. Outputs must not overwrite the input. Keep CSV as data: spreadsheet software may interpret leading formula characters if opened directly.

## Actual sample coverage

- [Lucas Guichard / TechNet VideoExample](https://github.com/GuicLuca/UnrealEngine_VideoExampleProject), project engine association UE5.3, commit pinned in `samples.json`. English and French resources: seven entries each. Independent UTF-16 `.archive` references validate `(namespace, key, source hash, localized text)` with multiplicities, using CRC32 over the native source's four-byte code units for the sample's BMP/ASCII source text. The manifest independently identifies five UMG text properties plus two `ST_CommonWords` StringTable-origin localization entries. This is not direct `.uasset` StringTable parsing.
- [Zompi UE4EasyLocalizationToolExample](https://github.com/zompi2/UE4EasyLocalizationToolExample), project engine association UE4.27. English, German and Polish resources: one entry each, compared with author `TestLocA.csv`. The plugin intentionally uses the **key as source text**, so its source hash is checked against `TEST_EXAMPLE`, not the English translation. `TestLocB.csv` is a different modified version, not the compiled resource reference.
- All five actual resources use locres version 3. Real-world v0/v1/v2 were not validated.

`results/verification.json` records per-file counts and hashes. `results/test-run.txt` records the validation run. Full per-resource JSON/CSV files are generated locally in `results/`.

## Additional synthetic tests

The separate generated tests exercise versions 0–3, Chinese, UTF-16 surrogate pairs (emoji), placeholders, line breaks, duplicate text with distinct keys, exact UTF-8 output, every byte truncation of each generated resource, negative/out-of-bounds pool offsets, unsupported version, impossible counts, invalid string indices, malformed UTF-16, missing terminators and trailing garbage. These tests do not pretend to be real game extraction. Non-wide strings accept ASCII only; ambiguous high-bit ANSI bytes fail explicitly rather than being replaced or misdecoded. Parser has a 128 MiB input limit and validates counts and boundaries.

## Limits

No claim of whole-game text coverage. Locres can omit hardcoded text, generated text, non-localizable `FString`, server text, image text, or resources not gathered for localization. PAK/IoStore unpacking, encrypted/custom variants, direct UAsset/Blueprint extraction, runtime hooks, live text replacement and packaged-game launch are not implemented or validated by this module. Source hashes are preserved; translation text must not be used to regenerate them.

## Licensing and references

Both sample repositories publish root MIT licenses, copied alongside each local fixture. VideoExample copyright © 2023 Lucas Guichard; EasyLocalizationToolExample copyright is retained verbatim in its downloaded LICENSE. Only author-created localization/sample metadata is fetched; no third-party art, engine source or game binaries are included. No separate conflicting license was found for those selected files. See immutable license URLs derived from each `samples.json` commit for auditability.

Format was inspected in [pylocres](https://github.com/stas96111/pylocres) (MIT); no third-party implementation was executed or vendored. The bounded reader here is independently implemented. [Epic's localization overview](https://dev.epicgames.com/documentation/unreal-engine/localization-overview-for-unreal-engine) distinguishes source archives from compiled runtime localization resources.

# Data and comparison rules

The initial compiled snapshot contains90 evidence records,88 counted coverage records and5 qualitative cross-platform groups. It remains unchanged. Later observations are separate, with four observation points in total: initial,01:00,06:30 and08:30 UTC+8. Individual platforms have exact capture timestamps inside their records.

The latest06:30→08:30 interval is the default. All provided earlier comparisons remain selectable and independently exportable. Comparisons match the same item, ranking scope and metric. A newly observed item insideTop10 or a technologyTop30 is not automatically a new platform-wide topic. The initial Weibo baseline saved12 selected items; later technologyTop30 snapshots were complete for that displayed scope.

Ranks and metric values can move in different directions. Neither establishes opinions, unique participants or approval. Displayed rounded values cannot establish exact growth. Bilibili danmaku is not a comment count. Browser observation time is not server refresh time; cache freshness is unknown.

An item not observed in an inspected list keeps null rank and metrics, not zero or a deletion claim. The relevant observed list size is retained. Content publication dates remain separate from observation dates.

## Reproducible compilation

`inputs/manifest.json` names every required local input and its SHA256. `python build_data.py --check` validates without writing. `python build_data.py` deterministically creates `dist/data.json` through an atomic write. Missing files, hash mismatch, nonchronological captures or inconsistent ranks fail before replacing output. Future updates require a versioned input batch and an intentional manifest/hash update.

The initial snapshot is a compiled evidence package; it should not be represented as an exhaustive raw source archive. Source links and individual limitations are retained. No missing raw source material has been synthesized.

# Bilibili evidence acquisition: blocked

No Bilibili video, audio, captions, or comments were acquired. This is a missing dataset, **not** evidence that the video has no comments. No stance analysis can be supported by it.

Candidate: https://www.bilibili.com/video/BV1NHmsBwEbT/

Public search index returned the title “15分钟从Prompt Engineering 到 Agent！一口气理解四种大模型增强技术！” and a description about prompt engineering, RAG, fine-tuning and agents. Actual uploader, duration, and comment diversity were not verified. The script and provenance record do not treat index text as a transcript.

Anonymous page access and metadata endpoint both returned HTTP 412. Web page fetch independently reported the same. Acquisition stopped. The failure body was not saved; exact status/error strings were retained in provenance.json. No evasion was attempted.

## Reproducible collection

`python acquire_bilibili.py BV1NHmsBwEbT --out evidence --pages 3`

This runnable standard-library script is provided for ordinary permitted access after the blocker has genuinely cleared. It has not been tested successfully against a live Bilibili API response in this environment. Do not run it repeatedly against the present denial. It requests three 20-root pages per hot/latest sort, deduplicates comment IDs, marks preview replies, strips author data and captures provenance. Any HTTP/API failure stops collection with partial evidence intact. No automatic media downloader, authentication or bypass is included.

Only derivatives (scripts, aggregate outcomes, evidence IDs and short necessary quotes) should be published. Keep downloaded media and full comment text private unless separate rights allow distribution. Comments can themselves contain personal data; review before quoting or sharing.

## Local import and normalized schema

For an authorized user export, run:

`python import_comments.py exported_comments.jsonl --out private/normalized_comments.json`

The source can be JSON array or JSONL. Rows require `id` or `comment_id` and `text`; optional `likes`, `sampling_group`, and `primary_stance` are preserved. Acquisition rows' `observations[].sort` are converted into a sampling group. The normalized output is a JSON list compatible with `analysis/aggregate_stances.py`: `id`, `text`, `likes`, `sampling_group`, and optional `primary_stance`. No stance is automatically invented. Author fields are discarded. The importer records source hash, import time and counts separately; keep original source metadata for capture time, pages, and root/reply relationships. Unknown export sampling must remain labeled unknown. Duplicate IDs retain first text and are counted once.

`python -m unittest discover -s bilibili -p 'test_*.py'` from the project root runs four entirely synthetic tests. Fixtures never represent real platform opinions. The acquisition script passed compilation/help checks only; successful live collection remains unverified.

## Later ordinary-browser result (2026-10-04 22:47 UTC+8)
The earlier HTTP412 remains a true method-specific failure, not proof that the whole site is unavailable. A normal browser visit loaded public metadata plus3 anonymous visible records. browser-evidence.json records this separate path and the explicit30-second video preview / login-to-view49comments restriction. The original comments.jsonl remains empty as the original API attempt result; visible-comments.raw.json is the separate local observation file. Full collection was not achieved. Only1 evaluative opinion was observed, so visible-comment-summary.json suppresses percentages. Do not publish full comment text or profiles; source publication date is2025, not a current-trend datapoint.

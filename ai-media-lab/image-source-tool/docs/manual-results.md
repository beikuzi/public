# Record Ascii2D / SauceNAO browser outcomes locally

Ascii2D remains a **manual browser route**, not an automated adapter. SauceNAO supports both its separately opted-in API adapter and manually recorded browser results. An imported record does not mean this CLI performed or independently verified that search.

## Workflow

1. Run the offline CLI for the image. Copy `input.sha256` from its private report.json.
2. Perform an authorized browser search on https://ascii2d.net/ or https://saucenao.com/. Record whether the image was actually submitted. On Ascii2D, distinguish color and BOVW results; do not invent a similarity percentage.
3. Save a small private JSON record using the format below. Keep images, raw HTML, screenshots, result pages and private findings out of public source control.
4. Import locally:

    python -m image_source_tool picture.jpg --manual-results private-output/browser-records.json --output private-output/combined

Importing makes no network request, uploads no image and fetches no result link. `--providers` and `--allow-upload` remain independent if you also want an API query. Invalid manual records are rejected before an API upload begins.

## Format (illustrative placeholders, not actual search results)

    {
      "schema_version": "1.0",
      "image_sha256": "REPLACE_WITH_THE_INPUT_SHA256_FROM_YOUR_OFFLINE_REPORT",
      "searches": [
        {
          "provider": "ascii2d",
          "method": "color",
          "status": "matches",
          "searched_at": "2026-10-05T00:00:00+00:00",
          "upload_state": "submitted",
          "candidates": [
            {
              "title": "Illustrative candidate title",
              "reported_artist": "Unverified index-reported name",
              "rank": 1,
              "links": ["https://example.com/illustration/123"]
            }
          ]
        },
        {
          "provider": "saucenao",
          "method": "browser",
          "status": "blocked",
          "searched_at": "2026-10-05T00:00:00+00:00",
          "upload_state": "not_submitted",
          "candidates": []
        }
      ]
    }

Replace all placeholders and example outcomes with what actually happened. Use the real timestamp with timezone. The file must match the exact original input hash; a recompressed or edited file has a different hash.

- Providers/methods: `ascii2d` with `color`, `bovw`, or `browser`; `saucenao` with `browser`. Use `browser` for a site-level attempt that never reached a particular result mode.
- Status: `matches`, `no_match`, `blocked`, `rate_limited`, `network_error`, or `service_error`.
- Upload state: `submitted`, `not_submitted`, or `unknown`. Do not report `matches` or `no_match` unless the image was submitted and the service returned an outcome.
- `matches` requires candidates. Other states require an empty candidate list. A challenge, failed submission, or inaccessible site is not a no-match result.
- Candidate fields: required `links`; optional `title`, `work`, `reported_artist`, `rank`; only SauceNAO allows `similarity` in its native 0–100 scale. Ranking is not similarity or attribution probability.
- Local bounds: 256 KiB, 1–6 search entries, no duplicate provider/method, at most 20 candidates per entry and 10 links per candidate. Unknown fields and known credential-bearing links are rejected. No raw provider payload or image data is accepted.

The report marks these entries `manual_record` and candidates `unverified_manual_candidate`. All identity and original-authorship conclusions stay unresolved. Metadata stripping of a prior browser upload cannot be verified by this importer. Imported text may itself contain private information; review before sharing.

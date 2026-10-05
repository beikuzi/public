# Provider implementation and observed availability

Last documentation review: 2026-10-05. This is a technical capability/status note, not a report of any user's image or findings. An implemented adapter, a successful unit test, and a completed live image search are three different things.

## Implementation and tests

- **Ascii2D:** manual browser route. Color and BOVW outcomes can be imported as local records. There is no automatic Ascii2D upload/search adapter in this release.
- **SauceNAO:** explicit opt-in API adapter using an existing environment key; also supports manually recorded browser outcomes. The two execution modes are labeled separately.
- **trace.moe:** explicit opt-in anime-frame API adapter. Does not identify the creator of an illustration.
- **AnimeTrace:** experimental explicit opt-in character/work API adapter. Dynamic enabled-default model lookup; no claim of original-art attribution.
- The current offline suite has 38 tests, including synthetic image handling, mocked APIs, privacy boundaries and manual records. These tests do not upload images or verify live service availability.

## Limited live observation: 2026-10-05

These observations describe one execution environment, not general service uptime. No image identity, candidate URL, private request headers, input hash or image content is published here.

- **Ascii2D web:** a normal GET of https://ascii2d.net/ returned HTTP 200, but its HTML displayed “Site Unavailable” and “Unable to access this site”. No upload form or search result was obtained; no image was uploaded. This is an inaccessible-page observation, not a completed search or no-match result. The cause could not be established from the response; do not label it a confirmed service outage, challenge, or network-policy denial.
- **SauceNAO web:** the homepage was observed earlier. A later file-selection/upload interaction did not return a completed submission or search result. A subsequent read-only browser inspection also stalled. Upload completion therefore remains **unknown** and the attempt **inconclusive**. A UI-tool timeout does not prove that SauceNAO itself failed, rejected the image, or returned no matches.
- **SauceNAO API:** not live-validated by those browser observations. Its mocked tests and form-transport client-source evidence remain separate from live availability.
- Neither requested website produced a verified search result in these observations. No character, work, original image or artist was identified by this live verification.

## How to record later attempts

For a private investigation, record each actual attempt with:

- provider and method (Ascii2D color/BOVW, SauceNAO browser/API);
- time and time zone;
- whether an image was submitted;
- returned matches, returned no-match, access block, rate limit, network/service failure, or an explicitly inconclusive attempt;
- candidate source evidence kept in the private report, not this public repository.

A homepage opening or HTTP 200 alone is not search success. A failed step before submission stays not-submitted; an interrupted step with unknown delivery stays unknown. `inconclusive` is available for workflow failures without a confirmed provider outcome, and `not_run` for an unattempted route. Neither is `no_match`. A browser success would not by itself verify the separate API adapter. These are historical observations, not uptime guarantees or source-attribution evidence.

# Provider implementation and observed availability

Last documentation review: 2026-10-05. This is a technical capability/status note, not a report of any user's image or findings. An implemented adapter, a successful unit test, and a completed live image search are three different things.

## Implementation and tests

- **Ascii2D:** manual browser route. Color and BOVW outcomes can be imported as local records. There is no automatic Ascii2D upload/search adapter in this release.
- **SauceNAO:** explicit opt-in API adapter using an existing environment key; also supports manually recorded browser outcomes. The two execution modes are labeled separately.
- **trace.moe:** explicit opt-in anime-frame API adapter. Does not identify the creator of an illustration.
- **AnimeTrace:** experimental explicit opt-in character/work API adapter. Dynamic enabled-default model lookup; no claim of original-art attribution.
- The current offline suite has 38 tests, including synthetic image handling, mocked APIs, privacy boundaries and manual records. These tests do not upload images or verify live service availability.

## Live verification record

Live provider outcomes must be recorded only after checking actual browser/service evidence. A homepage opening is not a completed search. No live success is asserted by this document until a dated, verified status is available.

For a private investigation, record each actual attempt with:

- provider and method (Ascii2D color/BOVW, SauceNAO browser/API);
- time and time zone;
- whether an image was submitted;
- returned matches, returned no-match, access block, rate limit, or network/service failure;
- candidate source evidence kept in the private report, not this public repository.

A challenge or failure before submission remains blocked/not-submitted, never no-match. A browser success does not verify the separate API adapter. These are historical observations, not uptime guarantees or claims that a source has been found.

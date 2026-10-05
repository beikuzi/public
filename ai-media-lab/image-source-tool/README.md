# Image Source Tool · 图片溯源工具

A local-first investigation CLI. It separates **which character/work is pictured** from **who created this particular image and where it originally appeared**. A matched anime frame does not establish the author of a derivative illustration. A repost does not establish an original artist.

## First milestone / Scope

- Offline inspection: decoded image validation, local SHA-256, dimensions, metadata inventory; no network by default.
- Explicit provider-by-provider upload consent; sanitize pixels into a fresh PNG before sending, stripping EXIF, location, comments, filenames and other embedded metadata. This does **not** anonymize visible image content.
- trace.moe for anime-frame/work candidates; SauceNAO for illustration/source candidates with an existing environment API key; experimental AnimeTrace for character/work candidates. Native provider scores remain separate.
- IQDB, ascii2d, Google Lens, TinEye and other browser-only routes are clearly labeled manual leads, never reported as completed searches.
- Static local HTML + JSON report; no trackers, remote images, image rehosting or public upload URLs. The original image is not embedded in the report.
- No invented probability, automatic artist attribution, circular-repost consensus, account creation, or paid-call automation.

## Install and run

Requires Python 3.10+ and Pillow. Use a virtual environment:

    python -m venv .venv
    . .venv/bin/activate
    python -m pip install -e .
    image-source picture.jpg --output private-output/example

Equivalent without installation (Pillow must already be installed):

    python -m image_source_tool picture.jpg --output private-output/example

This creates report.json and report.html locally. Open report.html in your browser. Reports can contain private source-search findings; keep the output directory private.

Explicit remote searches (upload sends sanitized image pixels to each named provider):

    image-source picture.jpg --providers trace_moe --allow-upload trace_moe --output private-output/frame
    image-source picture.jpg --providers saucenao --allow-upload saucenao --output private-output/art
    image-source picture.jpg --providers animetrace --allow-upload animetrace --output private-output/characters

SauceNAO requires an **existing** key in SAUCENAO_API_KEY. Never put credentials on the command line, into source control, or into reports. No tool creates keys. Anonymous trace.moe is quota-limited. The CLI does not opt into paid accounts or replenish quotas. A configured SauceNAO account could have a paid plan; use an account whose policy you accept. Quota and service limitations produce explicit states.

    python -m unittest discover -s tests -v

AnimeTrace is experimental. Its official API example uses no account or key, but no fixed free quota or formal pricing was verified. The adapter first fetches the enabled default model, then uploads once with AI detection disabled. No hard-coded model, payment credentials, new account or automatic retry. Character candidates are not evidence of the original artist.

## Reading a result

- work/character findings and exact-image/artist findings are separate.
- A provider match is a candidate, not a verified attribution; each retains provider, native score and candidate links.
- Author fields returned by an index are labeled reported_artist; they are not treated as first-party proof.
- All final identity/source conclusions stay unresolved until a human verifies the original post, artist identity and image match.
- Cross-provider duplicated links are grouped as the same lead, not counted as independent corroboration. Each provider's native score has its own scale and meaning.
- blocked, rate_limited, no_match, missing_credentials, consent_required, service_error and network_error are not interchangeable.
- Animated input is rejected rather than silently searching only its first frame. Supported inputs: still JPEG, PNG and WebP, max 20 MiB and 40 megapixels. Uploads are resized to at most 1600 px; search can miss crops, edits, redraws or lightly indexed originals.

## Privacy and network boundaries

No URL input/fetch, no arbitrary URL proxy, no automatic candidate-link fetching. Network requests are fixed HTTPS POST endpoints with TLS verification, no redirects, bounded response size and timeouts, and rejection of non-public resolved provider IPs. Returned links are validated as public HTTPS/HTTP web links before display; credentials, local/private hosts and unsupported schemes are omitted. Open result links only after your own review.

Upload metadata is removed in memory; sanitized pixels are not saved. Provider requests are not cached; reports are the only persistent findings, written with owner-only permissions. On POSIX, choose a fresh output directory or an existing directory with mode 0700; symlink output paths are rejected. On Windows, privacy depends on your user account and directory ACLs: choose a private, non-shared folder. Parent directories should be under your control. Known credential-bearing result URL query parameters are rejected, but review all findings before sharing them. Hashes are for exact local-file identity, not perceptual equivalence or public proof. Do not commit inputs or reports. No provider calls are retried automatically, avoiding duplicate uploads and quota consumption; a user may retry explicitly after checking the status.

### Limitations

This is an investigation helper, not a universal character recognizer. It has no local recognition model and does not scrape or bypass browser challenges. Trace.moe is primarily anime screenshot search, not a generic anime-art recognizer. Exact artwork and artist identification needs a first-party source and manual verification. The JSON schema and report record these limitations explicitly.

See docs/result-schema.json and docs/provider-notes.md. Third-party services have their own privacy policies and terms. Upload only images you are authorized to share with the selected service.

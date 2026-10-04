# Frame Evidence Lab

Four static frontend concepts sharing the same video-analysis evidence:
- `/#/workbench`: two-column evidence workbench
- `/#/terminal`: diagnostic stage rail and execution log
- `/#/notebook`: indexed editorial research notebook
- `/#/timeline`: frame-first inspection and transcript track
- `/#/`: layout chooser

## Run
Serve `dist` with any static HTTP server, e.g. `python -m http.server 8000 --directory dist`. No installation, API keys, backend, cookies, analytics or paid services required. Fonts use the OS font stack. `node check.mjs` validates routing render functions, data and core filtering logic; `node --check dist/app.js` validates syntax.

## Evidence
The neutral 40.103s public Beijing subway sample is a smoke/stress test, not a representative Mandarin benchmark. ASR tiny failed. Independent SenseVoice INT8 (sherpa-onnx 1.13.8) improved the noisy subway reference CER from 100% to 60% (39 edits / 65 characters), still unsuitable for precise quotation without review. Warm inference 0.592s; model load 1.071s; weights 239,233,841 bytes. Passing empty/repetition gates is not accuracy certification. Whisper base/small remain unmeasured. SenseVoice uses the custom FunASR MODEL_LICENSE 1.1, not Apache 2: https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE . Weights are not included. Direct HTTP/API Bilibili acquisition returned HTTP 412, but a later normal anonymous browser visit partially succeeded: metadata, displayed duration 15:19, and 3 visible records (2 roots + 1 emoji reply). Only 1 expressed a clear evaluative opinion. Full video/captions and the full displayed 49-comment set remain login-gated (30-second video preview). No overall stance percentages are reported. The site contains sanitized counts and one short paraphrase, never the complete comment corpus or commenter profiles. See every clickable benchmark row and on-page methodology for caveats. OCR held-out metrics are from a separate public subtitle sample and must not be mistaken for speech accuracy. No political transcript or raw comments are bundled. Pipeline v2 supports exact source PTS in new runs and has 9 portable tests; the existing published measurements and frames here remain v1 with approximate timestamps.

Derived subway frames: 2014Best, CC BY-SA 4.0. Source: https://commons.wikimedia.org/wiki/File:Beijing_Subway_Line_9_Arriving_at_Military_Museum_Station.webm . Frames retain the source license; timestamps are approximate FFmpeg sampling positions, not verified PTS.

## JSON import
The sample is `dist/data.json`. Import previews only `rows` in memory, while preserving built-in source frames/captions and context. The file is never uploaded or persisted. Maximum 1MB, 200 rows; required fields: id, name, status (measured/documented/blocked), seconds (number|null), cer (nonnegative number|null), cost (number|null), currency. Optional textual stage, quality, note, run, source (http/https). Do not put secrets or private source data in published files. Reset or refresh restores original records. Imported prices are not currency-normalized or ranked by cost.

## Portability and scope
Copy `dist` into any static hosting project for GitHub Pages or another host; the hash routes work without rewrite rules. Remove `.openai` when deploying outside Sites. All assets are local. The browser makes only same-origin asset reads unless the user opens a source link. The committed `data.json` is the complete sanitized snapshot. Update it from verified evidence; no original media, raw comments or model files are required.

## QA limits
All five route renderers and local asset paths validated, plus JSON provenance/null checks, sorting/filtering and HTML/URL escaping. Browser visual/layout QA was not executed because local browser preview was blocked in this environment; no restriction was bypassed. A bounded offline static-DOM → WeasyPrint → PDF/PNG inspection covered all four route documents with only embedded trusted local images and no network. This is document-render inspection, not browser validation: WeasyPrint shows pagination/grid and form/button rendering differences (thumbnail geometry and some grid/form intrinsic sizes are not faithful; an initial notebook column/pagination issue prompted a flexible-grid robustness fix). It establishes content/color/hierarchy inspection only, not live interaction or responsive browser correctness. QA output is kept separate from deploy assets. Responsive CSS has 760px and 1150px breakpoints, keyboard focus and dialog escape handling. No deployment thumbnail was created.

## Frame evidence demonstration
Timeline includes five inspectable visual questions tied to the existing corrected subway frames. Scene/train approach/green stripe have frame support; destination LED text and global no-passenger/all-doors assertions are unanswerable. Assistant-reviewed evidence demonstration, not independent blind validation and no accuracy percentage. Existing v1 approximate timestamps are retained.

## Comparison boundaries and scenario imports
Every benchmark record carries a scenario: noisy 17.940s subway crop (17.966s container), full subway, cleaner interview, held-out subtitle OCR, default OCR, preparation, Bilibili acquisition, documentation-only pricing, or unexecuted routes. Scenario and stage filters combine with status/search; sorting is within each scenario, never a global cross-task latency ranking. Mixed/unknown scenarios show a warning. Optional scenario string is backward-compatible: missing values become unassigned, not silently assumed comparable. Two preset noisy-clip preprocessing variants worsened SenseVoice reference CER: bandpass 86.15%, mild afftdn 81.54%, baseline 60%. Warm inference and extra preprocessing/combined time are separately labeled in the evidence drawer. Single-clip exploratory result, no universal denoising claim. No synthetic-voice ranking is mixed into video-ASR rows.

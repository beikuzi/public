# Measured benchmark snapshot — 2026-10-04

## Findings

The local media-to-evidence workflow executes. It does not yet satisfy high-accuracy general Mandarin transcription. Existing public captions are preferred when trustworthy and available; preserve them verbatim and verify speech correspondence. ASR needs confidence/repetition checks and manual/source cross-checks. Do not use low-quality hypotheses as the basis for factual or viewpoint analysis.

- Neutral subway video:40.103s. Audio extraction0.169s; 4 uniform frames1.109s; scene+initial extraction1.156s,1 frame. Different subprocess runs may vary. Contact sheet `outputs/subway_full_tiny_beam5/contact_sheet.jpg` is sorted and corrected.
- Published subtitle reference span10.954–28.894s:17.940s audio; re-encoded video17.966s. Tiny INT8 beam5: first inference0.643s, warm0.557s; reference CER100%. Output repeats a spurious phrase. Tiny INT8 beam1: first0.397s, warm0.275s; reference CER100%. Output empty. Neither is acceptable for this noisy announcement clip.
- Full40.103s subway context, tiny beam5: first1.862s,warm1.627s. Repetitive hallucinated output. No full-span CER because reference coverage is incomplete.
- Cleaner68.409s VOA interview, tiny beam5: first1.674s,warm1.604s. Coherent Mandarin output but visible homophone/name errors; no CER, because full independent verbatim reference unavailable. No conclusions about content.
- Tesseract Chinese `tessdata_fast`,14 executions across7 default subtitle crops: mean0.262s/image. Outputs poor; manually selected tighter crop took0.321s wall time and had38.46% normalized CER vs an assistant-read visible-caption reference. This is one selected image, not a representative OCR score or human gold annotation.
- Tiny model local files78,205,070bytes including metadata (~74.58MiB); load0.15–0.18s. Peak process cumulative RSS from separate runs roughly270–323MiB; not isolated model memory. Base/small are unmeasured: downloads did not complete.
- API bill:$0. Cloud CPU/time/storage costs were not priced; “free” means no paid API call, not zero infrastructure cost.

- Published-caption import:6 cues parsed into structured evidence in0.000260s, excluding network acquisition and verification. This retains existing text rather than recognizing speech; no independent accuracy measurement.

## Fairness and scope

4 CPU threads, INT8, temperature0, condition_on_previous_text=False, word timestamps enabled, VAD disabled, beam1 versus5. Same cropped source/reference and same tiny weights. Repeats are one first inference and one warm inference, not sufficient for variance estimates. Tiny beam5 cropped run occurred before beam1 and in a process preparing later downloads. Small timing differences are not robust rankings.

All model timestamps stayed within segment-level video bounds, but this does not demonstrate timestamp accuracy. Word/segment disagreement and hallucinations preclude meaningful anchor timing checks on subway. No independent manual listening/alignment was performed. Published SRT is saved raw; “CER” here means reference-caption disagreement, not certified speech error rate. Script variants (Traditional/Simplified) count as errors; no transliteration or hidden correction applied.

The neutral video is a difficult noisy/reverberant PA announcement; the cleaner VOA video is a different distribution. These are smoke/stress tests, not a representative dataset. The actual user Bilibili video and comment analysis remain unverified because acquisition returnedHTTP412.

## Failures and recovery

1. Default executor shell missing; explicit `/bin/bash` works.
2. Missing httpx SOCKS support; installed registry package.
3. Model cache tried read-only default directory; scoped writable HF_HOME/HF_XET_CACHE fixed it.
4. Current PyAV rejected `metadata_errors`; decode known16k PCM via stdlib wave and NumPy, avoiding incompatible wrapper.
5. Zero scene cuts caused FFmpeg JPEG initialization failure; select initial frame plus cuts.
6. Contact-sheet unsorted filesystem order mislabeled early sheet; sorted filenames fixed it. Use final corrected sheets.
7. Base Xet proxy TunnelUnsuccessful and tool approval cancellation; stopped this download route. No alternate endpoint bypass. Base/small timings/accuracy absent.

## Reproduce the measured local variants

```sh
.venv/bin/python pipeline.py inputs/subway_eval.mkv --output outputs/reproduce_beam5 --models tiny --threads 4 --offline --reference references/subway_10.954_28.894.txt
.venv/bin/python pipeline.py inputs/subway_eval.mkv --output outputs/reproduce_beam1 --models tiny --threads 4 --offline --beam 1 --reference references/subway_10.954_28.894.txt
```

Use actual option spacing `--threads 4` and `--beam 1` (see pipeline `--help`). Model and original video binaries are excluded from portable handoff; source URLs and licenses are inREADME. `benchmark-summary.json` and individual outputs contain raw measurements and hypotheses.

## Independent Vosk attempt

Official Vosk model page verified2026-10-04. Downloaded vosk-model-small-cn-0.22 ZIP43,898,754bytes in11.594s directly from the official alphacephei.com link; Apache2.0. Archive safety-checked and extracted. Runtime pip installation was blocked with proxy403 Forbidden and automatic approval cancellation. Stopped this route rather than using another registry. No inference, latency, CER or timestamp accuracy results. `vosk_benchmark.py` is prepared and syntax checked but unexecuted. Provenance and SHA256 in `outputs/vosk_attempt.json`.

## Offline OCR improvement

Six original848x480 frames were inspected and their visible captions transcribed by the assistant (not independently human-labeled). References and the fixed subtitle region were frozen before OCR candidate testing.12 preprocessing/PSM combinations were compared on development frames1–2 only. Selected method: pixels with allRGB channels>160 become black on white background; fixed caption crop;3× upscale;20px white border;Tesseract chi_sim psm6.

On frames3–6 held out from OCR parameter selection,99 reference characters: baseline microCER75.76% (75 edits) versus improved5.05% (5 edits), computed as sum of per-frame edits divided by total reference characters. Mean baseline OCR0.301s/frame vs improved0.190s including preprocessing and image save. Baseline was480px JPEG broadcrop; improved was original848px PNG narrowcrop+threshold. This bundled comparison cannot attribute gains to one component, and4 same-video/font frames are not a representative generalization benchmark. Residual errors include extraneous background characters and two substitutions. No automatic post-correction removed errors.

`outputs/ocr_improved/results.json` contains all held-out outputs;`development.json` retains every candidate score. The primary method is no longer represented by the earlier cherry-picked38.46% caption result; that earlier result remains historical baseline evidence.

Empty and highly repetitive ASR outputs now have explicit blocking quality gates in per-run JSON. Passing outputs remain unverified and require source review. Seven pipeline/gate tests pass.

## Version2 validation (separate from benchmark results)

Version2 rejects nonempty output directories, handles no-audio video and sub5s clips, records exact selected sourcePTS, and writes a sourcehash/options/version runmanifest. Nine portable tests passed using generated synthetic fixtures, including repeat-directory preservation and a nonzero sourcePTS offset. No synthetic fixtures count as real benchmark data. A separate existing-model offline smoke run is stored under `outputs/hardened_v2_eval/`; original timings and snapshots above are unchanged version1 results. Historical `pipeline_snapshot_v1.py` is retained for reproducing that implementation.

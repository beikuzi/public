# Video evidence workflow

Runs locally on a Linux CPU with FFmpeg. Keeps raw media, source metadata, audio, frames, ASR hypotheses, word/segment timestamps, reference text, and scored results separately. ASR does **not** analyze visual content. Review contact sheets and cite frame timestamps separately; sparse sampling can miss brief events.

## Setup / run

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
export HF_HOME="$PWD/.hf-cache"
export HF_XET_CACHE="$PWD/.hf-cache/xet"
.venv/bin/python pipeline.py /path/to/video.mp4 --output outputs/my_video --models tiny base --language zh --threads 4
```

FFmpeg/ffprobe and optionally Tesseract must be installed separately. First execution downloads official Systran converted Whisper models from Hugging Face. Models are large; downloads may fail in restricted networks. Set `--offline` to use existing `models/MODEL/model.bin` with no model download. No paid APIs or credentials required. Use `--frames-only` to avoid ASR/model downloads; `--beam 1` gives greedy decoding vs default beam5. Repeat runs share one loaded model; first-inference and warm-inference are labeled separately. CPU threads default4; comparisons should run sequentially, with no other compute workloads. `--reference reference.txt` computes punctuation/case/width-normalized character disagreement. This is reference agreement, not proof of factual accuracy or representative model performance. Chinese simplified/traditional differences are retained, so script variation counts as disagreement.

## Portable verification

Run `.venv/bin/python -m unittest test_pipeline.py -v`. Tests generate clearly synthetic2s/12s video fixtures in temporary directories and need no models/network/private files. `optional_tests/test_saved_benchmark.py` is an explicit historical-evidence suite requiring excluded benchmark files; it is not part of the portable suite.

## Evidence and limitations

- `probe.json`: raw media metadata
- `audio.wav`: mono16kHz PCM
- `frames/`: uniform JPEG selection starting at the initial frame and then every10sec or later source-frame PTS; scene-change threshold0.25 plus initial frame
- `contact_sheet.jpg`: sorted samples labeled with exact decoded source PTS and stream-relative time
- `MODEL_REPEAT.json`: full hypothesis, word/segment timestamps, timings and checks
- `results.json`: runs and extraction measurements
- Timestamp bounds checks do not measure alignment accuracy. Need manually verified speech anchors before a timing-accuracy claim.
- Character normalization only removes punctuation/whitespace and normalizes Unicode width/case; it does not silently correct recognition errors.
- Scene+initial frame count includes initial frame even when no cuts are detected.
- Model-byte total includes downloaded metadata; cumulative process RSS is not per-model isolated RAM.
- Model download time includes metadata/network overhead. Tiny initial download timing was interrupted by compatibility failures; successful tiny cached checks are not a true cold-download measurement.
- Runtime failures preserved: missing SOCKS dependency; unwritable default HuggingFace Xet cache; PyAV `metadata_errors` incompatibility (fixed by reading known PCM WAV with stdlib); zero-scene JPEG encoder issue (fixed by including initial frame). Base/small model downloads were not completed after proxy/approval cancellation. Do not claim their speed or accuracy was measured.

## Sources / licenses

Neutral sample: Beijing Subway Line9 Arriving at Military Museum Station, 40.103sec, 2014Best, CC BY-SA4.0. https://commons.wikimedia.org/wiki/File:Beijing_Subway_Line_9_Arriving_at_Military_Museum_Station.webm
Reference candidate: https://commons.wikimedia.org/wiki/TimedText:Beijing_Subway_Line_9_Arriving_at_Military_Museum_Station.webm.zh-hans.srt
Published SRT first four cues10.954–28.894sec are the scoring span. Not independently listened to/verified; results are agreement with published reference. Original source offset must be added to cropped timestamps. Re-encoded eval video duration17.966sec vs audio17.940sec due frame rounding.

Subtitle OCR stress sample: Ma Jian VOA interview20181112, Wikimedia file page marks VOA public domain. https://commons.wikimedia.org/wiki/File:Ma_Jian_VOA_interview_20181112.webm . Used solely to test Mandarin transcription and burned-in caption extraction. No political-content evaluation.
Models: https://huggingface.co/Systran/faster-whisper-tiny ; https://github.com/SYSTRAN/faster-whisper
OCR data: https://github.com/tesseract-ocr/tessdata_fast/blob/main/chi_sim.traineddata

Bilibili access and comments work is in `bilibili/` and `analysis/`. The direct HTTP/API acquisition attempt returned HTTP412. A later ordinary anonymous browser visit retrieved public metadata and3 visible comment records (2 roots and1 emoji reply), with only1 clear evaluative opinion. Full video/captions and the49-comment corpus remained login-gated; only a30-second preview was offered. See bilibili/browser-evidence.json. Do not report overall opinion proportions or treat fixtures as collected data.

## Caption-first route

`import_captions.py input.srt output.json --source-url SOURCE` preserves cue timing/text and source SHA256. Parsing is measured separately from acquisition (network time not included). Captions still need language, coverage, synchronization, and accuracy checks. No guarantee that uploader subtitles match spoken words.

## Transcript quality gates

`quality_gates.py` marks empty output and highly repeated character trigrams as blocked; raw hypotheses remain preserved. Passing output is explicitly `unverified_requires_review`, with independent verification required. These are conservative heuristics, not calibrated correctness estimates; real repetition can false-positive. Downstream analysis must honor `quality_gate.status` and never silently use blocked transcripts.

## Improved caption OCR experiment

`improve_ocr.py` freezes six assistant-read frame-caption references. Original848x480 frames are extracted to `outputs/ocr_improved/originals/`; a fixed subtitle region(100,350,745,435) is cropped.12 preprocessing/PSM candidates are selected on frames1–2; the selected method is evaluated once on frames3–6. This crop is tailored to this video layout, not a general subtitle detector. Outputs and candidate selection are fully saved.

## Version2 hardening

Output must be new or empty; a repeated nonempty destination is rejected before existing evidence changes. Each input therefore needs a fresh `--output`. Clips shorter than the sampling interval always receive an initial frame and contact sheet. Video without an audio track still produces visual evidence and ASR status `unavailable_no_audio_track`. Exact selected source PTS comes from FFmpeg `showinfo` with `-copyts`; manifest includes both sourcePTS and video-relative time. `run_manifest.json` records SHA256, source bytes, options, library/tool versions, and completion/failure status.

Version1 benchmark measurements and frame snapshots were preserved; `pipeline_snapshot_v1.py` is their historical implementation. Version2 changes sampling from FPS nearest-frame sampling(~5/15s) to first-frame plus elapsed-interval selection(0/10s), so do not mix frame sets. Version2 has9 portable tests and one separate offline ASR smoke rerun; historical performance numbers remain version1 and were not silently relabeled.

## Independent Mandarin ASR and noise trials
See sherpa_lab/REPORT.md for licensed SenseVoice INT8 local evaluation. On the same noisy17.94s published-caption-reference span, CER60% versus tiny100%; neither is high-accuracy. Predefined bandpass and afftdn presets worsened this clip to86.15% and81.54%; keep the unmodified source. Model weights are not distributed, and custom FunASR MODEL_LICENSE1.1 applies (not Apache/MIT). Passing repetition/empty gates still does not certify transcript correctness.

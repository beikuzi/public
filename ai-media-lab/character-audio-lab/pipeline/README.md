# Character audio dataset pipeline

Python 3.10+, FFmpeg and ffprobe. Standard library only. This is annotation-driven preparation, not automatic character recognition or a claim that a separator isolates one person.

## Run

```sh
python pipeline/dataset.py build --source source/movie.mp4 --annotations source/annotations.json --output private-output
python -m unittest discover -s pipeline/tests -v
python pipeline/dataset.py import-separation --dataset private-output --report separation-report.json --allowed-root /absolute/path/to/separator-outputs
```

Output must be absent or empty. Outputs: `clean/raw`, `noisy/raw`, `noisy/voice_only`, `manifest.json`, `statistics.json`. Audio is not uploaded by this program. Keep private outputs, source media and model weights out of source control.

## Annotation contract

```json
{
  "source_sha256": "SHA256_OF_EXACT_MEDIA",
  "timebase": "decoded_audio_seconds",
  "target_speaker": "character_A",
  "speaker_label_method": "human-reviewed scene and transcript attribution",
  "quality_criteria": "clean: no audible music, competing voice or material noise after listening; noisy: audible background; unknown: review required",
  "segments": [{"id":"a001", "start":1.2,"end":3.5,"speaker":"character_A","confidence":0.99,"transcript":"Example","quality":"noisy","quality_evidence":"Reviewer heard music underneath","overlap":false}]
}
```

The zero point is the start of FFmpeg-decoded first audio stream, not an assumed video timestamp. Verify subtitle offsets before annotating. Intervals identify whole utterances and must not include another speaker. Confidence is an annotation judgment, not model-calibrated probability. Original annotations and exact source SHA-256 are bound into the manifest. Optional segment fields pass through to mappings.

Unknown quality, missing affirmative quality evidence, confidence below 0.9, overlap, other speakers, overlapping target annotations and utterances longer than 10 seconds are quarantined in the manifest. Long utterances need independently annotated natural-pause boundaries; the program does not cut speech to force length. Unannotated time is reported separately. No claim is made that annotations exhaust a film or contain only voiced samples.

## Rendering and duration accounting

48 kHz stereo PCM16. Mono inputs become two-channel; first audio stream is rendered to stereo using FFmpeg. No loudness normalization or time stretch. Same-target utterances of the same quality class are concatenated in source order with 120 ms silence and 5 ms edge fades. Every source-to-clip frame mapping is recorded. These are assembled utterances, not one continuous original sentence. Clips span exactly 5–10 seconds; a final short group gets trailing silence up to 5 seconds. Extreme short inputs therefore technically pass duration but are not useful training examples.

Reports distinguish raw file duration, unique source-interval union, summed interval duration, added gaps and padding, processed file duration, accepted/excluded coverage and source time that was never annotated. Interval duration is an upper bound on speech content. Usable voice seconds remain null until validated VAD/listening and quality review exist; silence padding is never counted as speech.

## Separator import

A genuine external separator must run separately. Missing models never generate fake processed files. Clean audio remains unchanged. JSON report:

```json
{"outputs":[{"clip_id":"noisy_0000","input_sha256":"EXACT_RAW_SHA256","output_path":"/absolute/allowed/root/vocals.wav","model":"hdemucs","model_version":"version and checkpoint identifier","method":"music-source separation","limitations":["may retain other speakers and distort speech"]}]}
```

Import validates IDs, hashes, path containment, provenance, uncompressed WAV, 5–10 second bounds, and duration preservation within 10 ms. It copies outputs into `noisy/voice_only` and updates per-group statistics. Float32 separator WAV is supported via ffprobe. A `voice_only` folder is a processing label, not a purity guarantee. Listen for leaked background, missing consonants and changed timbre before any downstream training.

## Safety / reproducibility

Rejects path traversal, symlinks, stale source hashes, nonfinite/invalid timestamps, duplicate annotation IDs and nonempty output directories; separator import refuses overwrites. No pickle or model loading, network calls, third-party upload, or training in this module. CLI paths are operator-supplied; annotate only media you are entitled to process. FFmpeg/version and model provenance should be retained with run reports.

Tests synthesize tones locally and exercise stitching, exact endpoint crops, overlap quarantine, confidence, long and very short utterances, 5–10 second lengths, padding accounting, source hashes, path safety, missing models and separator import. Passing these tests validates mechanics, not source annotations or perceptual separation quality.

## Provisional source annotations

Unknown speaker overlap is excluded by default. `--allow-unverified-overlap` is an explicit experimental mode that retains unknown overlap labels in mappings and marks the entire manifest provisional. Known overlap is always quarantined. Use this only to prepare review examples, never to claim verified training-ready identity data. FFmpeg version is recorded in each manifest.

## Prefer contextual separation before assembly

Run the neural model on each original contiguous utterance with context (for example ±1 second), not on stitched unrelated utterances. Record each processed contextual WAV in a JSON report:

```json
{"outputs":[{"segment_id":"a001","source_sha256":"EXACT_SOURCE_HASH","output_path":"/absolute/allowed/root/a001.wav","output_source_start":0.2,"model":"hdemucs","model_version":"exact checkpoint/version","method":"contextual music-source separation","limitations":["not speaker-specific"]}]}
```

Then trim context at exact source frame positions and reproduce identical gaps, fades and padding:

```sh
python pipeline/dataset.py assemble-separated-segments --dataset private-output --report segment-report.json --allowed-root /absolute/allowed/root
python pipeline/verify.py private-output --output private-output/qa.json
```

The processed assemblies are float32 stereo WAV at 48 kHz to preserve model values. Their sample counts match raw PCM16 originals exactly. Mapping and model metadata identify every contextual file and trim. QA verifies hashes, frame counts, 5–10 second lengths, source-to-clip mapping and duration accounting; waveform metrics describe clipping/silence but do not establish perceptual quality. Synthetic fixtures are out-of-sample mechanical tests, never evidence of separation quality on the film.

A segment can set `review_quarantine: true` plus a `review_quarantine_reason` to force exclusion while preserving its original speaker confidence and acoustic class. Independent speaker audits should use this rather than silently altering acoustic labels.

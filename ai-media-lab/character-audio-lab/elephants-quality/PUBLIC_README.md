# Production-source candidate screening and actual-film separation

This source-only package accompanies a completed local Elephants Dream audio experiment. It includes no audio, film/DVD bytes, full ASR transcripts, weights, embeddings, dependencies or private data paths.

## Completed evidence

- Twenty original role-labelled production WAVs: mono,48kHz,PCM16. Container and VAD totals include alternative/repeated material and are not unique usable duration.
- Four selected Proog source crops,8.075,6.600,6.850 and6.900 seconds, pass explicit numerical gates:5–10s duration, zero full-scale samples, at least65% VAD coverage, at least6 ASR words with confidence diagnostics, file-level non-VAD RMS≤−50dBFS, and exclusion of known alternate-file duplicates.
- Actual HybridDemucs inference on four contiguous final-film contexts:43.000 seconds before and43.000 seconds after,11.505 seconds cumulative wall time. Exact48kHz stereo frame lengths verified. These contexts are broader than the final dataset clips and cannot be equated to admitted target-speaker duration.
- Independent before/after Silero VAD and unprompted Whisper tiny.en ASR completed. Eight unit tests pass. Original source hashes remain unchanged.

`public-summary.json` contains sanitized aggregate measured evidence. No synthetic score is presented as a film result. No SI-SDR improvement is reported because exact edit-free reference correspondence was not established. Final-minus-M&E residuals are not used as clean truth.

## Interpretation

The label is an authored role-labelled production-source, machine-screened candidate. It is not proof of isolated actor-only audio or verified clean speech. No human listening occurred. Music absence, overlap absence and target-only speaker purity remain unknown. Non-VAD file energy is a screening proxy, not measured noise or SNR. ASR words and VAD regions are model estimates. Lower RMS, changed VAD duration or one corrected ASR phrase are not perceptual improvement metrics.

HybridDemucs extracts all vocals, not a selected character. Separation can preserve other speakers, introduce artifacts and retain residual music. Boundary-safe target crops and piecewise movie alignment must be established separately before assembling paired examples. Production edits can change offsets within the same source WAV. File duration alone is not useful-speech duration.

## Source and dependencies

Public source context: https://orange.blender.org/blog/talking-heads/ and https://orange.blender.org/theteam/ . The original DVD mirror is https://archive.org/details/elephans-dream-iso . Source researchers checked the production folder's original CC BY2.5 license; downstream audio sharing must retain correct attribution and provenance independently of this source-only package.

Local inference uses existing official hash-checked Silero TorchScript, OpenAI Whisper tiny.en and Torchaudio2.8 HDEMUCS_HIGH_MUSDB_PLUS. No paid API, upload, ONNX telemetry runtime, or unrecognized executable source was used. Model API cost was zero; infrastructure cost is unpriced.

The measurement scripts require the already-installed local model/dependency environment and private authorized inputs. They are not a bundled dataset. Pure unit tests require only Python:

    python -m unittest discover -s character-audio-lab/elephants-quality -p 'test_*.py' -v

Tests cover union/clipping of VAD intervals, invalid bounds, numerical gates, unknown energy evidence, clipping rejection and alternate-take rejection. `crop_qc.py` imports audio dependencies only for its executable local audit, so importing its tested pure functions is dependency-free.

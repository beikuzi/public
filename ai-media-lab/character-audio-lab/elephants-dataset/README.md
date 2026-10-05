# Multi-source character dataset assembly

This experimental assembler consumes evidence-backed annotations from multiple role-labelled production WAVs, matched film intervals and separated film contexts. It does **not** certify speaker identity, clean purity, overlap absence, or training readiness.

Requires Python 3.10+, FFmpeg/ffprobe and the sibling `../pipeline/dataset.py`. No model or network dependency.

```sh
python assemble.py --config evidence-backed-config.json --output new-output-directory
python -m unittest discover -s tests -v
```

## Source and frame contract

Configuration has `sample_rate: 48000`, `target_speaker`, a `sources` object and a `segments` list. Every source has its exact `path`, `sha256`, and `kind`. Role-labelled source kind is `authored_role_labelled_production_wav`: this does not mean author-certified isolated voice. Movie sources use `movie_mix`. Contextual neural outputs use `contextual_separated_vocals` and require `model_provenance`.

Each voice unit records `id`, `speaker`, `author: {source_id, start_frame, end_frame}`, optional `movie` and `separated` references using the same structure, `machine_qc_pass`, `overlap_status`, `quality`, and `speech_regions` in author-local integer frames. Matched movie/separated reference lengths must exactly equal author interval length. The movie reference requires `alignment.accepted: true`, together with the actual evidence and uncertainty. A separated context has its own local frame zero; the config builder must subtract its verified original movie origin before making the reference.

All interval endpoints are half-open source-local sample frames, not video timestamps. The first audio stream is selected. Inputs must already be48k; unsupported resampling requires a separate provenance step. Exact source bytes are SHA-bound before use. No whole-file alignment offset is assumed: edited production recordings can need a different offset for each utterance. Known cross-role overlap, wrong-role candidates and failed QC are excluded. Unknown overlap remains unknown in every output.

## Output semantics

- `clean/raw`: authored role-labelled production-source **candidates** passing explicit machine screening; not a declaration of isolated or human-verified clean speech
- `noisy/raw`: aligned movie mixtures
- `noisy/voice_only`: genuine externally separated contextual movie vocals, cropped and assembled after separation; no target-only guarantee

A source-only unit may legitimately have no movie or separated counterpart. Missing models produce no fake processed file. Variants with the same coverage use identical packing and source mappings. Generated files are5–10s, stereo48k. Authored/movie files use PCM16; processed outputs retain float32. Mono source conversion uses FFmpeg's default equal-power stereo conversion and is recorded. No time stretch or loudness normalization. Edges get5ms fades; stitched utterances get120ms gaps. Final padding is separately counted and minimized with ordered dynamic packing. Utterances longer than10s must be reannotated at verified natural pauses; the assembler never cuts speech just to force length.

The manifest records every source ID/hash/frame interval and output frame mapping. Statistics separate file duration, source union, gaps, padding and machine-estimated speech. Author/movie/separated versions of a voice unit are alternate views and **never summed as three times the unique voice content**. Movie timeline overlap from alternate takes must be deduplicated before export. Same source bytes under different IDs cannot evade duplicate-interval checks.

## Safety and limitations

Rejects symlinks, traversal, stale source hashes, duplicate unit IDs, overlapping selected source intervals, invalid frames, mismatched paired lengths, nonfinite samples and existing outputs. Files are built in a staging directory and atomically moved into place only after successful rendering. It does not upload files, load weights/pickle, infer biometric identity or train a voice clone.

Labels and numerical screens are evidence, not ground truth. Low energy outside VAD does not prove no music during speech. ASR may hallucinate or truncate proper names; match interiors may cut utterance edges. Author and movie processing may differ in gain, EQ, reverb or editing, so alignment alone does not justify a reference-based SI-SDR claim. Any listening, overlap and residual-noise limits must accompany actual outputs.

Synthetic fixtures test mechanics only and are not evidence of real-film separation quality.

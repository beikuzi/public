# Local vocal-separation benchmark

## Measured result
The actual 10-second Sintel excerpt (205–215s of the 5.1 FLAC master) was processed by a genuine neural Hybrid Demucs separator, not a noise gate. On this machine, with four CPU threads, the first run used 5.22 seconds of wall time (including import/load) and 1.66 seconds of model inference, at about 1,048 MiB peak RSS. The output preserves all 480,000 frames at 48 kHz. Center-channel extraction took 0.006 seconds. API charges are $0; infrastructure is not priced.

These are implementation timings, not a promise for a user's hardware. CPU count is nine logical processors and reported physical memory about 9.7 GiB. The environment occupies about 767 MiB; model weights add 319.2 MiB.

## Files and comparisons
The following filenames describe private local benchmark artifacts, intentionally excluded from this repository. Only source, tests, aggregate observations and model provenance are published.

- `film10_stereo.wav`: FFmpeg downmix of the original 5.1 master.
- `film10_center.wav`: the actual FC channel, not a neural separator or stereo mid-side estimate.
- `film10_vocals.wav`: local neural estimate of the vocals stem.
- `film10_me_subtraction_unverified.wav`: privileged-source M+E subtraction candidate. It uses the separate official stereo master, so it is not exactly the same downmix as the first comparison. Do not treat it as a clean vocal reference.
- `film_no_reference_diagnostics.json`: finite values, duration, peaks and subtitle-window energy diagnostics. Lower energy outside subtitles is not measured music removal, because subtitles omit breath, nonverbal sounds and some speech.
- `stem_subtraction_validation.json`: M+E/master regression checks. Gross alignment is good, but a single gain does not cancel the background exactly. Calibration fitted gains range 0.640–0.726, with -8.7 to -12.9 dB residual energy relative to the master. No verified clean-dialogue reference was recovered.
- `background_classification.json`: conservative background-present labels using the official M+E stem, not a speech SNR or listening judgment.
- `controlled_results.json`: a separate deterministic synthetic-vowel diagnostic with known clean reference, mixed with official M+E at 0 dB RMS ratio. SI-SDR changes 0.02 → 4.43 dB (+4.41 dB). The reference is synthetic and has no real speaker. These numbers must not be presented as natural-speech or film-dialogue quality.

## Running
Use `.venv/bin/python separate.py input.wav output.wav --method hdemucs --threads 4`. Mono input is duplicated; stereo is preserved. Float32 WAV output avoids hidden peak normalization. For a verified six-channel WAV in standard FL FR FC LFE BL BR order, `--method center` extracts FC without requiring Torch. The CLI writes a JSON timing/length sidecar.

The neural path uses 44.1 kHz internally, five-second analysis windows and 0.5-second overlap. Output is resampled back and explicitly trimmed/padded to the original frame count. Dataset excerpts should be separated with contiguous source context first and trimmed/stiched afterward; model processing across artificial concatenation seams is avoided.

The environment was installed using official CPU wheels: torch==2.8.0 and torchaudio==2.8.0 from https://download.pytorch.org/whl/cpu. NumPy and SciPy are supplied by the host. The official weight URL, byte count and SHA-256 are recorded in `model_manifest.json`. The checked-in Python wrapper pins that checksum and loads using `torch.load(weights_only=True)`; it never enables remote code or unsafe pickle.

## Limits and review
1. Hybrid Demucs separates music stems. Its `vocals` output may retain every speaker, song vocal, breath and some sound effects. It does not identify Sintel or remove overlapping human speech.
2. VAD finds speech-like activity, not character identity. Speaker similarity needs an independently verified reference; a relative score without calibration is not a confidence percentage. Overlaps should be rejected or manually reviewed, not silently assigned.
3. Center extraction can be excellent when film dialogue is centered, but centered music/effects remain. Off-center speech may be lost. Stereo mid extraction is not equivalent to the actual 5.1 FC channel.
4. Review before admitting any training data: clipped syllables, wrong speaker, overlap, retained music/effects, watery/metallic artifacts, breath loss, reverb tails and seams. Auditory review has not been performed here; all estimates remain provisional.
5. Do not call outputs “music completely removed” or “target character isolated.” Do not fabricate a clean folder when no clean excerpt has been verified.
6. This sparse short-film demo does not establish a viable training corpus. No voice model was trained and no clone was created. Film copyright licensing does not by itself establish every performer, likeness or voice-cloning permission.

## Primary sources
- Official model bundle and training description: https://docs.pytorch.org/audio/2.8/generated/torchaudio.pipelines.HDEMUCS_HIGH_MUSDB_PLUS.html
- Official model source/loader: https://github.com/pytorch/audio/blob/v2.8.0/src/torchaudio/pipelines/_source_separation_pipeline.py
- Torchaudio BSD-2-Clause: https://github.com/pytorch/audio/blob/v2.8.0/LICENSE
- Original Demucs MIT repository, CPU use and music-stem limitations: https://github.com/facebookresearch/demucs
- Official Sintel audio source links: https://durian.blender.org/download/ and https://media.xiph.org/sintel/

The original Meta Demucs repository is archived; its author points to a maintenance fork and states active feature development has ended. Pinning this measured official TorchAudio implementation is intentional. MDX/UVR/Roformer wrappers offer other models, but no unverified third-party scripts or weights were executed in this benchmark. Model-specific licenses and resource needs must be reviewed before substituting one.

# Production-dialogue waveform alignment

This source-only package implements a conservative alignment method for role-labelled production dialogue and a final-film mix. It contains no audio, models, full dialogue text, machine transcripts, or file-specific paths. It does not download or upload anything.

## Run

Use Python with the dependencies in `requirements.txt`, then run:

    python -m unittest -v
    python align_production_dialogue.py --movie FILM.wav --source ROLE.wav --speech-regions VAD.json --output RESULT.json

`VAD.json` is an independently generated array of objects with `start` and `end` in seconds. CLI output identifies inputs by SHA256 rather than paths. Source role identity must be established separately.

## Method

1. Downmix stereo to arithmetic mean, resample to 4 kHz and apply a third-order zero-phase 100–1700 Hz bandpass.
2. Search 1-second anchors at 0.4-second stride within independent speech-activity regions, using normalized FFT correlation against the movie. Absolute correlation accommodates polarity/phase differences.
3. Group anchors with absolute correlation at least 0.60, source gap below 0.85 seconds, and lag difference below 12 milliseconds. Require at least two anchors per group.
4. Intersect matched windows with speech-activity regions. These are matched interiors, not complete utterance boundaries.
5. Optionally use the `refine_local_offset` function on unfiltered mono signals to search local full-rate lags within ±30 milliseconds at 0.5-second stride. Inspect individual lags rather than treating their median as exact ground truth.

The associated research used local Silero VAD with threshold 0.5, minimum speech 100 ms, minimum silence 150 ms, and 30 ms padding. The production analysis used 48 kHz full-rate refinement. The package accepts VAD annotations rather than bundling that model.

## Findings and limits

The compact aggregate report concerns 20 Elephants Dream production voice tracks matched to an official final stereo mix. Multiple edits within single production tracks invalidate a scene-wide offset. Alternate scene 7 tracks duplicate film coverage, so a timeline union is necessary to avoid double-counting.

A total of 64 speech interiors met the machine correlation rule. Their union covers about 85.77 seconds labelled Proog and 37.15 seconds labelled Emo in the final mix. These numbers are machine-supported matched coverage, **not usable clean training-data totals**. Source VAD estimates include alternate recordings and possible nonverbal activity.

A high waveform correlation supports correspondence; it does not prove speaker identity, absence of another speaker, or clean isolation. Source role labels originate in production filenames. Missing other-role matches cannot establish overlap-free speech because coverage is incomplete. Intersecting matched regions revealed one candidate cross-role overlap, which is not human-verified.

One-second anchors can straddle an edit. Their outer coverage boundaries may overlap differently edited neighboring material. Final phrase cuts require separate word/breath/pause review and explicit margins; VAD interiors alone are insufficient. Small lag variation may reflect phase, processing, resampling or edits; the method does not assert a global clock drift.

No human listening or verified-clean result is claimed. Clean-reference or separation-quality metrics require additional justification and should not treat these production tracks as sample-identical final-film ground truth.

## Tests

Seven synthetic tests cover known delays in noise, polarity reversal, silent-anchor rejection, piecewise edit grouping, isolated/weak-anchor exclusion, duplicate coverage union, and full-rate local refinement. They validate implementation invariants, not real-world listening quality.

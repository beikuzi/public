# Character-role speaker audit: source-only reproduction

This folder publishes source code, frozen exploratory protocols, scalar evidence, and reports. It deliberately excludes film clips, transcript collections, speaker embeddings, model weights, dependency trees, and local execution paths.

Read REPORT-v2.md first: the final result is a small Shaman positive control (9.592 seconds of machine-detected speech, including 4.488 seconds of enrollment and 5.104 seconds of non-enrolled candidates). Sintel remains a disclosed difficult case. No audio is asserted free of overlap, human-verified, or training-ready. Initial and follow-up gates and failures are retained.

## Public inputs and local preparation

- Licensed film and original soundtrack downloads: https://durian.blender.org/download/
- Film licensing: https://durian.blender.org/sharing/ and https://creativecommons.org/licenses/by/3.0/
- Film attribution: © copyright Blender Foundation | durian.blender.org
- Speaker model and model card: https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb
- Checkpoint: https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/resolve/main/embedding_model.ckpt
- Model checksum is pinned in validation.py; different bytes fail closed.
- Installed inference components used: SpeechBrain 1.1.1, Torch 2.8.0 CPU, TorchAudio 2.8.0 CPU, NumPy, and ffmpeg. Use trusted PyPI and the official PyTorch CPU package index. No remote model Python code or unrestricted checkpoint deserialization is needed.

Prepare the licensed masters and locally derived annotations under ../source/ using the source-preparation workflow. The code expects decoded-audio seconds and the documented 26 caption IDs. It checks actual master bytes against pinned hashes before inference; matching filenames alone are insufficient. The full annotation/transcript collection is intentionally not distributed here.

For V2, first run the boundary-audit workflow and contextual separator to produce local audit.json, boundary-proposals.json, and contextual segments_report.json. V2 checks their completeness, hashes, timebases, sample bounds, durations, and neural-file paths before use. Public evidence JSON files are not executable replacements for those richer local inputs.

Place the verified official checkpoint at embedding_model.ckpt. In an isolated environment with the dependencies installed, run verify.py, then verify_v2.py. The optional local deps/ directory is added to Python's import path if supplied by your local environment; dependencies are not published. Inference writes local raw evidence and local-only embeddings. Never add those outputs wholesale to a repository.

## Validation

From this directory:

    python -m unittest discover -s . -p 'test_*.py' -v
    python -O -m unittest discover -s . -p 'test_*.py' -v

Checks use explicit errors, not runtime assert statements, so optimization cannot disable integrity validation. Both inference scripts call the validators before checkpoint loading or waveform decoding. torch.load always uses weights_only=True, followed by strict state-dict matching.

The evidence exports were generated from completed inference before the subsequent validation-only hardening. The hardened validators were then tested against the actual local inputs under python -O, and passed. No numerical model changes were introduced. No fresh inference run is implied by the hardening tests.

export_public_evidence.py produces allowlisted scalar evidence and rejects common private-path/transcript fields. Review the exact file allowlist rather than staging the working directory recursively. The public outputs contain all 26 IDs per experiment, including quarantines; scores are not calibrated probabilities or error rates.

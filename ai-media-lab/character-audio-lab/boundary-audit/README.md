# Caption boundary audit (machine evidence, not listening)

This private audit preserves 48,000 Hz decoded-master sample coordinates. The measured caption/video offset of −44 ms was already applied in `source/target-annotations.json`; this audit adds no global offset. Each of all 26 captions receives one second of context on each side. Original stereo and verified 5.1 FC are decoded locally; available context-separated neural vocals receive the same checks.

Silero VAD 6.2.3 runs its official PyPI-bundled TorchScript model on CPU. Signals are resampled 48→16 kHz by scipy's polyphase resampler, and VAD boundaries map back by exactly ×3 to master samples. A 32 ms model analysis frame, 100 ms minimum speech/silence, and 60 ms padding make these approximate activity boundaries, not phoneme alignment. OpenAI Whisper tiny.en independently transcribes each context at temperature zero with no caption prompt and no previous-text conditioning. ASR word timestamps are model estimates, not forced alignment. Caption WER is reported only afterward. Full-context WER, caption-window WER and contiguous phrase-match WER have distinct meanings; word timestamps often stretch the first word to context start, so caption-window WER alone must not gate admission. Proper-name and short-whisper failures are not negative speaker evidence.

The first ONNX attempt was stopped after its runtime attempted Microsoft telemetry. The final runtime does not import or execute ONNX Runtime, uses the vendor's TorchScript model instead, and does not upload audio or call paid APIs. Official Whisper checkpoints are downloaded with embedded SHA-256 verification and loaded with `torch.load(weights_only=True)`. Silero TorchScript is executable vendor model code from the recognized official package, not an unrecognized pickle or remote-code hub. Both models have MIT licenses. Recorded hashes and actual runtime are in `audit.json`.

Sources:
- https://github.com/snakers4/silero-vad
- https://pypi.org/project/silero-vad/6.2.3/
- https://github.com/openai/whisper
- https://pypi.org/project/openai-whisper/20250625/

## Reproduction
Use the existing separation CPU Torch 2.8 environment read-only. Dependencies are isolated under `boundary-audit/deps`. Install official PyPI packages listed in `requirements.txt` to that directory; then run `separation/.venv/bin/python boundary-audit/audit.py` and `boundary-audit/summarize.py` from the lab parent. Run unittest discovery on `boundary-audit/test_audit.py`.

`audit.json` contains every tested signal's complete VAD regions in master samples, caption-clipped regions, RMS, unprompted ASR text, word timestamps relative to the context start, model no-speech/logprob/repetition diagnostics, and caption WER. `boundary-proposals.json` is the pipeline-facing summary. Three-or-more-word captions with WER ≤0.25 and VAD support are candidate boundary repairs only. Short utterances remain quarantined even if correctly recognized. Full contextual VAD regions are associated with the best contiguous independently decoded phrase match. Proposed boundaries can repair truncated caption onsets; any inter-proposal collision is quarantined. Center is preferred when it recovers at least70% of the longest supported activity, otherwise a supported fuller signal is selected. Complete context detections remain available for review.

No activity detector or ASR establishes character identity, absence of overlapping voices, or stem purity. All overlap values remain unknown; no human listening was performed. Do not discard ambiguous audio or promote these outputs to voice-cloning training. Audio, model weights, embeddings, and local environment files are private and must not be committed. Source scripts, tests, this README and requirements may be published through the source-only workflow.

## Actual result
All26 captions and66 signal checks completed in65.62s on CPU.12 phrase/VAD-supported proposals include5 Sintel candidates with8.28s of estimated speech, and7 Shaman candidates.14 captions stay ambiguous. This is not a usable-voice or speaker-verified duration. Examples: `Thank you` is recognized across all3 signals and center VAD spans124.978–125.482s, before the original125.206s caption start; `I have failed` spans445.642–446.818s. Existing clips therefore truncated onsets. `Get him, Scales! Come on!` benefits from the neural vocal signal, but the proper name is still mistranscribed.

## Offline source review and optimization regression

From the source snapshot root, set `LOCAL_LAB` to the existing authorized local lab with its dependency environment. No network calls, model inference, downloads, or source media are needed for these unit tests:

```sh
PYTHONPATH="$LOCAL_LAB/boundary-audit/deps" "$LOCAL_LAB/separation/.venv/bin/python" -m unittest discover -s character-audio-lab/boundary-audit -p 'test_*.py' -v
```

The unit suite launches a separate `python -O` process and verifies wrong sample rates, wrong vendor hashes, and an imported forbidden runtime still raise explicit errors. Production audit, reconciliation, and result-validation checks use explicit exceptions rather than assertions. Five tests pass. Running the results validator additionally requires the private local evidence and vendor model; it must not be pointed at a public source-only snapshot.

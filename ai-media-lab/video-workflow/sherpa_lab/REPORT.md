# Independent SenseVoice INT8 experiment

Sources verified2026-10-04:
- Runtime/docs: https://k2-fsa.github.io/sherpa/onnx/sense-voice/pretrained.html
- Official converted release: https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2
- Original model card: https://huggingface.co/FunAudioLLM/SenseVoiceSmall
- Current custom license: https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE

Local reference/learning evaluation uses FunASR MODEL_LICENSE1.1, not Apache2. Attribution and original model names retained. Exact retrieved license is saved with SHA256 in experiment manifest. License includes attribution, risk disclaimer, community-conduct provisions, and automatic updates. No explicit acceptance/payment/login step occurred. Review current license before reproducing or deploying; model weights are excluded from source deliverables.

## Actual measurements

Downloaded official archive163,002,883bytes in17.285s. Model loaded in1.071s. Runtime sherpa-onnx1.13.8, CPU4threads, INT8, forced Mandarin language, greedy decoding, inverse-text-normalization disabled. Input PCM16 mono16000Hz verified; no reference scripts/hotwords passed to recognizer. Long inputs split into fixed nonoverlapping20s chunks; boundary cuts can introduce errors. Same noisy subway crop needs no split.

- Subway17.940s: first0.673s, warm0.592s. Published-caption reference65chars;39edits,CER60%. Tiny baseline was100%. Still unacceptable for precise quotation without review.
- Cleaner interview68.413s:2.436s then2.427s. Coherent result, but not scored because no full independent speech reference. Source video nominal duration differs slightly from decoded audio duration.
- Original eSpeak narration38.033s:1.289s then1.327s. Original-script166chars;54edits,CER32.53%. Tiny baseline116.87%. Synthetic-domain roundtrip only; this is not human listening/naturalness scoring and does not isolate TTSquality from recognizer weakness.

CER independently recomputed with Jiwer and matches the standalone edit-distance implementation. Normalization exactly matches previous benchmark: UnicodeNFKC, lowercase, keep alphanumeric; no Simplified/Traditional conversion, no forced matching/correction. Token timestamps saved and range/monotonicity checked; alignment accuracy is not manually verified. Full raw outputs stay in local experiment evidence. Passing empty/repetition gates does not imply accuracy: subway passes those heuristics despite60%referenceCER.

This is a useful independent free-ASR route, with measured improvements on these samples, not proof of high accuracy across Mandarin videos. Two runs do not establish timing variance. Tiny and SenseVoice long-clip chunking differ, so those are whole-route comparisons, not controlled model-only comparisons. API spend$0; CPU/storage unpriced. No denied Whisper/Vosk endpoint was retried or bypassed.

## Reproduce

Install official sherpa-onnx and NumPy from a permitted reputable registry; record versions. Download the official model after reviewing its current custom license; do not include weights in public repository. `benchmark_sensevoice.py` uses existing saved PCM samples and references from earlier local experiments, so it is an optional evidence-dependent benchmark, not a portable default test. Its output directory must not already exist. Runtime already installed in the independent ChineseTTS lab was used read-only.

Current raw evidence: `outputs/sensevoice_int8/`; metrics-only export: `outputs/sensevoice_int8/metrics-only.json`. Existing v1benchmark/source staging remains unchanged.

## Sentence-aligned AISHELL-3VITS comparison

Latest neural preview source is37.46675s,8kHz PCM16, SHA256a2299aa5f6ca07e5775f249e0b970ed29b391887f8ab0d5162e90eb7357b8911. Resampled explicitly to16kHz; scriptSHA matches the original eSpeak script,166normalized characters. Same recognizer/settings20s chunks/no hints. Two identical recognition outputs:85edits,CER51.20%; first1.625s,warm1.416s. Original eSpeak score was54edits,CER32.53%. Neural preview therefore did not improve this independent ASR diagnostic. This does not establish a human-perceived quality ranking; voice/model compatibility and recording domain can affect ASR. Human listening remains necessary. Comparison evidence is separate under `outputs/sensevoice_aishell3_aligned/`; original benchmarks unchanged.

## Bounded third voice: Melo candidate

Original12-line script and sameSenseVoice settings, no hints. Candidate source37.817551s,44.1kHz mono, SHA25669cd0ae61abab99203d22ca156cbb02b9d0f3a13cfe7d60e3485edc8b56502e7. Explicit16kHz resampling verified. Two runs gave identical21edits/166characters,CER12.65%; inference1.497s first and1.463s warm. This improves the same-ASR diagnostic relative to original eSpeak32.53% and alignedAISHELL51.20%, though homophone errors remain and human naturalness/intelligibility is unmeasured. Exactsourcehash must be checked if packaging a regenerated voice. Raw evidence and three-voice metrics-only comparison: `outputs/sensevoice_melo_candidate/`. No modeldownloads or sourcebaseline changes in this step.

## Exact final HTMLv1.3 waveform (supersedes candidate for final-package claims)

Final sourceSHA2566ae7f1f0cde6202a7624d393551896c85dd53b0eec05606e5aa1ce8e3760f5ce,38.366667s,44.1kHz. Explicit16kHz resampling verified. SameSenseVoice options, no hints, original166character script:16edits,CER9.6386%, identical two recognition outputs; independently crosschecked with Jiwer. Inference1.195s first,1.240s warm. This exact-file result replaces the earlier candidate12.65% only when discussing the finalv1.3package; historical candidate results remain preserved. No human listening/naturalness validation. Evidence: `outputs/sensevoice_melo_final_v13/metrics-only.json`,manifest/results. HTMLworker and parent notified.

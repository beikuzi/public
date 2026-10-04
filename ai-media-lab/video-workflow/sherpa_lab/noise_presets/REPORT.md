# Two fixed audio-cleanup presets — exploratory, one noisy clip

Frozen source:17.940s PCM16mono16kHz subway announcement audio. SHA256aa3b3ea525633747247aa67d481396261a9e221aceae92a25fc3081940616f40. Published caption reference65normalized characters, not independently listened to. Parameters were predefined before either result; no tuning against the reference. Original audio and prior benchmark unchanged.

Same SenseVoice INT8/4CPUthreads/greedy/Chinese/ITNoff/no hints. Two runs per filtered waveform. Scores crosschecked with Jiwer. All WAV and PCM hashes, exact filterstrings, and timings are in preprocessing.json and metrics-only.json.

- Untreated baseline:39edits,CER60.00%; first0.673s,warm0.592s ASR.
- Speech bandpass: `highpass=f=120,lowpass=f=3800`.56edits,CER86.15%. Preprocessing0.094s; first0.712s,warm0.899s ASR. Preprocess+warm0.992s, excluding model load.
- Mild spectral denoise: `afftdn=nr=8:nf=-40:tn=1`.53edits,CER81.54%. Preprocessing0.106s; first0.487s,warm0.490s ASR. Preprocess+warm0.596s, excluding model load.

Both tested filters worsen this sample's caption-reference agreement. Keep the untreated source for this sample; do not make either filter a default. Faster output is not evidence of better recognition, and concurrent environment load plus only two runs prevents stable speed rankings. This is a single-clip exploratory result, not held-out evaluation or proof that noise reduction is generally harmful. Search stopped after exactly these two presets.

Raw hypotheses/token timestamps: outputs/sensevoice_noise_speech_bandpass/ and outputs/sensevoice_noise_mild_afftdn/. WAVs stay local, not public source. The optional benchmark script expects existing local evidence files and runtime; it is not part of portabledefault tests.

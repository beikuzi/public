# Offline SenseVoice CLI v2

## Install

Install FFmpeg/ffprobe from the official distribution/package manager. In a new scoped Python environment:

```sh
python3 -m venv .venv-sherpa
.venv-sherpa/bin/python -m pip install -r sherpa_lab/requirements-sherpa.txt
```

This route uses official sherpa-onnx1.13.8 plus NumPy2.3.5. No paid API, token or model download occurs during recognition.

Before obtaining weights, review the current custom [FunASR MODEL_LICENSE](https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE). It is **not Apache2**. The evaluated model is SenseVoiceSmall converted by sherpa-onnx, model name `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17`; attribution/model names must remain. See the official [model documentation](https://k2-fsa.github.io/sherpa/onnx/sense-voice/pretrained.html) and its [official release archive](https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2). Extract safely into a local directory containing model.int8.onnx and tokens.txt. Review archive paths and reject traversal/symlinks outside the extraction root. Weights are deliberately absent from this source bundle.

## Recognize without a reference

```sh
.venv-sherpa/bin/python sherpa_lab/recognize_audio.py /path/to/local-video.mp4 --model /path/to/reviewed-sensevoice --output outputs/new-run
```

Local MP3, WAV, and other FFmpeg-supported audio/video inputs are probed and explicitly decoded to mono PCM16 at16000Hz. URLs and embedded network protocols are blocked. Audio-free video is rejected clearly without creating an output directory. The first audio track is used. No-reference outputs have null CER/edit-distance/reference-character fields and status unverified_no_reference. Transcripts remain hypotheses, never claimed accurate merely because a heuristic gate passes.

## Optional reference scoring

```sh
.venv-sherpa/bin/python sherpa_lab/recognize_audio.py /path/to/audio.wav /path/to/reference.txt --model /path/to/reviewed-sensevoice --output outputs/new-scored-run
```

Reference must be nonempty UTF-8 and contain an alphanumeric character after normalization. It is used only after recognition, never passed as a prompt, hotword or forced alignment. Scoring normalization:UnicodeNFKC, lowercase, retain alphanumeric; no Simplified/Traditional conversion. CER is reference agreement and can exceed100% through insertions. A reference of uncertain provenance cannot establish true speech accuracy.

Output must be new; existing paths/symlinks are rejected without changing evidence. Input/reference/probe/decoding/model validation happens before output creation. A runtime inference failure after creation is marked failed in manifest; choose a new output when retrying. Manifest preserves source and decoded-wave hashes, original codec/rate, model hash/version/settings, and whether a reference was supplied. Exact token times are raw model outputs, not independently verified alignment. Long audio uses fixed20s chunks; boundary cuts may lose words. Default threads4/repeats2; override with --threads and --repeats.

## Portable tests

```sh
python -m unittest discover -s sherpa_lab -p test_recognize_audio.py -v
```

Tests need FFmpeg but no NumPy/sherpa runtime, model weights, network, or saved benchmark data. Synthetic fixtures are generated in temporary folders; model sentinel files are only path-validation fixtures and are never loaded. Tests cover optional/empty references, no audio, MP3/video probing, literal metacharacter filenames, URL and embedded-network rejection, existing/symlink outputs, missing assets, and null accuracy without a reference.

The two-noise-preset experiment is optional and depends on excluded historical local sample/reference files. Its launcher uses the current interpreter by default, or explicit --python:

```sh
.venv-sherpa/bin/python sherpa_lab/noise_presets/run.py --model /path/to/reviewed-sensevoice
```

Do not run it as a portable unit test. No historical benchmark numbers were recomputed or replaced by CLI hardening. A separate actual MP3/no-reference smoke run verified CERnull and unverified output using the already-downloaded model; it is a functionality check, not a new accuracy benchmark.

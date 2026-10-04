> 源码版提示：本文媒体与模型路径属于另行生成/下载的资产，本 GitHub 目录不包含这些文件。

# 可选神经中文试听版（v1.2）

**试听版，未经过人工可懂度/自然度验收。** 本模式保持eSpeak基线独立，不将“神经网络”或较低ASR错误率当作好听/可懂的保证。

## 文件

- `neural-aishell3-preview/demo.mp4`：新神经试听版。
- `baseline-espeak/demo.mp4`：同一源码重新渲染的机械音基线。
- 两个目录都含独立HTML、WAV、旁白稿、SRT/VTT、真实样本时间轴和测量/检查结果。
- 工作目录中的旧 `final/` 是v1.1冻结版本，v1.2 ZIP不重复打包它。历史基准仍保留在 `benchmark-history.json`。

## 运行

```bash
.venv/bin/pip install -r requirements-neural.lock.txt
.venv/bin/python render.py --backend aishell3 --model-dir /绝对路径/vits-icefall-zh-aishell3 --out neural-test
.venv/bin/python validate.py neural-test
.venv/bin/python render.py --backend espeak --out espeak-test
```

默认神经预设 `--speaker 10`，`--speed 1.0`。`--rate`仅对eSpeak生效；`--speed`仅对神经模式生效。初次运行输出目录须不存在或为空；更新自己的目录显式加 `--overwrite`。

模型权重不随ZIP分发，也不会由脚本自动下载。先从[官方模型发布文件](https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-icefall-zh-aishell3.tar.bz2)获取并解压到本地，再传入该文件夹。下载约31.6MB。程序会校验model.onnx、词典、token与三个FST的SHA-256，任何缺失/变化均拒绝加载；清单见 `provenance/aishell3-files.sha256.json`。这不是任意模型执行器。

## 同步与音量

本次是在一次加载的本地模型会话中逐句重新合成12句话，并按每句实际PCM样本数构建新时间轴。没有沿用eSpeak字幕时间，也没有简单替换整段WAV。VITS包含随机生成，重跑的语音、时长和输出哈希可能变化，但每次都会重新计时与校验。

原生音频为8kHz、单声道。整个神经旁白仅做一次全局峰值归一化至约-3dBFS，记录gain；没有逐句偷偷变速，没有声纹克隆。AAC输出重采样至48kHz以减小编码帧长造成的尾部时长量化差，**不会恢复原生8kHz音频缺失的高频**，也不是升格为高清音质。峰值归一化不等于LUFS响度达标。

## 计时

每份 `benchmark.json` 明确标记源码版本及哈希：完整端到端秒数、HTML栅格化、模型加载（含Python导入与模型文件哈希核验）、逐句推理和时间轴、音频增益、FFmpeg编码。计时不含联网安装/模型下载，不含测试/人工制作；采用本机CPU，付费API费用$0。不要用旧模型实验的推理耗时替代完整出片耗时。

## 来源与许可

- 运行时：[k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)，官方PyPI版本1.13.8，Apache-2.0。许可文本保存于 `provenance/ENGINE_LICENSE`。
- 模型：[官方AISHELL-3模型说明](https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/vits.html#aishell3-chinese-multi-speaker-174-speakers)。发布包本身未附LICENSE，因此另外将model.onnx的SHA-256与[作者模型仓库](https://huggingface.co/csukuangfj/icefall-tts-aishell3-vits-low-2024-04-06)的 `exp/vits-epoch-960.onnx` 对上。作者模型卡声明Apache-2.0；声明与远端文件元数据保存在 `provenance/`。
- 模型SHA-256：`5511d651b7840c0a93a6bbfd4afd070a2c7f39ca1ec3ff2ecd73191519bbb852`。
- 训练语料：[AISHELL-3 / OpenSLR 93](https://www.openslr.org/93/)标注Apache License v2.0。
- 未发现单独的输出许可声明；上述引擎/模型/语料许可不构成对所有下游用途的法律担保。没有下载语料，没有模仿或克隆指定真人，使用的是已有多说话人模型的编号预设。

## 质量状态

早期独立候选音频的Whisper-tiny原始CER约74.70%，eSpeak为116.87%；两者都很差，且CER混有ASR能力、机械音适应性及繁简差异，不能将其视为真人可懂度分数。该早期候选不是本目录重新随机合成的精确波形。本新波形的独立ASR诊断另行进行，完成前保持“待诊断/未人工验收”标记。技术QA通过仅覆盖音视频编码、同步、字幕结构、非静音/不削波与画面布局。

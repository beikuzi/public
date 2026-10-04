# v1.3：Melo 中文神经配音试听版

**试听版，未经过人工可懂度/自然度验收。模型与代码许可为 MIT；审阅到的上游资料未公开中文训练数据的组成及完整授权来源，不能宣称已完成全面商业授权清理。** 本次是有明确限制说明的技术评估，不推荐未经进一步审查直接部署商业配音服务。

## 快速打开

`neural-melo-preview/demo.mp4` 是新试听版；`baseline-espeak/` 和 `neural-aishell3-preview/` 保持先前实测输出及原始版本标记不变。三者有各自独立的字幕与采样计时。旧成片不因源码升级而重新标成v1.3。

## 可复现运行

```bash
.venv/bin/pip install -r requirements-neural.lock.txt
.venv/bin/python render.py --backend melo --model-dir /本地路径/vits-melo-tts-zh_en --out melo-test
.venv/bin/python validate.py melo-test
```

官方权重不打包，也不会自动下载。[官方sherpa-onnx模型包](https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-melo-tts-zh_en.tar.bz2) 约167MB压缩，使用其中约170.4MB的浮点 `model.onnx`。默认预设 `--speaker 0`、`--speed 1.0`；2个CPU推理线程，无GPU。模型、词典、tokens、3个FST和发布包LICENSE都按 `provenance/melo-files.sha256.json` 校验，不接受任意模型。

句子在同一个已加载模型会话中逐句重新合成，再按每句实际PCM样本数生成SRT/VTT、分镜时长。没有复用别的声音的时间轴。原生采样率44.1kHz；全片仅统一峰值归一化至-3dBFS，AAC输出48kHz。没有克隆真人。VITS随机性可能改变重跑结果，因此每次都重建时间轴并保存源码/模型哈希。

`neural-melo-preview/benchmark.json` 给出此次完整HTML到视频耗时，区分HTML渲染、模型加载/核验、逐句生成与编码。没有付费API。机器、模型下载、依赖安装、制作人工仍有成本，不能把$0 API当作零总成本。

## 许可、数据与来源

- [官方转换模型与运行说明](https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/vits.html)：官方GitHub发布包内 `LICENSE` 为MIT，保存于 `provenance/melo/CONVERTED_MODEL_LICENSE`。
- [上游MeloTTS](https://github.com/myshell-ai/MeloTTS) 与 [MeloTTS-Chinese模型卡](https://huggingface.co/myshell-ai/MeloTTS-Chinese)：MIT声明，保存于 `provenance/melo/UPSTREAM_LICENSE` / `UPSTREAM_MODEL_CARD.md`。
- sherpa-onnx 1.13.8运行时为Apache-2.0；代码包中只附许可和来源，不分发第三方运行时、字体或模型权重。
- **中文训练语料及其完整授权链未在审阅资料中披露。MIT模型声明不自动解决所有训练数据、人格权或商业下游风险。** 本次许可核查不构成法律意见。

## 质量解释

早期独立Melo候选，在同设置的SenseVoice回译下，166个规范化参考字的CER为12.65%（21次编辑），低于同一诊断中的原eSpeak32.53%、AISHELL试听版51.20%。这只是该ASR系统更易识别，不能证明真人听感、自然度或所有中文内容都更好。

本目录为重新逐句随机生成的新波形，已经用相同SenseVoice设置独立回译：**16/166次编辑，CER 9.64%**，冷/暖两次识别文本一致，已与另一实现交叉核对编辑距离。评测前将实际44.1kHz音频正确重采样为16kHz；无参考稿提示，20秒固定切块。精确来源与设置见 `neural-melo-preview/quality-diagnostic.json`、`quality-diagnostic-manifest.json`。

新成片旁白SHA-256为 `6ae7f1f0cde6202a7624d393551896c85dd53b0eec05606e5aa1ce8e3760f5ce`。对应成绩是9.64%，不要继续引用旧候选的12.65%。这个结果支持“在此ASR诊断中比已测基线更易识别”，不支持“真人听感/自然度已验证”。**无论ASR分数如何，本试听版都没有经过真人听审。**

诊断使用的SenseVoice模型及其授权是独立事项，不属于TTS的MIT声明；本包只保存诊断结果，不打包或提供该ASR模型的商业授权。

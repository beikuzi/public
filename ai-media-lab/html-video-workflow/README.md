# 文字 → HTML 分镜 → 视频：低成本可复现工作流

验证日期：2026-10-04。附带一条原创的 38.03 秒中文演示片，四页 HTML/CSS/SVG 分镜、真实本地合成旁白、烧录字幕与独立 SRT/VTT。无需录屏，无需付费 API，无需 GPU。

## 先看结果

- `final/demo.mp4`：1280×720，30 fps，H.264/yuv420p + AAC，支持 fast-start。
- `final/contact-sheet.jpg`：从成片抽取的四页预览。
- `final/slides.html`：实际渲染的原始 HTML，图形内联，无远程字体或素材。
- `project.json`：修改标题、卡片文案、配色、逐句旁白的入口。
- `final/narration.wav` / `.txt`：完整声音与稿件。
- `final/subtitles.srt` / `.vtt`、`final/timing.json`：同源字幕与时间轴。
- `final/benchmark.json` / `validation.json` / `ffprobe.json`：实测数据与验证证据。

旁白是 eSpeak-NG 的 Mandarin `cmn` 合成音，通过官方 PyPI `piper-tts` wheel 内附的 eSpeak 库生成。**没有调用 Piper 神经模型，也没有克隆任何人的声音。声音明显机械，适合验证流程，不代表成片级中文配音。**

## 快速运行

已验证平台：Linux x86_64、Python 3.12、FFmpeg 7.1.5、Poppler、Noto CJK 字体。需要系统已安装 FFmpeg（libx264、AAC、libass）、`pdftoppm`、Pango 等 WeasyPrint 系统依赖及 Noto Sans CJK SC。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
.venv/bin/python render.py --out output
.venv/bin/python validate.py output
```

本目录已经有安装好的 `.venv`；交付 ZIP 不包含它。安装需要联网；**安装后渲染完全离线**，没有模型下载、云 API 或浏览器依赖。锁文件固定本次安装版本；不是跨操作系统二进制复现保证。

模板源码版本：1.1.0。旧版实测保存在 `benchmark-history.json`，当前版本的实测和源码哈希见 `final/benchmark.json`。

CLI：`--rate 225` 调整 eSpeak 语速；`--threads 4` 控制编码线程；`--preset veryfast` 调整 x264 速度/压缩率；`--out` 选择输出目录。默认拒绝非空输出目录；`--overwrite` 仅允许更新带有本流程标记的目录，且目录必须在项目下、不能经过符号链接。不要将手工编辑的重要文件放进去。

若中文显示为方块，先检查 Noto CJK 字体；若安装报 Pango 缺失，参照 [WeasyPrint 官方安装说明](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation) 补齐对应系统依赖。依赖安装不是渲染耗时的一部分。

## 为什么快

1. AI 或人写 `project.json`，把内容切成四页、每页三句。
2. HTML/CSS/SVG → WeasyPrint PDF → Poppler PNG，每页只渲染一次。
3. 逐句合成音频，按真实采样数计算起止时间，同步生成 SRT/VTT。
4. FFmpeg 复用四张图片，添加淡入淡出，编码并烧录字幕。

38.03 秒 × 30fps = 1141 帧，但 HTML 只栅格化四次；其余帧是图片复用。避免了 1141 次浏览器画面求值，不过这不是实测“比 Remotion 快多少”的对照结论。

### 功能边界

本方案适合 PPT 式讲解、知识卡片、产品说明和批量信息视频。它是 HTML/CSS 排版后的视频合成，**不是任意网页录制器**：WeasyPrint 是打印排版引擎，不执行 JavaScript，不播放 CSS 动画、Canvas、WebGL 或网页交互。本示例真正变化的画面效果是 FFmpeg 淡入淡出；角色与排版没有逐帧动画。源 HTML 外部资源加载被显式禁用。

首次尝试使用保持 sandbox 开启的 Chromium 做离线渲染时，运行环境不允许所需 socket；未关闭 sandbox 或修改安全设置。已验证替代路线完全不需要浏览器。

## 实测与成本

本次机器可用约 9 个 CPU、9.7GiB 内存；编码使用 4 线程、无 GPU。v1.0 首次完整渲染约 8.90 秒、最终一次为 7.241 秒；v1.1 当前版本的精确耗时见 `final/benchmark.json`（依赖已安装、系统缓存可能热）。

费用：付费 API 调用 **$0**；软件没有按视频收取的调用费用。这不等于零总成本：未计入订阅、机器、人工、安装时间、电费或商业发行可能涉及的编码专利费用。若按假设 $0.10/机器小时计，8.90秒纯渲染时间约 $0.00025；这只是算术示例，**不是本环境价格或账单**。批量时另算排队、启动、储存与带宽。

验证内容：H.264/AAC、720p、30fps、1141 帧、所有 12 条字幕单调且落在对应音频/分镜范围、音频非静音、PCM 未满幅削波、A/V 终点差小于一帧、四张成片中间帧逐页检查。字幕为句级对齐，时间由该句 WAV 的全部长度得出（含引擎自带首尾静音），不是词级强制对齐。未进行真人听审，不能保证 eSpeak 每个汉字的声调/多音字都读对。随后用本地 Whisper tiny 对最终旁白进行无文本提示回译，规范化字符错误率为 116.87%（插入错误会使 CER 超过100%），出现重复误识别：**自动语音质量关卡未通过**。小模型也可能不适应这种机械音，这不能独立证明真人听不懂；但本音色不应作为正式配音交付，需真人试听或替换更好的合法TTS后再验收。视频技术合成与字幕结构验证通过不等于语音可懂度通过。

## 三条路线怎么选

| 路线 | 适合 | 能力/代价 | 授权与当前费用 |
|---|---|---|---|
| 本示例：HTML + WeasyPrint + FFmpeg | 低成本批量 PPT 型短视频 | 静态排版，一页渲染一次；复杂动画另做 | WeasyPrint BSD；FFmpeg 默认 LGPL，但本机启用 GPL/libx264；无按次软件费 |
| [Remotion](https://www.remotion.dev/) | 复用 React/HTML/CSS、产品化视频模板、复杂逐帧动画 | 强表达力、时间轴驱动；渲染与部署成本另算 | Source-available，非 OSI 开源。个人及符合条件的≤3人团队免费。公司自动化 $0.01/render、$100/月最低消费；Creators $25/席/月，组合最低消费规则看官方 FAQ |
| [Motion Canvas](https://motioncanvas.io/) | 图解、代码动画、技术可视化 | TypeScript + 自己的 Canvas 场景系统，不是把任意 DOM 原样转视频；有官方 FFmpeg 导出器 | 当前仓库主分支 MIT，免费；机器与开发成本另算。曾有改 GPL 的讨论，不能把讨论当当前许可 |

建议：先用本示例验证批量内容与节奏；需要元素级动画、React 组件复用时考虑 Remotion；以图解动画为主时考虑 Motion Canvas。两个框架本次只做文档/许可证核查，**没有实机性能对比**。

来源：[Remotion 价格](https://www.remotion.pro/license)、[Remotion License FAQ](https://www.remotion.dev/docs/license/faq)、[Motion Canvas 当前 LICENSE](https://github.com/motion-canvas/motion-canvas/blob/main/LICENSE)、[Motion Canvas FFmpeg 导出](https://motion-canvas.io/docs/rendering/video/)、[WeasyPrint 说明与 BSD](https://doc.courtbouillon.org/weasyprint/stable/)、[FFmpeg 许可/专利说明](https://ffmpeg.org/legal.html)。价格、团队口径与许可证以使用时版本为准；本表不是法律意见。

## 配音升级路径

- **本次已跑通：eSpeak-NG**。完全本地、无需 API 额度，速度快、体积小；中文机械感强，声调和多音字需人工检查。引擎是 GPL，查看 [eSpeak-NG LICENSE](https://github.com/espeak-ng/espeak-ng/blob/master/COPYING)。本项目通过 [Piper 官方 PyPI 安装方法](https://github.com/OHF-Voice/piper1-gpl) 使用它内附的库。
- **Azure 官方神经中文声音**：官方支持 `zh-CN-XiaoxiaoNeural`、`zh-CN-YunxiNeural` 等。页面列出 F0 每月 50 万字符免费额度，需要账户与相应区域可用性；付费单价网页在本次抓取中为动态占位符，因此不虚报固定单价。见 [声音列表](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts)、[官方价格](https://azure.microsoft.com/en-us/pricing/details/speech/)。本次未开账户、未调用。
- **OpenAI TTS**：当前 GPT-4o Mini TTS 模型页列出每百万文本输入 token $0.60、每百万音频输出 token $12，但本次官方页同时标记 Deprecated；选择前需确认当前可用模型与迁移方案。见 [模型与价格](https://developers.openai.com/api/docs/models/gpt-4o-mini-tts)。不能将 token 单价写成固定每分钟费用。本次未调用或付费。
- **Piper 神经中文模型**：Huayan 的 MODEL_CARD 明确写数据集许可 Unknown，不能因模型仓库顶层写 MIT 就宣称可无条件商用；本交付不包含也不使用该模型。见 [精确模型卡](https://huggingface.co/rhasspy/piper-voices/blob/main/zh/zh_CN/huayan/medium/MODEL_CARD)。

升级时最稳的是保留“每句单独音频 → 用真实长度构建时间轴”接口；不要换成按字数估时。若生成整段自然旁白，需要另加句/词级强制对齐；API 带时间戳时也应检查输出与实际语音是否一致。

## 许可与可复用性

原创新增 Python、JSON、HTML/SVG 内容由本项目提供；`LICENSE` 为本项目代码的 GPL-3.0-or-later 许可声明，以兼容这里加载的 GPL eSpeak/Piper 库。第三方软件、字体和编解码器保留各自许可。本 ZIP 不分发第三方二进制、wheel、神经模型或字体。交付演示内容与角色为原创，无第三方视频、私人数据或品牌角色素材。

## 输入限制与回归测试

`project.json` 是受限的自有可信内容结构，不接收任意HTML或远程网页。固定四页、每页三张卡片；标题至多两行、每行八个字符，卡片正文至多二十字符，旁白每句至多三十字符、每页一至四句。拒绝空旁白、控制字符、HTML标记、URL/资产字段和非法CSS颜色；HTML文本还进行转义。WeasyPrint的资源加载器拒绝所有外部资源。预算是保守的固定模板约束，不是对任意字体/复杂Unicode的像素溢出证明；更换模板仍需抽帧目检。

```bash
.venv/bin/python -m unittest test_pipeline -v
.venv/bin/python render.py --out output-new
.venv/bin/python validate.py output-new
# 仅更新自己已生成的目录
.venv/bin/python render.py --out output-new --overwrite
```

七项回归测试覆盖正常结构、空旁白、超长内容、HTML/URL/CSS注入、危险路径、非空/非目录/符号链接输出、内联HTML。成片验证另检查所有字幕单调、分镜内边界和音视频帧数。

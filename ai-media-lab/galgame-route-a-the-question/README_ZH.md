# 路线 A：The Question 原资源参数重组基线

这是三条路线共用的完整短篇测试作品，来自官方 Ren'Py 8.5.3 SDK；它只作为独立的受控比较案例。已完成的 KS 第一章 Demo 路线 A 保持独立。

共同前提：52/52 原始 .rpy 文件已由共同索引流程覆盖；本路线使用其版本固定的场景契约，不把 KS、旧引擎或其他发行版的素材混入。

## 本片

32 秒，1280×720，24 fps；英文原文，原 BGM，没有配音。

场景是 `marry` 标签前半段，book=False，对应先选“To ask her right away.”、再选“It's a videogame.”的路径。画面依次为黑场旁白、club 背景、Sylvie blue normal、Sylvie blue giggle。目标为第 188 行的“Will you marry me?”。book=True 才显示的第 173 行没有混入。

全部画面资源直接取自官方 SDK：原背景、原人物差分、原透明渐变对白框、原透明姓名框、DejaVuSans 字体和快速菜单样式。没有生成图片，没有独立设计对白框。

## 精确度边界

这是代码重组，不是原引擎录屏，不宣称像素级一致。

- 背景、人物图像、字体文件、UI PNG、颜色、位置和字号均有源文件映射。
- Pillow/FreeType 渲染替代 Ren'Py，文字的基线、字距、抗锯齿和按钮计算可能不同。
- 本片的停留秒数是剪辑设置。原作文字速度默认 0，即整句显示，本片保持即时显示。
- 两处 dissolve 为代码近似。转场时对白保留方式尚未逐帧验证。
- 原 BGM 从其文件开头播放，未声称匹配真实游玩到该段时的音频偏移。
- 快速菜单仅是画面组成，不可点击；本视频不存在游戏交互。

## 文件

- route-A-the-question.mp4：32 秒片段
- target-frame.png：重组目标帧
- contact-sheet.jpg：6 个时间点预览
- SCENE_ASSET_MAPPING.json：共同契约、素材哈希、UI 数值与覆盖范围
- QA_REPORT.json：验证结果及已知差异
- route-A-source-no-game-assets.zip：仅工具、说明、许可和映射；不含完整剧本/原素材

## 本地复现

需要同一份官方 Ren'Py 8.5.3 SDK、Python、Pillow、FFmpeg。tools/render.py 从同级 galgame-text-pipeline/vendor/renpy-8.5.3-sdk 读取，先核对 script.rpy SHA-256，再按行读取这 8 条短节选。

运行：python tools/render.py --stills；python tools/render.py。

## 原作署名与许可

Updated Character Art: Deji
Original Character Art: Derik
Updated Background Art: Mugenjohncel
Original Background Art: DaFool
Music: Alessio
Updated writing: Lore
Original writing: mikey (ATP Projects)
Ren'Py: Tom Rothamel and contributors

SDK LICENSE.txt 说明 Demo 美术由各作者按同样条款发布。随附原 LICENSE.txt 与 DejaVuSans 字体许可；软件依赖仍保留各自许可。这里只提供短节选与工具，不重发完整游戏或素材包。

官方：https://www.renpy.org/
版本下载：https://www.renpy.org/release/8.5.3

## 与真实引擎的对照

已与路线 C 正常 UI 游玩获得的第 188 行截图比较。真实截图为 1180×663，A 原生为 1280×720，比较时按同尺寸缩放，不能把误差指标解释为原生逐像素一致。根据对照校准文字基线，目标处 Skip/Q.Load 按原状态显示不可用。背景、角色和原 UI 布局相符；字形栅格化、缩放采样和部分字距仍有差异。参见 engine-vs-recomposition.jpg 与 COMPARISON_METRICS.json。


## Public closeout snapshot · 2026-10-06

This is an archive of already-completed experimental source. Only source, licences and limited technical coverage/QA records are published. Videos, screenshots, game assets, full scripts and scene-text mappings are excluded. Historical verification claims retain their original scope; closeout checked source syntax, JSON validity and publication boundaries only, without rerunning games or adding features. Paths referring to private inputs must be prepared separately from legally obtained matching editions.

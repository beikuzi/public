# 路线 A：原素材、原界面参数重构

本交付只验证官方第一章 Act 1 v5 Demo 这一特定版本，不代表全游戏剧本已读取，也不是后续完整游戏版本的最终工作流。

成片为 90 秒、1280×720、24 fps。游戏内容保持原生 800×600 的 4:3 构图，等比放大到 960×720，左右各留 160 像素黑边；没有把原画裁成 16:9。

## 这次真正改了什么

- 用官方 Demo 的 `ui/bg-say.png` 替换旧片自绘圆角对白框。
- 用官方中文 `font/wqy-microhei.ttc`，按照原设定 22 像素、70 字/秒、对白窗口高 160、原 padding 与缩进排字。旁白不再添加“久夫·内心旁白”名签；只有真正发言的第 2173 行出现久夫姓名及原配色。
- 人物只用原 PNG 差分，不生成、不重画；夜景使用原作 night 函数的饱和度和 RGB tint 矩阵。
- 恢复脚本真实的画面顺序。第 2103 行只有星空，旧片擅加的屋顶和角色已经移除。保留原作双手背后→张臂→缩成剪影→城市/山丘→烟花→双人剪影的变化。
- 城市、山丘、烟花全部是原素材，按脚本层级与坐标使用。不是另绘一张“类似 CG”；本段本来就是多层合成演出，没有另外编造单张 CG。
- 取消原片里的额外调色、自由推拉镜头、仿电影字幕、进度线和台词外感想。最后 4 秒是独立署名卡。

## 真实边界

这是代码合成，不是实机录屏，也不宣称与 Ren'Py 输出逐像素相同。

图像与界面资源来自原作，布局及演出数值来自官方包内脚本；Pillow/FreeType 代替旧 SDL_ttf 排字和栅格化，换行、粗体和抗锯齿可能有细微差异。烟花按原状态机概率、间隔及原噪声遮罩复现，但用固定随机种子，因此具体每发烟花不同于一次真实游玩的随机结果。缩放及 alpha 混合也由不同渲染器完成。初始星空取原 Fullpan 的右端状态；省略台词后的镜头停留时长是剪辑选择。只有真实引擎录制才能验证更强的“原游戏实际画面”一致性。

7 条中文原文与前一版本完全相同，均来自同一场景、保持原顺序；原文之间有删节。剪辑停留、删节、署名卡和收尾音频淡出属于编辑处理。保留原音乐/烟花音效的进出顺序，不把整段改成连续背景音乐。

## 复现与安全

官方 Act 1 v5 Linux Demo：
https://www.katawa-shoujo.com/download

本次获取的官方 CDN 文件为 189876864 字节，SHA-256：
2c1c95aa8c23968a458c5c9cab4a6d337f0c61093172ea925cc4412bef772e8a

资源通过严格只读 RPA 解析器提取，RPYC 只解析惰性 AST，不调用 pickle.load/loads，不执行还原的 Python/游戏脚本。16 项安全测试通过。原下载/解压基底未修改。原包内 32 位 Python 启动器仅作 `-V` 可运行性探测，当前环境返回 Exec format error；本路线没有假冒已经运行游戏。

源码包不包含游戏、原始素材包或完整剧本。复现需要自行取得同一官方 Demo，按清单在本地提取所需素材。

## 署名与使用边界

原作 Four Leaf Studios；原音乐 Blue123 / Nicol Armarfi；简体中文 arroz / janz / echo / leon 及完整本地化团队。完整署名见 ORIGINAL_CREDITS.txt。

本片是非官方、非商业、免费粉丝节选。基础 CC BY-NC-ND 3.0 与官方后来公布的免费粉丝作品/技术重制许可说明须一并阅读。官方 2022 年更新要求免费并保留署名；2024 年说明非官方修改版须注明非官方，且允许直播。个别作者对其作品仍保留权利。未授予任何商业使用许可。

官方说明（本次重新获取验证）：
https://ks.fhs.sh/viewtopic.php?f=13&p=248149


## Public closeout snapshot · 2026-10-06

This is an archive of already-completed experimental source. Only source, licences and limited technical coverage/QA records are published. Videos, screenshots, game assets, full scripts and scene-text mappings are excluded. Historical verification claims retain their original scope; closeout checked source syntax, JSON validity and publication boundaries only, without rerunning games or adding features. Paths referring to private inputs must be prepared separately from legally obtained matching editions.

# 抬头，看见此刻

《Katawa Shoujo / 片轮少女》第一章 v5，静音线祭典夜景。90 秒，1280×720，24 fps，简体中文，原作 BGM 与烟花音效。

## 这是什么

这是**非官方、非商业、经过删节的代码重构短片**，不是实机录屏，也不是原作逐帧复刻。它使用从官方免费 Demo 读取的图像、原场景音乐、七条简体中文原文，重新安排镜头、文字出现时间、夜色、转场和烟花动画。未生成角色图像、未配音。片头背景介绍和结尾「片段读后」为编辑文字，明确与原作台词区分。

选择这一段，是因为它有完整的情绪递进：内疚与忧郁 → 静音无声地展开双臂 → 看见眼前景色 → 烟花 → 重新感到温暖与活力。保留的七条原文在对应英文中共 128 词。它不是整场戏、完整路线或游戏替代品。

曾比较的候选：
- 周六琳的壁画：关于灵感、创作以及「没有想法」是否也是一种想法，哲学性强。
- 周三美术室：不同人的问题与相互理解。
- **最终选择周日静音的屋顶与烟花**：更符合「励志＋人生哲理」，也更适合用真实原作美术做视觉演出。

## 文件

- `katawa-shoujo-look-up.mp4`：成片
- `SOURCE_MANIFEST.json`：来源、版本、SHA-256、许可边界与原文定位
- `ORIGINAL_CREDITS.txt`：完整保留 Demo 内原作及中文本地化署名
- `workflow-source.zip`：可复现代码，**不包含游戏、解包素材或完整剧本**

## 合法来源与边界

官方获取页面：https://www.katawa-shoujo.com/download

官方发布者备用页面：https://4leafstudios.itch.io/katawa-shoujo

官方许可与粉丝作品说明：https://ks.fhs.sh/viewtopic.php?f=13&p=248149

基础游戏是 CC BY-NC-ND 3.0，**免费不等于公有领域，也不等于通用开放素材**。官方 2022 年 11 月说明另行允许免费粉丝作品、技术重制和模组，要求保留署名；每位作者仍可决定其具体作品的使用。2024 年 8 月官方 FAQ 说明直播无版权限制，同时要求修改版本在 Steam 外发布时注明非官方。

本次在该范围内制作限量节选，非商业、不收费，保留署名及官方获取入口。请勿把完整游戏、完整剧本、原始美术/音乐包放进公开仓库。任何后续商业用途或作者明确反对的用途，须另行解决授权；本项目不授予游戏素材的新许可。

## 技术路线与真实执行状态

1. 从官方链接下载 Act 1 v5 Linux Demo，核对固定 SHA-256，安全解开 tar。
2. 阅读 GitHub 的 `shizmob/rpatool` 和 `CensoredUsername/unrpyc` 文档，确认 RPA/RPYC 分工及版本限制。
3. **没有运行这两个 GitHub 工具。** 未经逐次批准的未知仓库执行路径被跳过，改用本项目自写的严格只读解析器。
4. RPA 索引使用原始数据指令解释器，不调用 `pickle.load/loads`。RPYC 只作惰性数据与字符串检查，不执行 Ren'Py、Python 或反序列化函数。拒绝 REDUCE、扩展、持久 ID、未知全局、目录穿越及符号链接。
5. 精确选择原场景相关图片与音频；Pillow 合成镜头，FFmpeg 编码 H.264/AAC。
6. 安全测试覆盖恶意 pickle、索引路径、界限、符号链接与拒绝覆写。仅支持本 Demo 的旧式 zlib RPYC；这不是可解任意游戏、加密归档或 DRM 的万能工具。

原 Ren'Py 源码参考：下载包内 `renpy/loader.py`、https://github.com/renpy/renpy/blob/master/renpy/loader.py

GitHub 工具参考（仅阅读）：
- https://github.com/shizmob/rpatool （该镜像已归档，维护迁往 Codeberg）
- https://github.com/CensoredUsername/unrpyc （v2 对旧引擎版本存在限制，不能假定本 Demo 直接兼容）

## 复现

已在 Linux、Python 3.12.14、Pillow 12.3.0、系统 FFmpeg 与 Noto Sans CJK 字体下验证。归档提取器需要 POSIX 的 O_NOFOLLOW 支持。字体默认采用 Debian/Linux 路径；其他路径可通过 render_clip.py 的 --font 和 --bold-font 指定。所有命令仅操作你指定的本地目录。渲染器会覆盖指定的同名输出视频；解析器和游戏准备工具不覆盖已有文件。

```sh
python tools/prepare_demo.py --destination ./local-game
python tools/render_clip.py \
  --game './local-game/Katawa Shoujo Act 1 v5-linux-x86/game' \
  --work ./local-work \
  --output ./look-up.mp4
python -m unittest discover -s tools -p 'test_safe_renpy.py' -v
```

已有官方压缩包时，prepare_demo.py 支持 `--archive`，不会重复下载。运行前阅读 `tools/README.md`。原图、原文和原音频始终留在你本地；分发代码时不附带它们。

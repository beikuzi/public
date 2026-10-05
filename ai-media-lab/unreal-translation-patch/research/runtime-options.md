# Unreal 游戏实时翻译补丁：调研与可验证边界

调研时间：2026-10-05。只读检查公开仓库、源代码和官方文档；没有下载/运行第三方 DLL、安装到游戏、注入进程或验证真实游戏效果。

## 结论

最接近 XUnity.AutoTranslator 需求的已找到项目是 [UE-RealtimeTranslationMod](https://github.com/shuipingbai6/UE-RealtimeTranslationMod)，它确实包含 UE4SS 运行时文本捕获、异步翻译和回写代码。但它是早期项目，不能作为“全部 UE4/UE5 游戏即放即用”的证据。当前交付应定位为：可测试的翻译桥接服务 + 已有运行时组件的实验性接入方案；完整游戏内补丁仍需选定游戏验证。

## 候选对比

| 项目 | 实际作用 | 许可 / 最近 push（GitHub 元数据） | 判断 |
| --- | --- | --- | --- |
| [UE4SS-RE/RE-UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) | UE4/5 Lua/C++ mod 加载、反射和钩子基础设施 | MIT；2026-10-02 | 不是翻译器。当前 main 声称目标 UE 4.7–5.8，明确说明并非所有游戏即插即用；发布版能力须单独核对。 |
| [shuipingbai6/UE-RealtimeTranslationMod](https://github.com/shuipingbai6/UE-RealtimeTranslationMod) | ProcessEvent 文本捕获、UI 属性扫描、缓存、API 翻译、SetText 回写 | GPL-3.0；2026-03-29 | 最相关的运行时原型，需审计/兼容修正/游戏实测。 |
| [LabrynthKing/TranslationHelper](https://github.com/LabrynthKing/TranslationHelper) | Subnautica 2 mod 作者使用的 JSON 本地化 API | AGPL-3.0；2026-08-27 | 特定游戏/mod 集成，不是自动翻译所有游戏文字。 |
| [Taktloss/uetrans](https://github.com/Taktloss/uetrans) | Life is Strange 的 CSV 与 .GER 文本转换 | 未找到仓库许可；2015-06-10 | 搜索 UnrealEngineTranslator 得到的旧项目；代码为离线文件处理，不是现代 UE4/5 通用运行时翻译。 |
| [akintos/UnrealLocres](https://github.com/akintos/UnrealLocres) | locres 导出、导入、合并 | GitHub 未识别许可；2021-10-24 | 离线本地化资源工具，文档声明读取/写入 locres 版本至 3。不要据此宣称覆盖所有未来 UE5 格式。 |
| [atenfyr/UAssetGUI](https://github.com/atenfyr/UAssetGUI) | 编辑/导入导出 Unreal .uasset | MIT；2026-08-31 | 离线资源编辑；需匹配版本，部分资源需 mappings；不提供实时屏幕文本捕获。 |
| [4sval/FModel](https://github.com/4sval/FModel) | 浏览、解析、导出 UE 资源 | GPL-3.0；2026-10-04 | 资源调查辅助；不是文本回写运行时补丁。 |
| [gildor2/UEViewer](https://github.com/gildor2/UEViewer) | Unreal 视觉资源查看/导出 | MIT；2024-03-16 | README 声称 UE1–4，不应将它当成已验证 UE5 翻译器。 |
| [HIllya51/LunaTranslator](https://github.com/HIllya51/LunaTranslator) | HOOK、OCR、翻译界面；部分游戏支持嵌入 | GPL-3.0；2026-10-03 | OCR 可作为独立备选，UE 游戏内原位替换不是其通用保证。 |

“最近 push”只代表仓库活动时间，不代表安全审核、支持承诺或发布质量。对无许可证项目，不复制/重新分发其源代码。未发现名称精确为 UnrealAutoTranslator 的明确现代仓库；这是本次搜索结果，不是不存在任何相关项目的证明。

## 运行时候选：实质代码核查

检查版本：[b4e2e11db91a37351a99e7c8f46d3862383f9dd5](https://github.com/shuipingbai6/UE-RealtimeTranslationMod/commit/b4e2e11db91a37351a99e7c8f46d3862383f9dd5)。

- [TextHookManager.cpp](https://github.com/shuipingbai6/UE-RealtimeTranslationMod/blob/b4e2e11db91a37351a99e7c8f46d3862383f9dd5/src/TextHookManager.cpp)：注册 ProcessEventPre 回调，通过函数名称筛选 SetText、K2_SetText 等，遍历反射参数提取 FText/FString；缓存命中时修改 FText 参数。不是通用 FText::ToString 底层拦截，也不是 Slate 全覆盖。
- [UIPropertyScanner.cpp](https://github.com/shuipingbai6/UE-RealtimeTranslationMod/blob/b4e2e11db91a37351a99e7c8f46d3862383f9dd5/src/UIPropertyScanner.cpp)：按类名/属性名启发式扫描 widget；跳过已扫描地址，限制文本长度 2–500。直接修改 FText/FString 属性不能证明所有 Slate 渲染缓存都刷新。
- [TextApplicator.cpp](https://github.com/shuipingbai6/UE-RealtimeTranslationMod/blob/b4e2e11db91a37351a99e7c8f46d3862383f9dd5/src/TextApplicator.cpp)：反射查找 SetText/K2_SetText，构造单个 FText 参数进行 ProcessEvent。异步队列保存原始 widget 指针，未见写入前验证对象仍存活、地址未复用以及当前文本仍与原文相同；有陈旧结果覆盖/生命周期风险。
- [TranslationMod.cpp](https://github.com/shuipingbai6/UE-RealtimeTranslationMod/blob/b4e2e11db91a37351a99e7c8f46d3862383f9dd5/src/TranslationMod.cpp)：在 EngineTickPost 处理回写及扫描；配置位置依赖进程 current_path，而非 DLL 所在路径。声明 ModIntendedSDKVersion 为 2.6。
- [AIProvider.cpp](https://github.com/shuipingbai6/UE-RealtimeTranslationMod/blob/b4e2e11db91a37351a99e7c8f46d3862383f9dd5/src/AIProvider.cpp)：发送 OpenAI 风格 chat-completions JSON + Bearer token；自身没有百度通用翻译的 appid/salt/sign 协议。可通过本地 HTTP 适配器转换。它的 IsConfigured 要求 endpoint、key、model 均非空。
- AI 响应使用手写字符串解析，Unicode 转义等边界需测；反射回写重新经过钩子，需测重入/二次翻译；没有充分的对象生命周期保障。以上是静态代码检查发现的风险，未通过运行复现。
- **安全阻断项**：[NetworkClient.cpp](https://github.com/shuipingbai6/UE-RealtimeTranslationMod/blob/b4e2e11db91a37351a99e7c8f46d3862383f9dd5/src/NetworkClient.cpp) 为 HTTPS 设置忽略未知 CA、证书日期和域名错误的 WinHTTP 标记。不要向未经修复的该组件提供真实云端密钥，也不要直接连接外部 API。研究用 loopback 适配器只能降低凭据暴露风险，不能把该 DLL 自动变成经过安全验证的软件。
- **保存策略阻断项**：[VocabularyCache.cpp](https://github.com/shuipingbai6/UE-RealtimeTranslationMod/blob/b4e2e11db91a37351a99e7c8f46d3862383f9dd5/src/VocabularyCache.cpp) 存在后台保存及析构保存；TranslationMod 的关闭路径还直接调用 Save。设置 auto_save:false 不能保证完全不落盘，调试日志也可能包含原文/译文。百度返回结果的持久保存/再分发许可未确认前，不应把百度接到这一未修复的运行时组件。

### 官方发布物存在，但未验证可用性

[beta 发布页](https://github.com/shuipingbai6/UE-RealtimeTranslationMod/releases/tag/beta) 发布于 2026-03-29，标记 prerelease，包含 RealtimeTranslationMod.dll 及一键安装 EXE。GitHub API 提供的 DLL digest 是 sha256:583485fd0c6ac03da573228650ac60fb0a6b7ea0b77dd6217955dbeaa191157b；本次未下载字节，不能声称独立核对过散列或安全性。较早发布标题直接包含 Alpha-untested。

本次检查 README、发布说明、issues，没有找到可引用的具体游戏+版本+引擎+测试结果矩阵。不要把 UE4SS 支持某个游戏误当成翻译 mod 已经支持该游戏。

### 安装文档冲突必须解决

运行时 README 把 DLL 放在 mod 根目录；[UE4SS 官方 C++ 安装文档](https://docs.ue4ss.com/dev/guides/installing-a-c%2B%2B-mod.html) 要求 Mods/ModName/dlls/main.dll（或 dlls/ModName.dll）及 mods.txt 启用项。应以实际固定 UE4SS 版本的加载规范为准。配置文件又依赖 CWD，必须从日志验证实际查找路径，不能只复制到看起来合理的位置。

[UE4SS 构建文档](https://docs.ue4ss.com/dev/guides/creating-a-c%2B%2B-mod.html) 要求 Windows C++ 环境、CMake、Git 及有权访问的 Epic 子模块；其配置名称 Game__Shipping__Win64 与候选 README 的普通 Release 不一致。先固定 ABI/构建版本，不能承诺“UE4SS 2.6+ 都兼容”。

## 文本类型和覆盖边界

- UMG 的 UTextBlock/FText 和经过反射调用的已知文字 setter 是第一阶段合理目标。
- [Epic UTextBlock::SetText](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/UMG/UTextBlock/SetText) 明确说明调用会清除 Text 属性绑定；盲目回写可能破坏动态界面逻辑。
- [Slate STextBlock](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Slate/STextBlock) 是原生 Slate 层，其 TAttribute/FText 通路不等同于反射 UFunction。ProcessEvent 方案无法据此推导全覆盖。
- [UE4SS RegisterHook](https://docs.ue4ss.com/dev/lua-api/global-functions/registerhook.html) 只能注册已经在内存里的 UFunction，并不支持 delegate functions；不存在只写一个 Lua hook 名字即可保证所有界面都被拦截的依据。
- LocRes 是本地化数据文件；导出→翻译→导入→可加载的资源覆盖包是离线汉化路线。需要源资源可合法访问、正确文化路径、namespace/key/hash、装载优先级和打包格式，不是实时 API 插件。
- 字体中没有中文字形、纹理内文字、视频字幕、Canvas 自绘 UI、原生 Slate、自定义 C++ UI、第三方 UI 中间件均可能需要单独方案。
- 有游戏工程源码时可增加引擎插件/本地化数据，但编辑器插件不能直接塞进任意已打包商业游戏并自动生效。

## 推荐的可行原型

1. 独立翻译桥：百度/OpenAI-compatible provider、按供应商条款控制的缓存、术语/占位符保护、超时/限速、原文保底；先通过纯协议测试。百度持久译文缓存和再分发默认禁用，直到当前账号协议得到核实；统计元数据与译文分开。
2. 实验性 HTTP 接入：将固定候选 mod 的 chat-completions 请求发到 loopback；服务端保管用户本地设置的凭据，游戏侧只持有本地随机 token。禁止将真实密钥写进 GitHub。
3. 选择一个无反作弊的离线 Windows x64 UE4.27 或 UE5 游戏，确认使用 UMG。先确认 UE4SS 独立正常，再测试纯缓存中文替换，最后测试远程翻译。
4. 面向生产的运行时适配器应改为明确类/函数白名单；安全弱引用/serial 验证；原文版本检查；主线程回写；重入保护；绑定保留策略；不默认翻译用户输入或聊天；允许游戏专用 profile。
5. 如果该游戏允许加载本地化资源，静态 LocRes 翻译通常更可控，可复用同一 provider/cache；OCR 覆盖层作为无法原位修改时的独立备选。

## 最低测试矩阵（均待真实游戏验证）

| 维度 | 必测 |
| --- | --- |
| 引擎/构建 | UE4.27 Shipping；至少一个明确版本 UE5 Shipping；UE4SS 版本/commit/ABI记录；不跨版本推断 |
| 文本 | 普通 TextBlock；RichText 标签；CommonUI 子类；静态构造默认值；Blueprint SetText；原生 Slate 作为预计缺口 |
| 生命周期 | 快速开关菜单；切场景；销毁 widget 后请求返回；同 widget 文本变化；地址复用；退出时未完成请求 |
| 正确性 | 中文字体；换行/emoji；{0}/{name}/%s；富文本标签；数值更新；文化切换；绑定是否仍工作 |
| 性能/网络 | 冷缓存与暖缓存；断网；401/429/5xx；超时；重复文本合并；大批文本队列上限；帧时变化 |
| 安全/分发 | 不读取或上传密钥；loopback 限定；token 校验；日志脱敏；无第三方游戏资源；许可证/源码与二进制对应 |
| 回滚 | 禁用 mod 后游戏正常；备份不覆盖；原文保底；缓存可独立删除；无存档改动 |

真实游戏验证前必须记录：具体游戏名称/版本、平台及 Windows 架构、UE 版本（如果已知）、是否离线且没有反作弊、希望翻译的原语言。Cursor 账号 API key 可走官方 Agent SDK 路线，但不是通用 OpenAI chat-completions key；应作为独立、严格关闭工具权限的离线适配器评估，参见 [API 调研](api-options.md)。

# 实验性 UE4SS 运行时接入

## 状态

这不是已经通过游戏测试的一键安装包。此目录提供接入说明、无秘密配置模板及 [固定版本源码加固 diff](upstream-hardening/README.md)，不包含或下载 DLL，不安装/注入游戏，不修改任何游戏资源。桥接服务的协议测试不等于 UE4/UE5 游戏兼容性测试。

候选运行时：[UE-RealtimeTranslationMod](https://github.com/shuipingbai6/UE-RealtimeTranslationMod)，固定研究版本 [b4e2e11d](https://github.com/shuipingbai6/UE-RealtimeTranslationMod/commit/b4e2e11db91a37351a99e7c8f46d3862383f9dd5)，GPL-3.0。完整审查见 [runtime-options](../research/runtime-options.md)。此目录的派生 diff 按 GPL-3.0 提供且附许可证；没有分发其二进制。以后发布修改后二进制时必须提供对应完整源码，不能只提供 diff。

## 先解决的阻断项

1. 未选定真实目标游戏，未验证 UE4SS 独立兼容性及对应 C++ ABI。
2. 上游 HTTPS 客户端关闭关键证书检查。真实云端凭据不能交给它；候选配置仅指向 127.0.0.1，填入的必须是本地临时 token。
3. 上游会保存词库和文本日志；auto_save:false 不足以禁止所有落盘。百度存储/再分发条款未确认前，不能把它当作可直接搭配百度发布的方案。
4. 异步 widget 生命周期、陈旧文本覆盖、回写重入、Text 绑定清除尚需修复和验证。

因此，模板用于离线协议联调和将来经过审计的运行时构建。真实游戏接入需先选择适合测试的离线游戏，再完成安全与兼容性检查。不要绕过反作弊或安全限制。

## 协议

桥接服务候选地址：http://127.0.0.1:18765/v1/chat/completions。服务只绑定 loopback。翻译模块位于独立 translation/ 子目录；先进入该目录，再按 [翻译模块 README](../translation/README.md) 启动 python -m utp。启动时创建 runtime/local-token.txt；把其中的临时 token 手动填写到本机配置的 api_key，绝不提交该文件。实际启动命令和 config 路径以上述 README 为准。

上游要求 api_endpoint、api_key、model 均非空。model 使用 bridge；真实供应商和语言由服务端配置决定，客户端不能通过 model 或 prompt 更改远程目标或获取工具权限。

上游请求的 messages 含一条固定翻译 system 文本和一条 user 文本；user 文本的固定说明之后是分隔符 `\n\nText to translate:\n`，随后才是真正原文。服务应严格识别已知封装并只提取一次，保留原文中的后续相同字符串；不得把原文当作对服务的指令。

返回格式为 choices[0].message.content 文本。上游手写 JSON 解码不完整，响应最好使用 UTF-8 实际字符（ensure_ascii=false），并测试引号、反斜杠、换行、emoji；不能因此关闭桥接端严格 JSON 验证。上游会重试，因此服务端的实际收费尝试与预算计数必须独立于客户端重试次数。

## 安装布局与路径注意

只有在 UE4SS 已被证明能安全加载目标游戏之后，才考虑该阶段。

- [UE4SS C++ mod 文档](https://docs.ue4ss.com/dev/guides/installing-a-c%2B%2B-mod.html) 的布局是 Mods/RealtimeTranslationMod/dlls/main.dll，加 mods.txt 的启用项。
- 候选 README 的布局与官方文档不一致；不要照搬成通用安装脚本。
- 上游读取配置的实际位置是进程 current_path()/Mods/RealtimeTranslationMod/translation_config.json，未必是 ue4ss/Mods。需要检查固定版本日志/源代码，不能仅凭 DLL 位置猜测。
- UE4SS 本体通常位于真实游戏可执行文件旁的 Binaries/Win64；根目录的启动器未必是真正 EXE。尊重已有 mod loader，备份且不要覆盖其他 DLL。
- 构建运行时必须匹配 UE4SS 的准确版本和 ABI；“2.6+”不是兼容性保证。不要自动执行候选一键安装 EXE。

## 最小验证顺序

1. mock 翻译服务：固定 Hello → 你好；确认 HTTP/token/JSON 协议。
2. 不开网络：指定测试 UI 的缓存替换；记录游戏、版本、UE/UE4SS 构建、捕获/回写数量和截图。
3. UI 生命周期、动态文本、绑定、字体、富文本、断网和回滚测试。
4. 经授权的少量真实 API 测试；验证计费限制、脱敏和供应商存储策略。

只有完成这些步骤，才能给具体游戏打“已验证”标记。UMG 测试通过也不能扩展成 Slate、自绘 UI、纹理文字和所有 UE 版本都支持。

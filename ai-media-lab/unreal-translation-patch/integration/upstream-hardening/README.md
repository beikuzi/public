# UE-RealtimeTranslationMod：固定版本的窄范围加固补丁

适用仓库：https://github.com/shuipingbai6/UE-RealtimeTranslationMod

唯一核查基线：b4e2e11db91a37351a99e7c8f46d3862383f9dd5（2026-03-29）。这是源码 diff，不是可直接安装的 DLL。改动日期：2026-10-05。

## 做了什么

- 删除 WinHTTP 忽略 CA/有效期/域名证书错误的选项，恢复默认验证。
- 将 VocabularyCache::Save 的完整实现替换为返回 false。普通 Store、批量保存、手动按钮、后台调用、退出和析构等路径即使调用 Save，也不会写词库/模板文件。TemplateCache::Save 本来不单独写文件。
- 禁止启动后台保存线程；SetAutoSave 不再能重新开启保存。这是固定的仅内存缓存构建，而不是运行时可切换选项。
- 关闭 DebugLogger 的文件和 OutputDebugString 输出；将七处包含原文、译文、响应、地址或详细错误的 UE4SS Output 日志改成固定诊断文本。

## 如何应用

仅在独立的、准确基线版本源码副本中操作。先核对 commit；保留本地修改，不要在未知工作区强制覆盖。

```sh
git rev-parse HEAD
git apply --check /path/to/privacy-tls.patch
git apply /path/to/privacy-tls.patch
python /path/to/verify_source.py /path/to/UE-RealtimeTranslationMod
```

这些操作只处理源码。构建/运行仍需匹配 Windows C++ 工具链、UE4SS ABI 和游戏；不要将修改直接视作经过验证的运行时安全方案。

## 验证证据和边界

- 已对本次读取的固定版本源码进行 git apply --check。
- 已将补丁应用到另一个临时源码副本，检查七个修改文件的 SHA-256 与预期一致。
- 静态确认 NetworkClient 不再含 SECURITY_FLAG_IGNORE_*；VocabularyCache 不再有输出文件流；DebugLogger 不再有输出文件流/OutputDebugString。
- 未编译，未加载 UE4SS，未运行游戏，未调用任何云端翻译 API。未执行上游代码。

static-checks.json中的散列针对 UTF-8/LF 源码文本，不是上游 DLL。CRLF 工作区应先按正常 Git 文本换行配置处理；不能用散列结果替代运行时测试。

此补丁不修复原始 widget 指针生命周期、地址复用、陈旧结果覆盖、绑定丢失、JSON 解析、重入、配置 CWD、ABI 或覆盖率问题。配置仍可能保存本地 token，日志仍可保存非文本诊断；游戏本身、操作系统分页/崩溃转储和其他 mod 不在本补丁控制范围内。旧词库文件不会被删除。UI 某些保存按钮仍可能显示旧版文案，不能相信其“已保存”提示。

关闭译文文件保存不等于取得供应商使用许可。百度实际账号协议、内存缓存和游戏文本再分发权限仍需确认。真实 provider 密钥仍只放在桥接进程，不放进 mod；运行时配置只指向 loopback。

## 许可证与署名

本 diff 派生自上述 GPL-3.0 项目；diff 及其涉及的上游源码遵循 GPL-3.0，完整许可证见 COPYING.GPL-3.0。保留上游作者署名（README 作者账号 shuipingbai6，源码 ModAuthors 为 jx666）。补丁变更为 2026-10-05 的隐私/TLS 加固。

这里只分发可审查补丁和验证脚本，没有分发上游 DLL。将来若分发修改后二进制，必须同时按许可证提供对应完整源码、构建信息和许可证/变更通知，不能只提供该 diff 当作完整对应源码。

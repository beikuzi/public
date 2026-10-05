# Unreal Translation Patch · 实验原型

目标：把 Unreal 游戏文本交给自己的翻译服务，再交回游戏。当前交付是**可运行的本地翻译桥 + 实验接入说明**，不是已经验证的通用游戏补丁。没有目标游戏、没有执行 DLL 注入，也没有游戏内测试。

## 已实现

- Python 3.10+ 标准库桥接，无 Python 第三方依赖；Windows PowerShell 示例
- 百度官方通用翻译 API：APP ID + 密钥仅从环境变量读取；不接触网页 cookies
- 可选自有 OpenAI-compatible 模型服务；这不等于 Cursor 账号 key
- Cursor 账号 key 的独立文本批处理实验模块见 `cursor-batch/`（如该阶段已加入）；不承诺实时响应
- 内存去重/缓存，保留 UE `{字段}`、printf、富文本标签和换行；验证失败保留原文
- 每日请求/字符上限、串行限速、15 秒网络超时、单次失败不自动重试
- 默认 mock 离线模式；必须显式 `--allow-remote` 才会向服务发送文本并产生用量
- 文件队列，以及需要手动开启的 127.0.0.1 鉴权兼容接口

## 1. 离线体验（无密钥、无费用）

进入本目录，在 PowerShell 执行：

```powershell
python --version
Copy-Item config.example.json config.json
New-Item -ItemType Directory -Force runtime/inbox | Out-Null
Copy-Item examples/demo.json runtime/inbox/demo.json
python -m utp --config config.json --once
Get-Content -Encoding UTF8 runtime/outbox/demo.json
python -m unittest discover -s tests -v
```

mock 只翻译示例词语，不是真实翻译模型。第一次命中返回 translated，同进程重复请求返回 cache。程序重启清空内存缓存。

## 2. 使用百度

先确认你的百度账号已开通通用翻译 API、当前额度/价格及服务协议允许所需用途。`config.json` 中将 provider 改为 baidu。默认目标 `zh`；百度使用 `jp`/`kor`/`fra`/`spa` 等语言代码，不要直接套用所有 ISO 代码。目标不能是 auto。

不要把真实密钥写进命令历史、脚本、配置、GitHub 或聊天。以下输入在当前 PowerShell 会话内设环境变量：

```powershell
$env:BAIDU_APP_ID = Read-Host '百度 APP ID'
$secret = Read-Host '百度密钥' -AsSecureString
$env:BAIDU_SECRET_KEY = [System.Net.NetworkCredential]::new('', $secret).Password
# 百度文件队列输出当前禁用，避免默认把译文持久写入磁盘。
# 只有在确认服务条款且接收端不会保存译文后，才启动内存 HTTP 接口：
python -m utp --config config.json --serve --allow-remote
# 未修复的第三方模组不能作为上述接收端。
# 结束后清除本会话变量
Remove-Item Env:BAIDU_APP_ID, Env:BAIDU_SECRET_KEY
```

输入游戏文本会发送给百度。默认最多 100 次请求 / 10000 个计费近似字符每天（UTC）；字符按保护标记替换后的请求计数，不能当作账单金额保证。标准版默认每条原文不超过 1000 字符，掩码后还限制 5500 UTF-8 字节。失败请求也扣本地预算，避免重试扩大支出；服务端计费以你的套餐为准。多行作为一个带保护标记的请求发送。预算记录存在 runtime/usage.sqlite3，仅包含日期和计数，无翻译文本。不要删预算文件来绕过自己的限制。

桥本身不持久缓存译文；百度 provider 当前拒绝文件队列模式。其他 provider 的文件队列输入/输出仍含明文，消费方应及时删除，避免写入云同步目录。百度当前账号服务条款需自行确认；不提供/分发真实游戏翻译库。上游游戏模组自己的缓存和日志不受桥控制，必须另行检查。

## 3. 实验性游戏接入

先阅读 `../research/runtime-options.md` 与 `../integration/` 中的说明。上游源码审查发现证书校验绕过及退出时无条件落盘缓存：未应用并重新编译验证修复前，仅允许本地 mock 接入，不要把百度真实翻译接到该模组。把 auto_save 设为 false 本身不足以阻止退出保存。当前候选是第三方 UE-RealtimeTranslationMod，不包含其 DLL 或源码副本。本项目没有安装或运行它，也不保证它适配你的游戏/UE4SS 版本。

```powershell
python -m utp --config config.json --serve
# 真正的远程翻译需要额外添加 --allow-remote
```

仅监听 `http://127.0.0.1:18765/v1/chat/completions`。每次启动生成临时会话 token，放在 `runtime/local-token.txt`；不要上传。手动填入模组配置的 api_key，endpoint 指向上述地址，model 填 local-bridge。关闭程序 token 失效，正常退出删除 token 文件。此 token 只控制本地临时服务，绝不是百度/Cursor 密钥；真实服务密钥只留在桥进程环境里。接口串行处理，游戏侧必须异步调用，不能从游戏主线程阻塞请求。

桥会拒绝浏览器 Origin 请求、跳转、环境 HTTP 代理，并且不修改防火墙或系统网络配置。不要将监听地址改为 0.0.0.0，不要经公网转发。本机不可信进程仍是风险；Windows 请限制 runtime 目录 ACL 为自己的账号，Python 3.12+ 可额外识别 junction，3.10/3.11 用户不要使用 junction/reparse runtime 路径。POSIX 目录/文件使用 700/600；它们不是 Windows ACL 的替代。

没有指定游戏时，无法判断其引擎版本、文本系统、字体覆盖、反作弊或模组许可。只在允许本地模组的离线游戏测试，不在联网/竞技/反作弊进程中试用。字体、Slate/自定义渲染、图片内文本、嵌套 ICU/plural、对象生命周期和动态文本更新仍需逐游戏处理。

## 4. 自有模型服务（可选）

仅在你拥有官方支持的服务 key/base URL/model 时，把 provider 设为 openai-compatible，增加 base_url（例如该服务官方文档给出的 HTTPS API 根路径）和 model。将密钥放入 TRANSLATION_API_KEY 环境变量。地址会附加 `/chat/completions`。不同厂商参数/语言名/限流可能不同，未做线上兼容性承诺。不要填 Cursor 账号 key，更不要使用非官方 Cursor 代理。

## 备份、回退和卸载

- 接入前备份游戏相关配置和原有模组目录；不覆盖原版 EXE/DLL，不改存档
- 关闭桥按 Ctrl+C；如使用游戏模组，关游戏后先恢复你备份的配置/移除本次模组项，具体目录见 integration 文档
- 删除本项目文件夹即可移除桥；清除当前会话的 API 环境变量
- 崩溃遗留 worker.lock 时，确认没有桥进程运行后才手动删除该空目录。token 退出即无效，但遗留文件也应删除
- 删除 runtime 会删除队列明文和预算记录；不代表服务商已删除它收到的数据

## 协议与测试边界

参阅 `docs/protocol.md`。已做离线合成测试；未执行真实百度调用、Cursor 付费用量、第三方 DLL、UE4SS 或任何游戏内验证。不要将通过单元测试理解为游戏适配已完成。

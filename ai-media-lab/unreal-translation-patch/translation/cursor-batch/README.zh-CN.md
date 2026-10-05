# Cursor 账户 API Key：文本批量翻译适配器

这是构建阶段的批处理示例：读取文本 JSON，调用官方 Cursor SDK，再由本程序校验并写出 JSON。不是游戏内实时翻译插件，也没有验证具体游戏。所谓“离线批处理”仅指离开游戏运行；推理需要联网，文本会发送给 Cursor，并可能产生费用。未做真实账户、付费请求或 SDK 安装验证；当前测试全部使用模拟 SDK。

## 使用前

- Node.js ≥22.13。仅使用官方 npm 包 `@cursor/sdk`。请先核对当前官方版本，将审核过的精确版本安装并保存锁文件；本示例没有捏造一个已经验证的版本号。
- 使用 Cursor 官方提供的 User API Key 或 Service Account API Key。Team Admin Key 不适用。没有把账户 Key 当成 OpenAI Chat Completions Key。
- Key 只能由本机环境变量 `CURSOR_API_KEY` 提供，不放在 JSON、源码、命令行参数或提交记录中。不使用 Cookie、代理服务、自动登录或创建 Key。
- 自行确认待翻译内容可发送给 Cursor。不要输入聊天记录、密码、真实玩家信息或未获授权的游戏资源。
- 在 Cursor 账户后台设合适的使用上限。本程序的请求数/字符数只是输入限制，不是金额上限；单次 agent run 的内部推理量不能由这些限制准确预测。

## 本地测试（不联网、不需要 Key）

```sh
cd cursor-batch
node --test *.test.mjs
```

## 输入和运行

输入文件：

```json
{"version":1,"texts":[{"id":"welcome","text":"Hello {PlayerName}!\n<Emphasis>Welcome</>"}]}
```

在本机安全地设置环境变量并安装已审核的官方 SDK 后，只有明确同意远程传输与计费时才使用 `--allow-paid-remote`：

```sh
node cli.mjs --input ../my-texts.json --output ../my-translations.json --model YOUR_ACCOUNT_MODEL_ID --target zh-CN --max-calls 10 --max-characters 10000 --timeout-ms 120000 --allow-paid-remote
```

必须指定账户可用的固定模型 ID；不使用未经校验参数的 Router。输入按最多 300001 字节有界读取，超过 300000 字节即拒绝。输出文件必须不存在，以免覆盖原有译文；任何 SDK 调用前先独占创建并打开输出文件，预检路径与写入权限。后续磁盘耗尽或硬件故障仍可能导致写入失败，无法由预检保证。输出含 `version`、`results`；每项含 `id`、`text`、`status`、`original_sha256`，失败项另含不带原文的错误码。失败保留原文，部分成功可以保留。任何写回游戏文本的程序都应再次核对 SHA-256（原始 UTF-8 文本，无归一化）及格式，并先人工抽检；不要直接写入游戏资源文件。

每次最多 64 条，每条最多 1000 个 Unicode 字符；默认最多 10 次 run、总计 10000 个原文字符。预算不足会在调用前拒绝整个批次。每条有效文本独立一个新 agent；没有自动重试。网络、运行状态或工具异常会停止剩余请求；纯输出校验错误只影响当前条。

## 防护边界

空的临时工作目录、禁用环境设置层、`tools: []`、禁用 MCP 和 subagent、禁用 SDK 自动重试。模型只返回字符串，文件写入由本程序完成。格式占位符、标签和换行先掩码，收到响应后核对顺序和原文哈希。嵌套 ICU 等不支持结构跳过。JSON 不是可信命令，源文本中的指令也不应执行。

SDK 的临时会话存储在临时目录，正常结束后清理。崩溃、强制结束或系统故障可能留下含原文的临时目录；不要同步或上传 `utp-cursor-*` 目录。Cursor 服务器端数据遵循其账户设置和条款，清理本地文件不等于删除服务端数据。应用日志只输出计数和错误码，不输出 Key、提示词或译文；SDK 自身日志行为尚未实测。

超时或 Ctrl+C 会尝试取消并释放 agent；网络中断时不能保证远端立刻停止或完全不计费，不应自动重跑。存在无法中断的 SDK 初始化/发送时，适配器会观察迟到的句柄并取消。操作系统强制结束仍需要自行检查 Cursor 用量。

官方契约依据：[Cursor TypeScript SDK](https://cursor.com/docs/sdk/typescript)。需要真实验证的事项：当前包版本、账户权限、模型可用性、取消行为、译文质量、耗时与实际费用。

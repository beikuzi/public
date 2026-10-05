# Unreal 文本提取与独立翻译实验

当前优先目标是正确提取 Unreal 游戏文本；翻译模块独立放在 `translation/`。目前不能把它称为经过游戏验证的通用补丁。

- `extraction/`：提取工作及真实样本验证（正在推进，以该目录的证据和报告为准）
- `translation/`：可运行的离线 mock、百度官方 API 桥、文件队列和实验兼容接口。使用方法与测试命令见该目录 README
- `translation/cursor-batch/`：Cursor 官方 SDK 文本批处理实验（以该模块实际交付和测试报告为准）
- `research/`、`integration/`：候选方案与源码风险审查，非已验证游戏适配保证

不会将未知 DLL 注入游戏，不修改反作弊，不把真实 API 密钥写进项目。所有真实联网翻译默认关闭；提取文件可能包含受版权保护或敏感文本，请保留在本地，不要直接上传 GitHub。

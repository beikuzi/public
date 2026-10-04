# 原始资料 → 视频理解 → 评论观点

## 必需输入
- video_manifest.json：来源 URL/BV、标题、时长、抓取 UTC、许可/访问条件、处理命令。
- transcript.json：每段 start/end/text、来源（人工字幕/平台自动字幕/ASR/OCR）、模型与版本。各来源分开保存，不能把平台 AI 字幕当人工真值。
- frames/：时间戳、采样方法、图像文件。字幕转录不能代替画面观察。
- comments.raw.jsonl 或导入文件：id、parent_id、text、发布时间、抓取时间、likes、sampling_group、抓取页码/游标。只保存完成任务需要的字段，不需要用户名、头像、主页或粉丝资料。

## 分析步骤（可交给任何能看图片的模型，或人工审核）
1. 先读 manifest、转录和真实抽帧，不只读标题。输出视频主张及其时间戳，分别标出「说话者说的」「画面直接呈现的」「分析者推断的」。看不到的细节不要补写。
2. 先浏览样本再决定 3–5 种主流观点。每条有效评论只标注一个 primary_stance；确实模糊的标为 ambiguous。广告、纯表情、重复内容、与主题无关可排除但记录原因。引用他人的话不等于作者赞同。
3. 保存 comments.annotated.json：id、原文（本地保存）、primary_stance、reason、evidence_excerpt、confidence、sampling_group、likes。出现多种立场时解释主立场判断，或标 ambiguous。
4. 用 aggregate_stances.py 统计，不让语言模型凭感觉填百分比。报告分母、排除数量、去重方式。按 hot/latest 分开报告，再说明是否及如何合并。
5. 每种主流观点写：核心论点；支持它的样本条数与占比；最多一两条短例证及原评论引用 ID；支持证据；反例/局限；分析者评价。评价论证是否充分，不评价评论者人格。
6. 对视频事实主张的核查需要另找可验证来源，评论数量和点赞数不是事实证据。无法核查写「未核实」。不从账号或评论推断敏感身份、政治倾向等个人特征。
7. 结论注明：这是采到的评论声音分布，不是全体观众观点比例。热评放大高互动内容，最新评论有时段偏差，回复有群聚效应。点赞加权结果单列为「样本点赞分布」，不能解释成赞同人数。

## 运行
python analysis/aggregate_stances.py comments.annotated.json stance_summary.json

## 公开发布边界
公开仓库默认只包含代码、合成测试、聚合结果、证据链接和必要短引文；原视频、完整字幕和评论语料不自动公开。Cookie、访问令牌、签名媒体链接、作者标识不提交。访问受阻则记录 failed/not_run，不能使用合成数据伪装真实结果。

默认至少20条可解释评论才展示样本内百分比（可用--min-sample调整）；这是防止极小样本误导的展示阈值，不代表20条就具有统计代表性。低于阈值仍保存条数与排除原因。

## 点赞缺失与覆盖率（汇总 schema2.0）
- 缺少 likes、null 或空白字符串，均是「未知」，不能填成0。明确观测到0次点赞才是0。
- 接受非负整数与仅含ASCII数字的整数字符串（可有首尾空白）。布尔值、负数、小数/浮点数、科学计数法、带逗号字符串及其他类型标为 invalid；不截断、不猜测、不静默归零。导入后用 likes_status 保留 observed/unknown/invalid。
- likes_coverage 的分母是去重后、实际纳入观点统计的评论；被排除评论不影响该分母。保留第一条重复记录，不利用后续重复快照补点赞。
- likes_received 只有该观点的点赞覆盖完整才有值；否则null。observed_likes_received 是已观测评论的部分合计，没有任何观测时也是null。两者不可混用。
- 只要纳入评论有任何未知或无效点赞，所有 share_of_sample_likes_pct 均为null，like_share_status 标明 suppressed_incomplete_likes_coverage。评论条数占比仍可按原来的样本门槛单独显示。
- 即使点赞覆盖完整，合计0次也没有可定义的点赞份额，保持null；样本量不足同样抑制显示。点赞份额仍不代表赞同人数。
- 导入器保留 exclusion_reason；原始导出不改写，规范化记录和 provenance.json 保存校验状态与输入哈希。

完整本地链路：
python bilibili/import_comments.py user-export.json --out comments.normalized.json
python analysis/aggregate_stances.py comments.normalized.json stance-summary.json

回归测试（仅合成数据，无网络）：
python -m unittest discover -s analysis -p 'test*.py' -v
python -m unittest discover -s bilibili -p 'test*.py' -v

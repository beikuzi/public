# 图片识别与溯源：仓库、接口与实现建议

核查日期：2026-10-05。以下为公开官方文档和仓库的桌面研究，不代表所有在线服务已完成实图测试。网页缓存可能滞后；未验证的信息明确保留为未知。这里没有用户图片、搜索结果、凭据或个人资料。

## 结论

建议采用“小而可替换的多源适配器”，不要把任何单个识图结果包装成可靠的原作者证明。

- 动画截图：trace.moe 找作品、集数和时间点；角色名称需要独立证据。
- 同人插画：SauceNAO → ascii2d → IQDB 找相同图及来源候选；AnimeTrace 仅辅助角色和作品判断。
- 转发图、壁纸、裁切图：OCR 提取署名/水印，使用多源反搜，逐级跟随来源链接，核对作者原帖。
- 通用图片：Google Lens / Bing 网页作为人工补查入口；不建设已退役的 Bing Visual Search API。
- 第一阶段采用直接 HTTP 官方接口 + 手动补查入口；PicImageSearch 是扩充非官方网页适配器时的优选候选。

以上路由是工程建议，不是服务商对准确率的保证。图像相似度不是作者身份概率；多个索引若都转引同一转载站，不构成多个独立证据。

## GitHub 候选对比

| 仓库 | 角色、许可 | 维护证据与取舍 |
|---|---|---|
| [kitUIN/PicImageSearch](https://github.com/kitUIN/PicImageSearch) | Python 多源聚合，MIT；Python 3.10+，异步接口 | 首选可选聚合层。[提交页](https://github.com/kitUIN/PicImageSearch/commits/main/)可见 2026-07-05 依赖更新、6月服务适配修复。包装网页的模块仍有失效风险；不能把库名中的 API 当官方授权 API。 |
| [soruly/trace.moe](https://github.com/soruly/trace.moe) | 官方系统索引/自托管入口 | 说明包含视频索引流程；自托管仍需自己的视频及索引资源。第一版不自建全量动漫数据库。 |
| [soruly/trace.moe-api](https://github.com/soruly/trace.moe-api) | 官方 API 服务端，[MIT](https://raw.githubusercontent.com/soruly/trace.moe-api/master/LICENSE) | 优先采用其公开 HTTP API；文档现包含向量搜索和双路裁边。仅据最新文档，不宣称已核实最后提交日期。 |
| [soruly/trace.moe-mcp](https://github.com/soruly/trace.moe-mcp) | 官方 MCP 客户端，MIT；Node.js 24+ | 较小的新项目，页面显示6次提交；支持本地算 hash 后仅发向量。适合未来集成，先审查并固定版本，不直接执行浮动 npx。 |
| [soruly/trace.moe-id](https://github.com/soruly/trace.moe-id) | 官方图像描述符提取库 | 官方 API 文档推荐的 MPEG-7 ColorLayout 向量实现。适合降低原图上传；本轮未逐一验证其许可/发布时间，采用前再核对。 |
| [danbooru/iqdb](https://github.com/danbooru/iqdb) | 自托管相似图引擎，GPL（README） | 有 HTTP JSON、SQLite 索引；它不会自带全网数据。只在用户积累自己的图库后值得加入。最后提交日期未核实。 |
| [soruly/iqdb](https://github.com/soruly/iqdb) | 原始 IQDB 镜像，GPL | 旧接口与编译方式，适合算法参考，不优于上述 fork 作新服务基础。 |
| [l2studio/iqdb-api](https://github.com/l2studio/iqdb-api) | TypeScript iqdb.org 客户端，Apache-2.0 | 仅一个来源；与 Python 主程序不合算。仍依赖网站行为；维护时间未核实。 |
| [nomnoms12/saucenao_api](https://github.com/nomnoms12/saucenao_api) | SauceNAO JSON 包装，GPL-3.0 | 提供作者、标题、URL 和配额容器；适合研究响应结构。新项目优先直接 HTTP 或 MIT 聚合层；勿把示例配额当现行承诺。 |
| [DaRealFreak/saucenao](https://github.com/DaRealFreak/saucenao) | SauceNAO Python 包装/批处理，MIT | 单源、偏目录批处理；不是多源证据融合器。最后提交日期未核实。 |
| [Nachtalb/reverse_image_search_bot](https://github.com/Nachtalb/reverse_image_search_bot) | 多源 Telegram 成品，GPL-3.0 | **2026-09-06 已归档**；维护转入闭源版本。可参考交互，但不选作持续维护主干。还需要 Telegram 和上传基础设施。 |
| [dessant/search-by-image](https://github.com/dessant/search-by-image) | 浏览器多引擎入口，GPL-3.0 | 支持30多个引擎、选择/裁切/粘贴模式；适合人工补查。它不是统一结果解析 API，安装浏览器扩展需用户明确授权。 |
| [JohannesBuchner/imagehash](https://github.com/JohannesBuchner/imagehash) | 本地感知哈希，[BSD-2-Clause](https://raw.githubusercontent.com/JohannesBuchner/imagehash/master/LICENSE) | 适合本地去重、缓存与已下载候选比对；不能发现未索引的互联网来源。 |
| [tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract) | 本地 OCR，Apache-2.0（仓库） | 轻量工具链备选，适合明显署名/水印。最后提交日期未核实。 |
| [PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | 多语 OCR，Apache-2.0 | 官方 README 有2026年发布记录，维护明确；环境和模型较重，作为后续可选项，不拖慢首版。 |

许可针对各仓库软件，不授权抓取其服务、不授予所搜图片版权。GPL 项目若复制/分发代码，应单独评估对应义务。

## 服务与接口状态

### trace.moe：动画截图首选

官方：[接口](https://raw.githubusercontent.com/soruly/trace.moe-api/master/docs/docs.md)、[额度](https://raw.githubusercontent.com/soruly/trace.moe-api/master/docs/limits.md)。

- 免费无账户、无 API key：每 IP 滚动24小时100次搜索、并发1；另有HTTP每分钟100次限制。赞助档提高额度，最低列为每月1美元/每日1000次。部署时再读 `/me`，以实际账户为准。
- `POST https://api.trace.moe/search`，multipart字段 `image` 或原始图片bytes；最大25MB。URL输入须是可公开取到的图片。
- 返回 `result[]`，包含 `anilist`、`episode`、`from/to/at`、`similarity`、预览。`anilistInfo` 可扩充标题，额外依赖 AniList。
- 官方提醒低于90%的相似度通常不正确。预览URL五分钟到期，报告不能把临时预览当永久来源。
- 402区分配额/并发问题，429为HTTP限流；队列繁忙应有限退避。`cutBorders=2`可能消耗2次额度。
- 支持本地提取向量；向量也是对外发送的数据，不应描述为完全离线。

### AnimeTrace：角色/作品候选，不是画师溯源

官方：[开发文档](https://www.animetrace.com/api-docs/)、[隐私及版权声明](https://www.animetrace.com/copyright/)。

- 文档最后更新2026-07-03，示例未使用登录或API key；未见正式价目或固定免费额度，不能承诺永久免费/不限量。
- `POST https://api.animetrace.com/v1/search`，`file/url/base64` 三选一，`is_multi=1`可保留多个候选。
- `GET /v1/model/list`动态获取模型，仅选 `enabled=true`，优先 `default=true`；官方明确不要硬编码模型名。
- `data[].character[]`有`work/character`；`box`定位，`not_confident`低置信提示。不凭其AI检测布尔值断言图片一定是AI生成。
- 基础识别政策称上传仅用于当次识别、未经主动反馈/授权不参与训练；可选Agent对话另有保留/训练条款，不能混同。
- 允许个人/商业API调用，但未经书面许可禁止系统性、规模化自动抓取。适用用户主动即时查询。
- 未找到可核实的官方公开识别模型源码仓库；PicImageSearch是第三方客户端。模型列表本轮读取工具失败，不代表服务下线。

### SauceNAO：插画图源主候选

官方：[主页及索引](https://saucenao.com/)、[条款](https://saucenao.com/legal.html)、[API设置](https://saucenao.com/user.php?page=search-api)。

- 网页可直接显示上传表单；API设置页本轮403，账户价格、现行匿名/免费额度未官方核实。
- [PicImageSearch客户端源码](https://raw.githubusercontent.com/kitUIN/PicImageSearch/main/PicImageSearch/engines/saucenao.py)使用 `POST /search.php`、`output_type=2`、multipart `file`，可选 `api_key`。这是第三方实现证据，不是服务商保证。
- 配额在不同包装库注释中有100/150每日等矛盾，故不硬编码。读取返回的短期/长期剩余额度；遇限流停下，不换IP/账户绕过。
- 保存原始候选URL与索引类型；Pixiv/作者原帖与booru转载应区分。返回author字段仍需要源页证实。

### ascii2d 与 IQDB：备用网页渠道

- [ascii2d官网](https://ascii2d.net/)目前公开URL/文件表单，无需登录即可看到。未核实公开官方稳定JSON API、价目、固定额度或SLA。
- [PicImageSearch ascii2d实现](https://raw.githubusercontent.com/kitUIN/PicImageSearch/main/PicImageSearch/engines/ascii2d.py)提交 `/search/file` 或 `/search/uri`，再解析HTML，可切color/bovw。作为可选脆弱适配器，默认保留人工入口。
- [PicImageSearch IQDB实现](https://raw.githubusercontent.com/kitUIN/PicImageSearch/main/PicImageSearch/engines/iqdb.py)向 `https://iqdb.org` POST `file`/`url`并解析HTML。本轮官网无法读取，在线额度及可用性待实测。
- 自托管 `danbooru/iqdb` 的JSON接口与 `iqdb.org` 网站不是同一个API；不可混为一谈。

### 通用网页搜图及付费备选

- Lens：本轮未核实官方通用Lens逆向搜图API。保留 [Lens网页](https://lens.google.com/)人工入口，第三方包装不等于Google官方支持。
- Bing：[微软官方](https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement)说明Bing Search APIs已于2025-08-11退役。Bing网页可作人工渠道；Grounding不是等价的图片反搜替代品。
- Google Cloud Vision：[Web Detection文档](https://docs.cloud.google.com/vision/docs/detecting-web)可返回网页、匹配图及实体线索；需要Cloud项目、认证和相应计费配置。[官方价格](https://cloud.google.com/vision/pricing)列每月首1000单位免费，随后至500万单位为每1000单位3.50美元，其他Cloud资源可能另收费。仅作为用户明确开启后的付费选项。

## 建议的数据结构与证据规则

每个候选分别记录 `provider`、`kind`（scene/character/exact-image/repost）、`source_url`、`creator_candidate`、`work_candidate`、`character_candidate`、`provider_score`、`retrieved_at`、`evidence`、`verification_status`。分数保留原始量纲，不将多个来源分数直接平均。

作者确认至少需要原帖/作品页与相同画面可核对，并记录页面作者。最早可见发布日期、高分和高分辨率只能作线索，不能单独证明创作权。若只有转载站则输出“找到转载/索引，原作者未确认”。角色不确定时保留多个候选；不做真人身份识别。

隐私默认：本地先做尺寸/格式/元数据处理、SHA-256缓存键，保留原文件不修改；外部请求按服务逐个启用，展示实际发送目标。禁止自动把私有图片托管为公开URL。移除EXIF不等于图片内容不敏感。日志不保存API key、原图base64或带秘密参数的URL。

## 实现验收清单

1. 零配置本地检查、帮助、报告生成都能离线运行。
2. 每个在线provider单独开关，网络失败/配额耗尽/HTML异常有清晰状态，不掩盖为“未搜到”。
3. 用自有或获授权测试素材分别测试动漫截图、同人插画、裁剪图、水印图、无匹配图。
4. 单元测试模拟响应，不在默认测试中上传图片或扣额度。
5. 没有原帖证据时永不输出“已确认原作者”。
6. 每个适配器固定依赖版本；网页解析器失败后保留人工入口，不绕过安全或访问限制。

## 补充：SauceNAO 参数传输方式

同日核对的第16个仓库是 [ClarityCafe/Sagiri](https://github.com/ClarityCafe/Sagiri)，MIT许可的Node.js SauceNAO包装库。其发布者的 [v4.3.0分发源码](https://app.unpkg.com/sagiri%404.3.0/files/dist/sagiri.cjs)把 `api_key`、`output_type`、`numres` 等参数放入 `FormData`，连同文件作为multipart请求体POST至 `/search.php`；因此“凭据放请求体而不是URL”有现有客户端实现证据。

这不是官方服务端契约或本轮在线测试。受保护的官方API页仍未读取成功。建议保留请求体传参，同时明确标记在线适配器待真实授权调用验证；不要仅因为另一个客户端使用query参数就把秘密迁入URL。任何日志、异常和调试输出都应屏蔽凭据，请求体同样不能原样记入日志。

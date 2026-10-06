# 實驗工具與工作流

所有已提交的工作現已集中在 `main`，保留各階段提交歷史。後續工作也直接在 `main` 分次提交。

[技術交付收尾狀態（2026-10-06）](CLOSEOUT.md)：已完成內容與未完成邊界。

## 專案入口

- [Unreal 文本提取與獨立翻譯](ai-media-lab/unreal-translation-patch/)：先做 LocRes 提取驗證；翻譯另放子資料夾。不是已完成遊戲內驗證的通用補丁。
- [圖片識別與來源調查](ai-media-lab/image-source-tool/)：本地檢查、多平台候選與手動搜尋紀錄；候選不等於確認原作者。
- [角色音訊準備與分離](ai-media-lab/character-audio-lab/)：音訊流程、測試及公開數值證據；不代表訓練就緒資料。
- [影片分析流程](ai-media-lab/video-workflow/)與[證據視覺化](ai-media-lab/video-visuals/)。
- [HTML 影片流程](ai-media-lab/html-video-workflow/)：受限分鏡、旁白、字幕與媒體驗證。
- [趨勢研究](ai-media-lab/trend-research/)與[歷史快照看板](ai-media-lab/trend-visuals/)：有日期的觀察資料，不是即時榜單。
- [Galgame 重構工具](ai-media-lab/galgame-workflow/)：受限解析與重構，不包含遊戲本體或完整劇本。

詳見 [工作區總覽](ai-media-lab/README.md)及各專案 README 的範圍、測試和限制。本頁只列目前倉庫中已存在的專案，不表示其他歷史任務已上傳或完成。

## 分發邊界

主要提供原始碼、測試、文件與經審查的公開證據。私人圖片、憑據、模型權重、完整遊戲資產及私人調查結果不在這些提交中。各元件授權分別適用；第三方服務、真實遊戲相容性及人工品質驗收請以各專案說明為準。


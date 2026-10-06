# 技術交付收尾狀態

日期：2026-10-06 UTC。本頁記錄目前main中的原始碼與驗證邊界，不是原始目標全部完成的聲明。本次收尾僅歸檔已完成的工作，沒有新增研究、功能或重新執行遊戲／媒體流程。

## 已公開與尚未成立的部分

- [影片分析](ai-media-lab/video-workflow/)：已有匯入、ASR/OCR、品質關卡與有限公開樣本。指定B站影片到完整評論分析的端到端鏈路尚未完成，不能從少量可见记录推算整體觀點比例。
- [趨勢研究](ai-media-lab/trend-research/)與[看板](ai-media-lab/trend-visuals/)：保存有時間標記的歷史觀察，並非即時完整覆蓋；抽樣、缺失來源和跨平台指標不可比較的限制保留。
- [Galgame語料流程](ai-media-lab/galgame-text-pipeline/)與[原素材重構](ai-media-lab/galgame-original-visuals/)：只對固定Demo及[The Question短篇基線](ai-media-lab/galgame-route-a-the-question/)提供來源範圍和重構結果，沒有通用遊戲成功率。重組畫面不等於原引擎錄屏；[歷史錄音結果](ai-media-lab/galgame-audio-recovery/)另列其限制。
- [Unreal工具](ai-media-lab/unreal-translation-patch/)：鬆散LocRes的17條記錄逐條比對已成立；真實PAK工作僅索引探測，沒有解碼遊戲payload或完成封裝遊戲文本提取。翻譯子模組是獨立實驗，不是已驗證的通用遊戲內补丁。
- [圖片溯源](ai-media-lab/image-source-tool/)：具備本地處理、明確授權的適配器與手動紀錄；實際來源／角色／原作者尚未確認。模擬測試和匯入紀錄不等於完成線上搜尋。
- [角色音訊](ai-media-lab/character-audio-lab/)：已完成來源研究、機器對齊／篩選、分離與組裝流程。輸出仍是待人工審查的候選；沒有確認乾淨、無重疊、角色唯一性或訓練就緒。
- [瀏覽器影音診斷](ai-media-lab/browser-compatibility/)：僅公開已完成的通用診斷片段；不宣稱裝置相容性問題已修復。

## 本次收尾歸檔

補入三份既有Galgame原始碼快照中的程式、授權與有限覆蓋／QA記錄，以及經刪除環境資訊的錄音技術說明和通用瀏覽器診斷片段。歷史測試記錄保持原範圍；收尾只做語法、JSON、公開範圍及遠端檔案雜湊核對。

原始媒體、遊戲資產、完整劇本／聲音逐字稿、私人圖片、存檔／憑據、環境專用執行設定及模型權重不隨這些提交分發。場景文字映射和裝置專用文件／截圖也未公開。未在本倉庫列出的其他歷史專案，不推定已上傳或完成。

main保留階段提交歷史；根目錄舊script資料夾已透過可恢復提交移除。各元件的授權與重現條件以各自README為準。


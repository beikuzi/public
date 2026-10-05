# 角色音訊工作流與證據

這裡公開的是原始碼、合成測試、來源授權資料及有限的機器測量結果。原始聲音、影片／DVD、模型權重、聲紋向量、完整逐字稿和私人資料集不隨此倉庫分發。

## Elephants Dream 多來源路線

- [來源與授權](second-source-research/public_source/PROVENANCE.md)：20份角色標記的製作WAV，CC BY2.5來源證據及保存副本限制。角色檔名不等於已認證的乾淨獨立人聲。
- [分段對齊](elephants-alignment/publish/README.md)：製作素材與成片之間存在剪接差異，需逐段對齊並去重。機器匹配範圍不等於完整句界或可用訓練時長。
- [品質篩選與實際分離](elephants-quality/PUBLIC_README.md)：數值篩選、實際電影情境的Demucs運行與有限測量；不把低能量或ASR結果當成人工聽感證明。
- [多來源組裝](elephants-dataset/README.md)：半開區間的整數音訊影格映射、5–10秒輸出、來源雜湊、配對版本及獨立的間隔／補零核算。

最新原始碼檢查：組裝17項、對齊7項、品質篩選8項測試，在普通及Python最佳化模式通過。合成測試只驗證程式行為，不能證明真實素材完全無雜音。

## 先前的單來源路線

[通用註記管線](pipeline/README.md)、[分離基線](separation/README.md)、[字幕句界審查](boundary-audit/README.md)和[說話人證據](speaker-verification/README-public.md)保留各自的實驗範圍與限制。

## 結果解讀

`clean/raw` 在多來源路線中只表示通過明確機器篩選的角色標記製作素材候選，不是人工確認乾淨。`noisy/raw` 是匹配的成片混音，`noisy/voice_only` 是處理後的人聲估計，可能殘留其他人聲或背景。

同一段素材的製作版、成片版與分離版是不同視角，不能加總成三倍的新聲音。成片／分離輸出的機器語音時長採映射的作者來源VAD估計，並非再次測得的純人聲時長。人工聽審、無重疊、角色唯一性、乾淨程度及訓練就緒狀態均未確認。版權授權也不等於取得聲音仿製、人格或背書權利。

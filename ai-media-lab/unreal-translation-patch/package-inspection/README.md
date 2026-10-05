# 封裝資源探測：可重現的限制驗證

此模組只讀取 PAK 的索引與中繼資料，**不解包、不解壓縮、不提取遊戲文本**。第一階段 `../extraction/` 的 17 筆逐筆驗證結果保持不變。

## 實際查驗結果

1. [ShooterGame benchmark-v1.3 作者發行包](https://github.com/cqcallaw/shootergame/releases/tag/benchmark-v1.3)：PAK v11，索引加密。讀到標記後停止，不尋找金鑰。
2. [Bomberrage 23-06-2026 作者發行包](https://github.com/JanSeliv/Bomber/releases/tag/23-06-2026)：10 份 PAK v12 全部標記索引加密。作者專案雖提供獨立本地化參考檔，但不能據此聲稱封裝檔提取成功。
3. [Elemental Code 的 DLC Simulator](https://elementalcode.itch.io/dlc-simulator)：5 份 PAK v11 未加密，可讀索引。主包 2,172 筆索引項目；主索引、路徑雜湊索引及完整目錄索引的 SHA-1 均吻合。主包僅找到 3 份引擎／線上子系統 `.locres`，全部採 Oodle 壓縮，沒有找到遊戲自身本地化 `.locres`。其餘 4 份 DLC PAK 未找到 `.locres`。

因此，完整「真實遊戲封裝 → 遊戲文本」驗證**尚未成立**。2,172 是檔案索引項目數，不是文字數，也不是已提取檔案數。SHA-1 在此只用於檔案格式完整性檢查，不代表來源認證或數位簽章。

沒有執行下載包內的任何 EXE／DLL，沒有執行第三方 GitHub 程式，也沒有解密。發行 ZIP、PAK、遊戲資產與完整文字不納入此原始碼交付。只有程式、測試及不含遊戲內容的中繼資料報告。

## 本機使用（PowerShell）

Python 3.9+，僅標準函式庫：

```powershell
cd .\package-inspection
python -m unittest -v
python .\pak_index.py 'D:\your-authorized-game\Content\Paks\game.pak'
```

需要另存 JSON 時，加 `--json .\my-report.json`。檔案已存在便拒絕寫入，不覆寫輸入或已有輸出。

回傳碼：

- `0`：v11 索引探測完成；仍未解碼任何內容。
- `3`：已確認索引加密，或認得 v12 頁尾但尚不支援其索引解析。
- `2`：檔案損毀、雜湊不符、超出界限或不支援的結構。

加密檔案只讀頁尾及邊界資訊即停止，連索引本身也不解碼。v12 只辨認頁尾；不聲稱支援其 UTF-8 索引。v11 未壓縮／Oodle 等欄位只是中繼資料，並非解壓能力。

## 重現實測

`results/package-candidate-audit.json` 含三個作者來源、官方 ZIP 檔名、大小及 SHA-256。從上述作者頁面正常下載相同發行包後，可使用標準 ZIP 工具只解出 PAK，不啟動程式。`expected-paks.json` 記錄被測 PAK 的檔名、大小、SHA-256 及預期狀態。

為避免不同遊戲的同名檔案衝突，實測本機檔名採以下規則：

- ShooterGame：`ShooterGame-WindowsNoEditor.pak`。
- Bomberrage：原始 PAK basename 前加 `Bomber-`，例如 `Bomber-Bomber-Windows.pak`。
- DLC Simulator：原始 PAK basename 前加 `DLC-`，例如 `DLC-pakchunk0-Windows.pak`。主包在普通路徑與 `OFFLINE PATCH` 重複，只保留一份。

將這 16 份已獲授權的本機 PAK 放在同一資料夾，再執行：

```powershell
python .\replay_local.py 'D:\pak-validation'
```

預期 `verified_paks: 16`、`payloads_extracted: 0`、`text_extraction_validated: false`。缺檔或 SHA-256 不符會失敗，不會跳過。下載頁面未來若更換內容，此重現也應停止。

`expected-inspections.json` 是隨原始碼提供的固定、已去除遊戲內容的中繼資料基準；重放會逐欄比較完整結果，不依賴 `results/` 資料夾。`results/real-package-inspections.json` 是開發時產生的同次實測輸出，可不隨原始碼 ZIP 交付。測試中的自造小型 PAK 只驗證格式與邊界，不冒充真實遊戲。

## 安全界限與下一個必要條件

索引讀取上限 64 MiB、項目上限 100 萬；檢查偏移、長度、字串結尾、編碼、雜湊、重複路徑及項目計數。未實作非編碼項目、裁剪目錄回復、解密、payload 解包或任何編碼器。索引中出現的 `../../../` 掛載點僅呈現為文字，絕不拿它建立路徑或寫出檔案。

下一個能成立的完整驗證，需要作者公開且未加密的「遊戲自身本地化資源」封裝、同版本獨立 archive／PO／CSV 參考，以及可合法安全使用的編碼器。優先找未壓縮或 zlib 封裝；不能把引擎文字或自行製造封裝當成完整遊戲驗證。若必須執行未認證來源的解碼器，需先取得相應批准。

格式欄位參考 [repak 的作者原始碼](https://github.com/trumank/repak/tree/master/repak/src)（MIT／Apache-2.0）；只閱讀格式，沒有執行或納入該實作。此處是獨立撰寫的有界只讀探測器。

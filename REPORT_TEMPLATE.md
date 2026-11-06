# HW4 — Vision-Based UI using Background Subtraction

> 將方括號中的提示替換成實際資訊。結果須來自 `results/` 中實際完成的 CSV；不要用模擬數值補齊尚未進行的試驗。

## 1. 作業目的

本作業實作 Vision-Based Touchless Document Reader，使用攝影機和 Background Subtraction 偵測指定 Hot Zones 中的前景變化，並以變化比例門檻觸發閱讀指令。

研究問題：

- [說明本作業如何以非接觸式視覺操作閱讀器]
- [說明比較門檻與環境光線條件的原因]

## 2. 辨識原理與程式實作

### 2.1 Background Model 與 Foreground Mask

系統使用 OpenCV MOG2 建立背景模型。每張攝影機畫面經過背景減除與陰影像素過濾後，產生二值 Foreground Mask；白色像素代表相對於背景模型的變化。

### 2.2 六個 Hot Zones 與 ROI

介面閱讀區占上方 78%，左、右半部各為 Previous Page、Next Page。底部 22% 分為 Zoom In、Zoom Out、Menu、Settings 四區。攝影機影像依相同比例分割成六個 ROI。

| Zone | 指令 | ROI 位置 |
|---|---|---|
| Z1 | Previous Page | 上方 78% 左半部 |
| Z2 | Next Page | 上方 78% 右半部 |
| Z3 | Zoom In | 底部工具列第 1 格 |
| Z4 | Zoom Out | 底部工具列第 2 格 |
| Z5 | Menu | 底部工具列第 3 格 |
| Z6 | Settings | 底部工具列第 4 格 |

每區的 `motion_ratio = changed_pixels / zone_area`，避免不同 ROI 面積造成絕對像素數不易比較。系統需連續 K 個影格超過門檻才觸發；預設 K = 3、Cooldown = 1 秒，並等待該區變化量降至釋放門檻後重新啟用。正式實驗期間固定 K 與 Cooldown，Experiment 2 僅改變 motion ratio 門檻。

**辨識限制：** HW4 只判斷 foreground change，不辨識變化物體是否為手。本作業未使用 MediaPipe Hands、Hand Landmark、Hand Center、Wrist、Skin Segmentation、YOLO 或其他 Hand Detection 技術。

### 2.3 六個指令與視覺回饋

- Previous / Next：頁碼限制於第 1 至第 8 頁。
- Zoom In / Out：每次調整 10%，範圍 50%–200%。
- Menu：顯示目前頁碼、跳至第一頁、跳至最後一頁、關閉。
- Settings：切換 Light / Dark Theme、重設縮放、關閉。
- [描述觸發區反白、目前頁碼、縮放比例與 Last Command 回饋]

## 3. 介面與實驗設計

閱讀器使用 8 張 PNG 文件頁面與共用 6 Zone 版面。攝影機診斷視窗並列顯示鏡像攝影機畫面及 Foreground Mask。

### 3.1 Pilot 與門檻選擇

Pilot 在正常光線下記錄實際觸發的 motion ratio。由 Pilot 分布產生第 25、50、75 百分位的 Low、Medium、High 建議門檻，並於正式 Experiment 2 前檢視及確認。

| Pilot 有效樣本數 | Low (25th percentile) | Medium (50th percentile) | High (75th percentile) |
|---:|---:|---:|---:|
| [填寫] | [填寫 %] | [填寫 %] | [填寫 %] |

### 3.2 Experiment 1 — 6 Commands Basic Accuracy

- 條件：Normal Lighting、固定門檻。
- 設計：6 個指令各 5 次，共 30 次。
- 記錄：target / triggered zone 與 command、correct、motion ratio、trigger time、false trigger。

### 3.3 Experiment 2 — Threshold Test

- 條件：Normal Lighting；Low、Medium、High 三組門檻。
- 指令：Previous、Next、Zoom In。
- 設計：3 指令 × 3 門檻 × 3 次，共 27 次。

### 3.4 Experiment 3 — Lighting Interference Test

- 條件：Normal Lighting、Dim Lighting。
- 指令：Previous、Next、Zoom In。
- 設計：3 指令 × 2 光線條件 × 3 次，共 18 次。變更光線後先讓背景模型重新穩定。

總計：30 + 27 + 18 = **75 次正式試驗**。

每筆目標和條件會先顯示，攝影機背景穩定且使用者確認準備好後才開始 8 秒計時。Experiment 3 切換光線時先重設背景模型；背景重新穩定所需時間不納入觸發時間。

## 4. 實驗結果與討論

執行 `python analyze_results.py` 產生以下表格，再將摘要填入報告。另將各實驗的 CSV 與原始截圖一併保存。

### 4.1 Experiment 1：基本準確度

[貼上 Experiment 1 整體與各指令摘要表。]

- Overall Success Rate：[填寫]
- 各指令成功率：[填寫]
- False Trigger Count：[填寫]
- Mean Trigger Time：[填寫]

### 4.2 Experiment 2：門檻比較

[貼上各門檻 × 指令摘要表。]

- Low：[填寫觀察]
- Medium：[填寫觀察]
- High：[填寫觀察]
- 門檻改變對成功率、誤觸、漏觸及觸發時間的影響：[填寫]

### 4.3 Experiment 3：光線影響

[貼上 Normal / Dim Lighting × 指令摘要表。]

- Normal Lighting：[填寫]
- Dim Lighting：[填寫]
- Mean Motion Ratio 與 Mean Trigger Time 的變化：[填寫]

### 4.4 錯誤案例與討論

- False Trigger / Missed Trigger 案例：[依 CSV 與截圖描述]
- Background Subtraction 的優點：[填寫]
- Background Subtraction 的限制：[填寫]
- 對免持文件閱讀器操作體驗的影響：[填寫]

## 5. 截圖與資料檢核

- [ ] 完整 Document Reader UI
- [ ] Foreground Mask
- [ ] Previous Zone 觸發
- [ ] Next Zone 觸發
- [ ] Bottom Toolbar Zone 觸發
- [ ] Normal Lighting
- [ ] Dim Lighting
- [ ] False Trigger 或 Missed Trigger（若有）
- [ ] Experiment 1 / 2 / 3 CSV
- [ ] 分析摘要

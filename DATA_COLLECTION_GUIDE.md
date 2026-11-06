# HW4 資料蒐集操作指南

## 1. 啟動與相機畫面

在「作業四」資料夾執行：

```bash
python3 app.py
```

程式會開啟 Document Reader 與 Camera Diagnostics。第一次使用時，允許系統存取攝影機。Reader 上半部左／右區分別是上一頁、下一頁；下方四格是放大、縮小、Menu、Settings。Diagnostics 也以相同版面比例標示 Z1–Z6。

相機固定後，讓測試者與背景在正常光線下先保持靜止，按 **Reset Background Model**。等待 Diagnostics 狀態顯示 **Ready**，並確認沒有動作時各 Zone 的 Motion ratio 接近低值。若靜止時數值仍偏高，先固定鏡頭、停止移動並重設背景；不要在背景尚未穩定時開始試驗。測試者可以留在鏡頭畫面中，但背景學習期間要保持靜止。

本方法只偵測畫面變化，不知道變化是不是手。正式操作時一次只在一個 Zone 做短暫動作，移開動作後等狀態回到 **Ready**，再開始下一筆，避免身體同時跨過多個區域。

## 2. 建議辨識設定

Diagnostics 的數值意義如下：

- **Threshold**：各 Zone 的 changed pixels / zone area 百分比。初始值為 **2.5%**，僅作為開始操作的參考值。
- **Consecutive frames**：連續超過門檻幾個影格才觸發，建議固定 **3**。
- **Cooldown**：兩次觸發間的冷卻時間，建議固定 **1.0 秒**。

先用預設值做 Pilot。若正常幅度的動作很少觸發，可小幅降低門檻；若靜止畫面也觸發，先重設背景並確認畫面穩定，再視情況提高門檻。Pilot 一旦開始，盡量固定門檻；如果必須調整，停止目前 Pilot 後再重新收集，避免把不同設定混成同一批樣本。

正式實驗期間程式會鎖住 Threshold、Consecutive frames、Cooldown 設定；Experiment 2 只會依試驗條件更換門檻。切換光線時，依 Runner 的準備按鈕重設背景模型。

## 3. Pilot 與門檻選擇

1. 開啟 **Experiment → Open Experiment Runner**，選 **Pilot Calibration**，按「開始 Pilot 收集」。同一按鈕會在收集期間變成「停止 Pilot 收集」。
2. 確認正常光線及背景已 Ready。以平常操作的幅度，分別在不同 Zone 做短暫動作；每次動作後收回並等 Ready。每次成功觸發會把 Zone、motion ratio、當下門檻寫入本次獨立的 `pilot-data/pilot-motion-ratios_*.csv`。
3. 再按同一顆「停止 Pilot 收集」按鈕結束收集，接著按「以 Pilot 分位數填入建議值」。工具會以樣本的第 25、50、75 百分位產生 Low、Medium、High 建議值，單位是百分比。
4. 檢視分布。如果建議值相同或很接近，依 Pilot 的 motion ratio 分布手動設定三個遞增且有區別的值；不要直接把相同門檻當成三個條件。
5. 若要重新調整 Pilot 門檻，停止後重新開始 Pilot 會建立新的 CSV；分位數按鈕使用最近一次 Pilot 的樣本，不會混合不同 Pilot 設定。為了讓 Experiment 1 與 3 使用同一個固定基準，可先將 Diagnostics 的門檻調成你選定的基準值（例如採用 Medium 作為基準），再開始各正式流程。每個 CSV 會保存實際使用的門檻。

如果 Pilot 完全沒有樣本，先確認 Diagnostics 狀態是否為 Ready、目標 Zone 的 ratio 是否會隨動作上升；再略微降低門檻後重新開始 Pilot。若沒有動作時 ratio 仍高，先改善背景穩定度，不要只靠提高門檻掩蓋不穩定畫面。

## 4. Experiment 1 — Basic Accuracy（30 次）

1. 在正常光線下，確認鏡頭與背景穩定；設定並固定基準門檻、K = 3、Cooldown = 1.0 秒。
2. 選 **Experiment 1 - Basic Accuracy (30 trials)**，按「開始流程」。Runner 會先顯示第一筆目標區與條件。
3. 等相機 Ready，確認條件後按「我已準備好，開始計時」。從此刻起有 8 秒執行目標操作。
4. 成功或誤觸會立即結束該筆並記錄；8 秒內沒有任何觸發則記為 Missed Trigger。回到靜止、等 Runner 啟用下一筆後再繼續。
5. 六個指令各五次，共 30 次。資料寫入 `results/experiment1_*.csv`。

## 5. Experiment 2 — Threshold Test（27 次）

1. 維持正常光線與相同背景。先在門檻欄填入 Pilot 推導的 Low、Medium、High 百分比，確認 `Low < Medium < High`。
2. 選 **Experiment 2 - Threshold Test (27 trials)**，開始流程。每筆開始前 Runner 會顯示該筆的門檻和目標命令。
3. 等相機 Ready 後按「我已準備好，開始計時」，再操作目標區。K 與 Cooldown 在整個流程中維持固定。
4. Previous、Next、Zoom In 各在三種門檻下測三次，共 27 次。資料寫入 `results/experiment2_*.csv`。

## 6. Experiment 3 — Lighting Test（18 次）

Experiment 3 將條件分成正常與昏暗兩組，每組包含 Previous、Next、Zoom In 各三次。每一筆都先完成條件準備，計時才會開始：

1. 選 **Experiment 3 - Lighting Test (18 trials)**，按「開始流程」。Runner 會**先顯示尚未開始的光線條件、門檻與目標命令**，此時尚未計時。
2. 將環境調成畫面顯示的光線條件，按 **準備光線條件並重設背景**。這會重建背景模型，不會開始該筆試驗的計時。
3. 保持畫面靜止，等待 Diagnostics 顯示 **Ready**。Runner 會啟用 **我已準備好，開始計時** 按鈕。
4. 確認光線與目標區都準備好後，再按 **我已準備好，開始計時**。**8 秒計時從這次按鈕操作才開始**；按鈕啟用前的調光與背景學習時間不會列入觸發時間。
5. 同一光線條件下的後續試驗不必每次重設背景，但仍須等上一筆動作消失、Diagnostics 回到 Ready。Runner 顯示另一種光線時，再切換條件並按準備按鈕重設背景。
6. 兩種光線各 9 次，合計 18 次。資料寫入 `results/experiment3_*.csv`。

## 7. 截圖、分析與檔案位置

程式會在 `screenshots/` 儲存每個 Zone 首次觸發、正常／昏暗光線條件及誤觸／漏觸證據。Diagnostics 的 **Save Mask Screenshot** 會保存攝影機畫面與 Foreground Mask；Reader 的 **File → Save Reader Screenshot** 會保存完整介面。

完成三組試驗後，在專案資料夾執行：

```bash
python analyze_results.py
```

需要將摘要存檔時：

```bash
python analyze_results.py --output results/summary.md
```

正式資料位於 `results/`，Pilot 資料位於 `pilot-data/`，截圖位於 `screenshots/`。報告填寫範本是 `REPORT_TEMPLATE.md`。

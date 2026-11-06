# HW4 — Vision-Based UI using Background Subtraction

以 OpenCV 背景減除實作免持文件閱讀器。系統依攝影機畫面中六個 Hot Zones 的前景變化比例觸發閱讀指令；不使用手部偵測或手部關鍵點。

## 環境需求

- Python 3.9 以上
- 可用的攝影機
- Tkinter（macOS Python 通常已內建；Linux 可由系統套件安裝）

## 安裝與啟動

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

啟動後會開啟 Document Reader 與攝影機診斷視窗。允許攝影機權限後，讓鏡頭拍到穩定背景並等待背景模型完成學習。診斷視窗會同時顯示攝影機影像、前景遮罩、六區變化比例與門檻控制。使用者在鏡頭影像中對應的操作區移動，即可觸發閱讀器指令。完整的設定與資料蒐集步驟請見 [`DATA_COLLECTION_GUIDE.md`](DATA_COLLECTION_GUIDE.md)。

## 操作與實驗流程

1. 在診斷視窗完成相機、背景與門檻設定；預設 K = 3、Cooldown = 1 秒、初始 motion ratio 門檻 = 2.5%。
2. 從「Experiment → Open Experiment Runner」開啟實驗工具。先選 Pilot，在正常光線下收集實際觸發 motion ratio。
3. 停止 Pilot，檢視第 25、50、75 百分位門檻建議值；選好正式實驗的固定基準門檻後，再開始 Experiment 1、2、3。
4. Runner 會先顯示下一筆的目標與條件。Experiment 3 需先切換光線並按「準備光線條件並重設背景」，等診斷狀態 Ready，再按「我已準備好，開始計時」；正式試驗的 8 秒計時不包含準備時間。
5. 正式流程期間會固定 K 與 Cooldown，Experiment 2 只改變門檻。每筆觸發後自動記錄；逾時會記為漏觸。
6. 每筆正式試驗完成後會立即寫入獨立 CSV：`results/experiment1_*.csv`、`results/experiment2_*.csv`、`results/experiment3_*.csv`。每次 Pilot 寫入獨立的 `pilot-data/pilot-motion-ratios_*.csv`。
7. 完成實驗後執行 `python analyze_results.py`，或指定一個以上的實驗 CSV；需要另存摘要時加上 `--output results/summary.md`。

首次觸發各 Zone、正常／昏暗光線條件及誤觸／漏觸時，程式會在 `screenshots/` 自動儲存證據圖。完整介面與前景遮罩也可由視窗按鈕手動儲存。

## 專案內容

- `HW4_Background_Subtraction_Experiment_Plan.md`：作業目標、三組實驗與報告要求。
- `Touchless_Document_Reader_UI.md`：HW4 / HW5 共用的操作介面規格。
- `assets/pages/`：閱讀器使用的 8 張文件頁面圖片。
- `background_subtraction.py`：MOG2、ROI motion ratio 與連續影格觸發邏輯。
- `experiment_runner.py`：Pilot、75 次實驗排程、逐次 CSV 記錄與證據截圖。
- `analyze_results.py`：成功率、誤觸、漏觸、變化比例及觸發時間摘要。
- `results/`、`pilot-data/`：執行後建立的實驗資料 CSV，可納入作業版本紀錄。
- `screenshots/`：介面、前景遮罩及實驗條件截圖。
- `REPORT_TEMPLATE.md`：作業報告架構與填寫提示。
- `DATA_COLLECTION_GUIDE.md`：相機設定、門檻選擇與三組實驗逐步操作方式。

本作業只使用 Background Subtraction 判斷各區域前景變化，不使用 Hand Detection、Hand Landmark 或 Skin Segmentation。

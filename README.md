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

啟動後會開啟 Document Reader 與攝影機診斷視窗。請讓攝影機拍到背景，等待背景模型穩定，再將動作放入預覽畫面對應的操作區。實驗記錄器可由「實驗」選單開啟。

## 專案內容

- `HW4_Background_Subtraction_Experiment_Plan.md`：作業目標、三組實驗與報告要求。
- `Touchless_Document_Reader_UI.md`：HW4 / HW5 共用的操作介面規格。
- `assets/pages/`：閱讀器使用的 8 張文件頁面圖片。
- `results/`：實驗記錄 CSV 輸出位置。
- `screenshots/`：作業截圖輸出位置。

操作、實驗記錄與報告填寫方式請見 `REPORT_TEMPLATE.md`（完成實驗功能後補上）。

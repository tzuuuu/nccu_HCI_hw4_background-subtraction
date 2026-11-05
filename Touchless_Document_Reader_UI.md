# Touchless Document Reader — 共用系統介面規格

## 1. 系統定位

本系統為 HW4 與 HW5 共用的 Vision-Based Touchless Document Reader。

兩份作業共用相同的文件閱讀介面、6 個操作區域、文件內容、Command Actions、攝影機輸入與 UI feedback；差別只在辨識方法：

| 作業 | 辨識方法 |
|---|---|
| HW4 | Background Subtraction |
| HW5 | Hand Detection |

HW4 不得使用 Hand Detection / Hand Landmark / Skin Segmentation。
HW5 則以 Hand Detection 為主要輸入辨識方法，不再以 Background Subtraction 的變化量作為主要選擇依據。

---

## 2. 介面配置

整個文件頁面顯示於背景。

閱讀區覆蓋兩個半透明大型操作區：
- 左半部：Previous Page
- 右半部：Next Page

底部為四個工具列區域：
- Zoom In
- Zoom Out
- Menu
- Settings

總共 6 個操作區域。

```text
┌──────────────────────────────────────────────┐
│                                              │
│          Document / Reading Content          │
│                                              │
│  ┌──────────────────┬───────────────────┐    │
│  │                  │                   │    │
│  │    Previous      │       Next        │    │
│  │       ←          │        →          │    │
│  │                  │                   │    │
│  └──────────────────┴───────────────────┘    │
│                                              │
├───────────┬───────────┬───────────┬──────────┤
│ Zoom In   │ Zoom Out  │   Menu    │ Settings │
│    +      │    -      │    ☰      │    ⚙     │
└───────────┴───────────┴───────────┴──────────┘
```

## 3. Zone 定義

| Zone | 位置 | 功能 |
|---|---|---|
| Z1 | 閱讀區左半部 | Previous Page |
| Z2 | 閱讀區右半部 | Next Page |
| Z3 | 底部工具列第 1 格 | Zoom In |
| Z4 | 底部工具列第 2 格 | Zoom Out |
| Z5 | 底部工具列第 3 格 | Menu |
| Z6 | 底部工具列第 4 格 | Settings |

## 4. 建議區域比例

若畫面寬度為 W、高度為 H：

```text
Reading Area:
0 <= y < 0.78H

Toolbar:
0.78H <= y <= H
```

閱讀區：
```text
Z1: x = 0 ~ 0.5W, y = 0 ~ 0.78H
Z2: x = 0.5W ~ W, y = 0 ~ 0.78H
```

底部工具列：
```text
Z3: x = 0 ~ 0.25W
Z4: x = 0.25W ~ 0.50W
Z5: x = 0.50W ~ 0.75W
Z6: x = 0.75W ~ W
```

四區 y 範圍皆為 0.78H ~ H。

## 5. Command 行為

- Z1 Previous Page：上一頁，不得小於第一頁。
- Z2 Next Page：下一頁，不得超過最後一頁。
- Z3 Zoom In：每次 +10%，建議最大 200%。
- Z4 Zoom Out：每次 -10%，建議最小 50%。
- Z5 Menu：顯示 Current Page、Go to First Page、Go to Last Page、Close。
- Z6 Settings：顯示 Light/Dark Theme、Reset Zoom、Close。

## 6. 文件內容

正式 Demo 建議使用 5–10 頁已轉成 PNG/JPG 的文件頁面，不要求真正解析 PDF，以避免作業重心移到 PDF renderer。

## 7. 視覺回饋

所有 Zone 平時低透明度顯示；接近觸發或觸發時加深框線/透明度。

建議顯示：
```text
Current Page: 3 / 8
Zoom: 120%
Last Command: Next Page
```

## 8. HW4 使用方式

```text
Camera
→ Background Subtraction
→ Foreground Mask
→ 每個 Zone 的變化量
→ Threshold
→ Trigger Command
```

HW4 禁止使用 MediaPipe Hands、Hand Landmark、Hand Center、Wrist、Skin Segmentation、YOLO Hand Detection。

## 9. HW5 使用方式

```text
Camera
→ Hand Detection
→ Hand Reference Point
→ 判斷所在 Zone
→ Dwell / Consecutive Frame Confirmation
→ Trigger Command
```

建議固定使用 Wrist 作為 Hand Reference Point。

## 10. Frozen UI Decisions

```text
System = Touchless Document Reader
Zones = 6
Z1 = Previous
Z2 = Next
Z3 = Zoom In
Z4 = Zoom Out
Z5 = Menu
Z6 = Settings
Reading area = upper 78%
Toolbar = lower 22%
Document pages = image-based pages
```

HW4 / HW5 不得自行改成不同 layout。

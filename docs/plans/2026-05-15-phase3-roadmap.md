---
title: Phase 3 進階功能開發計畫
author: Hermes Agent
date: 2026-05-15
status: Planning
---

# 📋 Phase 3 進階功能開發計畫 (Roadmap)

針對現有 AI 人臉打卡系統 (v2.2.0)，規劃下一階段四大核心功能。目標是提升系統安全性、擴展性以及管理價值。

---

## 🛡️ Feature 1: 活體檢測 (Anti-Spoofing / Liveness Detection)
> **最高優先級 (P0)**：解決「拿照片/影片騙過系統」的安全漏洞。

### 1. 技術選型 (Tech Stack)
推薦使用 **「靜默活體檢測 (Silent Liveness)」**，使用者無需眨眼或搖頭，系統自動判斷。

| 方案 | 優點 | 缺點 | 推薦度 |
|------|------|------|--------|
| **MiniVision (Face-Anti-Spoofing)** | 輕量級、準確率高、Python 支援好 | 需要自行編譯部分依賴 | ⭐⭐⭐⭐⭐ |
| **Silently (CVPR 2022)** | 學術界最新成果，抗攻擊性強 | 模型較大，延遲較高 | ⭐⭐⭐⭐ |
| **InsightFace (內建)** | 與現有系統整合最快 | 支援度較舊，準確度普通 | ⭐⭐⭐ |

**✅ 決定方案：** 採用 **MiniVision** (或類似開源庫如 `face-anti-spoofing`)。

### 2. 實作邏輯 (Implementation)
在 `main.py` 的檢測迴圈中，於「人臉比對 (Recognition)」之前插入活體檢查。

```python
# Pseudo-code logic in main.py
if face_detected:
    # 1. 活體檢測 (新增)
    is_real = liveness_detector.check(face_region)
    
    if not is_real:
        show_warning("⚠️ 偵測到非活體 (照片/影片)!")
        continue  # 跳過比對，不記錄打卡

    # 2. 正常比對
    name = face_db.match(face_region)
    ...
```

### 3. 效能優化 (Performance)
- 活體檢測會增加約 50-100ms 的延遲。
- **優化策略：** 每 3 幀執行一次活體檢測，或者僅在 `track_id` 首次出現時執行。

### 4. 任務拆解
- [ ] **Task 1.1**: 建立 `src/liveness_detector.py`，封裝模型載入與推論邏輯。
- [ ] **Task 1.2**: 下載並整合活體檢測權重檔 (`weights.pth` 或 `onnx`)。
- [ ] **Task 1.3**: 修改 `main.py` 整合活體檢查流程。
- [ ] **Task 1.4**: 撰寫測試：使用螢幕播放人臉影片 vs 真人，驗證拒絕率 (FAR/FRR)。

---

## 💰 Feature 2: 薪資與考勤計算 (Payroll Integration)
> **價值提升 (P1)**：從單純的「紀錄工具」變成「管理工具」。

### 1. 功能規劃
- **規則引擎**：
  - 遲到規則：`> 09:00` 且 `< 09:15` (不計扣薪)，`> 09:30` (扣半日薪)。
  - 早退規則：`< 18:00` 且 `< 17:30` (扣半日薪)。
  - 加班計算：`> 18:00` 後每 30 分鐘 = 1 小時加班費。
- **匯出格式**：生成 `.xlsx` (Excel) 薪資明細表。

### 2. 任務拆解
- [ ] **Task 2.1**: 新增 `src/payroll_engine.py` (規則計算核心)。
- [ ] **Task 2.2**: 新增 `config.yaml` 中的薪資規則區塊。
- [ ] **Task 2.3**: 整合 `pandas` 或 `openpyxl` 實現 Excel 匯出功能。
- [ ] **Task 2.4**: UI 新增「薪資報表」頁籤 (Admin 專用)。

---

## 🔔 Feature 3: 即時推播通知 (Push Notifications)
> **體驗優化 (P2)**：管理者不需一直盯著螢幕。

### 1. 整合方案
利用 Hermes 既有的 Webhook 或 CLI 功能發送通知。
- **事件觸發**：
  - `GuardStatus.LATE` → 發送「⚠️ [姓名] 遲到 15 分鐘」。
  - `GuardStatus.UNKNOWN` (陌生人) → 發送「🚨 偵測到不明人士」。

### 2. 實作方式
在 `src/guard_engine.py` 回傳異常狀態時，呼叫非同步通知函式。
```python
def notify_user(message):
    # 呼叫外部 API 或寫入通知佇列
    subprocess.run(["telegram-send", "--message", message]) 
```

### 3. 任務拆解
- [ ] **Task 3.1**: 新增 `src/notifier.py`。
- [ ] **Task 3.2**: `config.yaml` 設定通知開關與 Webhook URL。
- [ ] **Task 3.3**: 串接主迴圈的狀態判斷。

---

## 🗄️ Feature 4: 資料庫升級 (Database Migration)
> **擴充性 (P3)**：為未來多人使用做準備。

### 1. 技術選型
- 目前：`SQLite` (單檔案，適合 < 100 人)。
- 未來：`PostgreSQL` 或 `MySQL` (適合 > 1000 人，多併發)。

### 2. 過渡策略
- 引入 **SQLAlchemy (ORM)** 取代原生的 `sqlite3` 語法。
- 這樣只需修改 `config.yaml` 中的 `database_url`，程式碼即可無痛切換資料庫。

### 3. 任務拆解
- [ ] **Task 4.1**: 安裝 `sqlalchemy`。
- [ ] **Task 4.2**: 重構 `src/face_db.py` 和 `src/attendance_logger.py` 使用 ORM。
- [ ] **Task 4.3**: 編寫 Migration 腳本 (將 SQLite 資料轉入 PostgreSQL)。

---

## 🗓️ 建議執行順序

1.  **活體檢測 (Phase 3.1)**：這是最關鍵的安全補丁，防止系統被騙。
2.  **薪資計算 (Phase 3.2)**：讓系統產生實際商業價值。
3.  **推播通知 (Phase 3.3)**：改善使用體驗。
4.  **資料庫升級 (Phase 3.4)**：當系統真的變慢或人多時再做。

# 🤖 AI Face Attendance System | AI 人臉打卡系統

Real-time face recognition attendance system powered by YOLOv8 detection, BYTETrack tracking, and InsightFace recognition. Includes Guard Mode for access control.

由 YOLOv8 偵測、BYTETrack 追蹤和 InsightFace 辨識驅動的即時人臉打卡系統。包含門警模式 (Guard Mode) 用於進出管制。

---

## 🌟 Features | 功能特色

- **Real-time Detection**: YOLOv8 + Supervision (BYTETrack) for person tracking. (即時人臉偵測與追蹤)
- **Face Recognition**: InsightFace ArcFace with high accuracy. (高精度人臉辨識)
- **Auto Check-in/Check-out**: Single camera auto-toggles between entry and exit logging. (單鏡頭自動判斷上下班進出)
- **Liveness Detection (Phase 3)**: Silent Anti-Spoofing to block photos/screens using Mini-FASNet. (活體檢測：防止照片/螢幕造假)
- **Guard Mode (Phase 2)**: Work-hour rules, Late/Abnormal warnings, and Leave/Business exemptions. (門警模式：上下班判定、異常警告、請假/公出差勤豁免)
- **Employee Self-Service**: View personal attendance history and submit leave requests. (員工自助：查看個人打卡歷史、申請單據)
- **Admin Password Management**: Secure SHA-256 hashed passwords with in-app change support. (管理者密碼：SHA-256 雜湊儲存，後台可直接修改)
- **Multi-person Support**: Concurrent status display for multiple people. (支援多人同時進出顯示)
- **Bilingual UI**: English / Traditional Chinese toggle in the web dashboard. (網頁後台支援中英雙語切換)
- **Streamlit Dashboard**: Register employees, view reports, and manage exceptions. (Streamlit 儀表板：員工註冊、報表查詢、單據管理)
- **API Integration**: REST API for ERP/HR system connection. (開放 API 串接 ERP/人資系統)

---

## 🚀 Quick Start | 快速啟動

```bash
# 1. Install dependencies | 安裝依賴套件
pip install -r requirements.txt

# 2. Register employees via Streamlit UI | 透過網頁註冊員工
streamlit run src/ui/streamlit_app.py

# 3. (Optional) Download Liveness Detection Model | 下載活體檢測模型
python scripts/download_models.py

# 4. Run the attendance pipeline | 執行即時視訊打卡
python main.py
```

> Press **`q`** in the terminal to quit. (在終端機按 `q` 退出)

---

## 🔐 Default Credentials | 預設帳號密碼

> ⚠️ **重要：** 首次登入後請立即修改密碼！（管理員：`Settings > 🔑 管理者密碼`；員工：`Employee Portal > 🔐 修改密碼`）

| Role | Default Password | 說明 |
|------|------------------|------|
| **Admin (管理員)** | `admin` | 首次登入後建議立即修改 |
| **Employee (員工)** | `1234` | 員工可自行修改個人密碼 |

- 所有密碼均以 **SHA-256 雜湊** 儲存於 `data/users.db`，非明文。
- 若已修改過密碼，預設值即失效，需使用新密碼登入。

---

## 🛡️ Guard Mode | 門警模式

Toggle Guard Mode in `config.yaml` or the Web UI ("🛡️ Guard Mode" tab) to enable access control rules.

在 `config.yaml` 或網頁版「🛡️ 門警模式」頁面切換開關，即可啟用進出管制。

- **System Status**: Shows current mode and configured work hours. (顯示目前模式與設定的上下班時間)
- **Exception Management**: Add Leave/Business requests to exempt employees from abnormal warnings. (例外管理：新增請假/公出單據，解除異常警告)
- **Visual Feedback**:
    - 🟢 **Normal**: Within work hours. (正常時段)
    - 🔴 **Abnormal**: Late, Early Leave, or After Hours. (異常：遲到/早退/非工作時間)
    - 🔵 **Exempted**: Approved Leave/Business request. (豁免：已核准單據)

---

## 🌐 Bilingual UI | 雙語介面

The system supports **English** and **Traditional Chinese**. You can switch languages instantly in the sidebar of the Streamlit dashboard.

系統支援「英文」與「繁體中文」。你可以在 Streamlit 儀表板的側邊欄即時切換語言。

---

## 📷 IP Camera (RTSP) Setup | 網路攝影機設定

To use an IP camera instead of a USB webcam, update the `source` in `config.yaml`.

若要使用網路攝影機 (IP Camera) 取代 USB 鏡頭，請修改 `config.yaml` 中的 `source`：

```yaml
camera:
  source: "rtsp://admin:12345@192.168.1.50:554/h264/ch1/main/av_stream"
```

**Common Formats | 常見格式:**
- **Hikvision:** `rtsp://admin:password@IP:554/h264/ch1/main/av_stream`
- **Dahua:** `rtsp://admin:password@IP:554/cam/realmonitor?channel=1`

---

## 🏗️ Architecture | 系統架構

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Camera    │────>│   Detector   │────>│   Zone Checker   │
│  (OpenCV)   │     │ YOLOv8 + BT  │     │  (Polygon ROI)   │
└─────────────┘     └──────┬───────┘     └────────┬─────────┘
                           │                      │
                    ┌──────▼───────┐     ┌────────▼─────────┐
                    │   Persons    │────>│  FaceRecognizer  │
                    │  in Zone     │     │  (InsightFace)   │
                    └──────────────┘     └────────┬─────────┘
                                                  │
                                           ┌──────▼───────┐     ┌───────────────┐
                                           │  FaceDatabase │     │ Exception Mgr │
                                           │  (SQLite)     │     │  (Leave/Biz)  │
                                           └──────┬───────┘     └───────┬───────┘
                                                  │                     │
                                           ┌──────▼───────┐     ┌──────▼───────┐
                                           │ AttendanceLog│     │ Guard Engine │
                                           │  (SQLite)    │     │ (Status/Color│
                                           └──────────────┘     └───────┬───────┘
                                                                        │
                                                                 ┌──────▼───────┐
                                                                 │ Video Display│
                                                                 │  (Multi-msg) │
                                                                 └──────────────┘
```

---

## 📦 Tech Stack | 技術堆疊

| Layer | Technology |
|---|---|
| **Detection** | Ultralytics YOLOv8 + Supervision (BYTETrack) |
| **Recognition** | InsightFace ArcFace (buffalo_l) |
| **Storage** | SQLite (faces, attendance, exceptions) |
| **UI** | Streamlit (Bilingual Dashboard) |
| **API** | FastAPI + Uvicorn (ERP Integration) |
| **Video** | OpenCV (Capture + Pillow for Chinese Text) |
| **Logging** | Loguru |

---

## 📂 Project Structure | 專案結構

```
attendance-system/
├── main.py                      # Entry point (Video pipeline)
├── config.yaml                  # Configuration
├── requirements.txt             # Python dependencies
├── src/
│   ├── config.py                # Config loader
│   ├── detector.py              # YOLOv8 + Tracking
│   ├── face_recognizer.py       # InsightFace logic
│   ├── face_db.py               # Face storage
│   ├── attendance_logger.py     # Attendance records
│   ├── guard_engine.py          # Guard mode status logic
│   ├── exception_manager.py     # Leave/Business requests
│   ├── api_server.py            # ERP API endpoints
│   ├── i18n.py                  # Translation dictionary
│   └── ui/
│       └── streamlit_app.py     # Bilingual Web UI
├── docs/
│   └── usage.md                 # Comprehensive usage guide
├── tests/                       # Unit & Integration tests
└── data/                        # Databases (gitignored)
```

---

## 🧪 Testing | 測試

```bash
# Run all tests | 執行所有測試
pytest tests/ -v
```

---

## 🔗 API Endpoints | API 串接

- `GET /api/v1/attendance/today`: Today's records. (今日打卡記錄)
- `GET /api/v1/guard/status?employee_id=...`: Current access status. (目前進出狀態)
- `GET /api/v1/exceptions`: List of approved exceptions. (已核准單據清單)

---

## 📋 Changelog | 更新日誌

### v2.2.0 — 2026-05-15

| 項目 | 說明 |
|------|------|
| 🔄 **Auto Check-in/Check-out** | 單鏡頭自動判斷進出：當日首次偵測記為 `checkin`，後續偵測自動切換為 `checkout` |
| 📊 **Employee Attendance History** | 員工入口新增「📋 我的打卡」分頁，可查看今日打卡記錄與完整歷史 |
| 🔑 **Admin Password Management** | 管理者密碼不再硬編碼，改為可修改的雜湊儲存。設定頁新增「🔑 管理者密碼」區塊 |
| 🔒 **Security Fix** | `exception_manager.py` `created_at` 改為本地時間（UTC → Local Timezone） |
| 🐛 **Bug Fix** | 修復主程式重複疊加訊息區塊的 bug；修復已請假/午休時員工仍顯示「打卡成功」的優先級問題 |
| 🛡️ **Priority Fix** | 例外狀態 (EXEMPTED/LUNCH) 優先級高於打卡成功，畫面正確顯示藍色/青色提示 |
| 🐛 **Fix** | `get_last_event_type()` 改用明確日期範圍比對 (`>=` / `<`)，取代脆弱的 LIKE 字串比對 |
| 🌐 **i18n** | 新增 14 組繁英雙語翻譯鍵值 |

### v2.1.0 — 2026-05-14

| 項目 | 說明 |
|------|------|
| 🛡️ **Guard Mode** | 門警模式：工作時段判定、遲到/早退/非上班時間異常警告 |
| 📝 **Exception Management** | 請假/公出差勤單據申請與審核 |
| 🌐 **Bilingual UI** | 中英文切換介面 |
| 🔐 **Role-Based Access** | 管理員/員工分權登入 |
| 📷 **IP Camera** | RTSP 網路攝影機支援 |

### v2.0.0 — 2026-05-14

| 項目 | 說明 |
|------|------|
| 🚀 **Initial Release** | YOLOv8 + InsightFace 即時人臉打卡系統 |
| 📊 **Streamlit Dashboard** | 員工註冊、即時畫面、報表查詢、CSV 匯出 |
| 🔒 **Cooldown** | 30 分鐘防重複打卡機制 |

---

## 🪟 Windows Installation | Windows 安裝指南

### Prerequisites | 前置需求

- **Python 3.10–3.12**（推薦 3.11）：[python.org/downloads](https://www.python.org/downloads/)
  - ⚠️ 安裝時務必勾選 **"Add Python to PATH"**
- **Git**：[git-scm.com](https://git-scm.com/download/win)
- **Visual C++ Build Tools**：ONNX Runtime 編譯所需
  - 下載 [Build Tools for Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
  - 安裝時勾選 **"C++ 桌面開發"**
- **DirectX / GPU（可選）**：如需 CUDA 加速，需安裝 [NVIDIA CUDA Toolkit 11.8+](https://developer.nvidia.com/cuda-downloads) 與對應驅動

### Step-by-Step | 安裝步驟

```powershell
# 1. Clone the repository
git clone https://github.com/brucetseng625-tech/attendance-system.git
cd attendance-system

# 2. Create a virtual environment (recommended)
python -m venv venv
.\venv\Scripts\activate

# 3. Upgrade pip (avoids build errors on some packages)
python -m pip install --upgrade pip

# 4. Install dependencies
pip install -r requirements.txt
```

### ⚠️ Windows-Specific Notes | Windows 注意事項

1. **ONNX Runtime / InsightFace 安裝**
   - 如果 `pip install insightface` 回報 `onnxruntime` 編譯錯誤，手動安裝預編譯版本：
     ```powershell
     pip install onnxruntime  # CPU-only (推薦先試這個)
     # 或
     pip install onnxruntime-gpu  # GPU 加速
     pip install insightface --no-deps
     pip install protobuf numpy opencv-python
     ```

2. **相機權限**
   - Windows 10/11：**設定 > 隱私權 > 相機** → 確保「允許桌面應用程式存取相機」已開啟
   - 如果 `main.py` 啟動後畫面全黑，檢查是否被防毒軟體阻擋

3. **字型路徑差異**
   - `main.py` 預設載入 macOS 字型 (`/System/Library/Fonts/STHeiti Medium.ttc`)
   - **Windows 需修改 `main.py` 字型路徑**為：
     ```python
     # Windows: Microsoft JhengHei (微軟正黑體)
     font_path = "C:/Windows/Fonts/msjh.ttc"  # 或 msjhbd.ttc (粗體)
     ```

4. **防火牆 / 防毒軟體**
   - 部分防毒軟體會阻擋 Python 存取 webcam，需將 Python 新增至白名單
   - Windows Defender：**設定 > 隱私權與安全性 > Windows 安全性 > 應用程式與瀏覽器控制 > 應用程式隔離**

5. **Streamlit 防火牆提示**
   - 首次執行 `streamlit run src/ui/streamlit_app.py` 時，Windows 防火牆可能彈出提示
   - 選擇「允許存取」（私人網路即可）

6. **路徑分隔符**
   - PowerShell 中使用 `.\venv\Scripts\activate`（注意反斜線）
   - 避免在路徑中使用空白或中文目錄名稱

7. **GPU 加速（可選）**
   - 僅限 NVIDIA 顯卡。安裝後修改 `src/face_recognizer.py`：
     ```python
     self.detector.prepare(ctx_id=0, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
     ```

### Quick Test | 快速驗證

```powershell
# Verify installation
python -c "import cv2; import insightface; import ultralytics; print('All dependencies OK')"

# Start Streamlit UI
streamlit run src/ui/streamlit_app.py

# Run camera pipeline
python main.py
```

---

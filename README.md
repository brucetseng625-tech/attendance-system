# 🤖 AI Face Attendance System | AI 人臉打卡系統

Real-time face recognition attendance system powered by YOLOv8 detection, BYTETrack tracking, and InsightFace recognition. Includes Guard Mode for access control.

由 YOLOv8 偵測、BYTETrack 追蹤和 InsightFace 辨識驅動的即時人臉打卡系統。包含門警模式 (Guard Mode) 用於進出管制。

---

## 🌟 Features | 功能特色

- **Real-time Detection**: YOLOv8 + Supervision (BYTETrack) for person tracking. (即時人臉偵測與追蹤)
- **Face Recognition**: InsightFace ArcFace with high accuracy. (高精度人臉辨識)
- **Guard Mode (Phase 2)**: Work-hour rules, Late/Abnormal warnings, and Leave/Business exemptions. (門警模式：上下班判定、異常警告、請假/公出差勤豁免)
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

# 3. Run the attendance pipeline | 執行即時視訊打卡
python main.py
```

> Press **`q`** in the terminal to quit. (在終端機按 `q` 退出)

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

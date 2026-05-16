# Attendance System — Windows 安裝指南

> 適用於 **Windows 10/11**，Python 3.10–3.12
> 最後驗證日期：2026-05-18

---

## 一、前置需求

### 1. Python 3.10–3.12

- 下載：https://www.python.org/downloads/
- **安裝時務必勾選「Add Python to PATH」**
- 驗證：打開 PowerShell 執行 `python --version`

### 2. Git

- 下載：https://git-scm.com/download/win
- 驗證：`git --version`

### 3. Visual C++ Build Tools（必要！）

InsightFace / ONNX Runtime 需要 C++ 編譯器。

- 下載：https://visualstudio.microsoft.com/visual-cpp-build-tools/
- 執行安裝程式，勾選 **「使用 C++ 的桌面開發」**
- 不需要安裝完整的 Visual Studio IDE，只需要 Build Tools 即可

### 4. NVIDIA GPU 加速（可選，僅限 NVIDIA 顯卡）

如需 GPU 加速，需安裝：
- **NVIDIA CUDA Toolkit 11.8+**：https://developer.nvidia.com/cuda-downloads
- 對應的顯示驅動程式

CPU 模式可直接執行，不需要額外安裝。

---

## 二、安裝步驟

### Step 1：Clone 專案

```powershell
# 選一個你喜歡的位置，例如桌面或 Documents
cd $HOME\Desktop
git clone https://github.com/brucetseng625-tech/attendance-system.git
cd attendance-system
```

### Step 2：建立 Python 虛擬環境

```powershell
python -m venv venv
```

### Step 3：啟動虛擬環境

```powershell
# 注意：Windows 使用反斜線 + Scripts 目錄
.\venv\Scripts\activate
```

啟動後命令提示字元前面會顯示 `(venv)`。

### Step 4：升級 pip

```powershell
python -m pip install --upgrade pip
```

### Step 5：安裝依賴套件

```powershell
pip install -r requirements.txt
```

> ⏱ 這個步驟可能需要 5–15 分鐘，視網路速度而定。
> 會安裝約 100+ 個套件，包含 PyTorch、Ultralytics、InsightFace、Streamlit 等。

### Step 6：（可選）下載活體檢測模型

```powershell
python scripts/download_models.py
```

如果 `models/fasnet.onnx` 已存在則會跳過。

---

## 三、驗證安裝

### 快速驗證（所有依賴是否正常）

```powershell
python -c "import cv2; import insightface; import ultralytics; import streamlit; print('All dependencies OK')"
```

正常應顯示 `All dependencies OK`。

### 執行測試

```powershell
pytest tests/ -v
```

> **已知測試失敗**（非安裝問題，程式碼本身的 bug）：
> - `test_different_event_not_blocked` — cooldown 邏輯需修正
> - 5 個 `TestProcessRegistration` 測試 — `_process_registration` 函數不存在

---

## 四、啟動系統

### 1. Streamlit 儀表板（員工註冊、報表、設定）

```powershell
streamlit run src/ui/streamlit_app.py
```

- 瀏覽器會自動打開 `http://localhost:8501`
- 首次執行 Windows 防火牆可能彈出提示 → 選擇「允許存取」（私人網路）

**預設帳號密碼：**

| 角色 | 預設密碼 | 說明 |
|------|----------|------|
| 管理員 | `admin` | 首次登入後建議立即修改 |
| 員工 | `1234` | 員工可自行修改 |

### 2. 即時視訊打卡主程式

```powershell
python main.py
```

- 會開啟 OpenCV 視窗顯示攝影機畫面
- 按 **`q`** 鍵退出
- 如果畫面全黑 → 檢查 Windows 相機權限（見下方注意事項）

### 3. FastAPI 伺服器（ERP 串接用）

```powershell
python -m uvicorn src.api_server:app --reload
```

- API 文件：`http://localhost:8000/docs`

---

## 五、⚠️ Windows 專屬注意事項

### 1. 字型路徑差異

`main.py` 預設載入 macOS 字型路徑，在 Windows 上會 fallback 到預設字型（可能導致中文顯示異常）。

**修改方式**：編輯 `main.py` 第 108 行：

```python
# 原碼（macOS）
font_path = "/System/Library/Fonts/STHeiti Medium.ttc"

# 改為 Windows 路徑
import os
if os.name == 'nt':  # Windows
    font_path = "C:/Windows/Fonts/msjh.ttc"  # 微軟正黑體
else:  # macOS
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
```

如果 `msjh.ttc` 不存在，也可以嘗試：
- `C:/Windows/Fonts/msjhl.ttc`（微軟正黑體 Light）
- `C:/Windows/Fonts/simsun.ttc`（宋體）

### 2. 相機權限

Windows 10/11 可能阻擋 Python 存取攝影機：

1. **設定 → 隱私權與安全性 → 相機**
2. 開啟 **「允許應用程式存取您的相機」**
3. 確保 **「允許桌面應用程式存取相機」** 也已開啟

如果 `main.py` 啟動後畫面全黑：
- 檢查防毒軟體是否阻擋 Python
- Windows Defender：**設定 → 隱私權與安全性 → Windows 安全性 → 應用程式與瀏覽器控制 → 應用程式隔離**

### 3. PowerShell 執行政策

如果 `.\venv\Scripts\activate` 出現「無法載入檔案...因為這個系統上已停用指令碼執行」：

```powershell
# 以管理員身份執行 PowerShell，然後：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. ONNX Runtime / InsightFace 安裝問題

如果 `pip install insightface` 回報編譯錯誤：

```powershell
# 方案：先安裝預編譯的 onnxruntime，再安裝 insightface
pip install onnxruntime  # CPU 版本
# 或
pip install onnxruntime-gpu  # GPU 版本
pip install insightface --no-deps
pip install protobuf numpy opencv-python
```

### 5. 路徑注意事項

- **避免在路徑中使用空白或中文目錄名稱**
- 例如：`C:\Projects\attendance-system` ✅
- 不要用：`C:\我的專案\attendance system` ❌
- PowerShell 中使用 `.\` 而非 `/` 作為相對路徑前綴

### 6. 虛擬環境每次都要重新啟動

關閉 PowerShell 後虛擬環境會失效，下次使用前需重新執行：

```powershell
cd C:\你的路徑\attendance-system
.\venv\Scripts\activate
```

### 7. GPU 加速（可選，僅限 NVIDIA）

如需 GPU 加速，修改 `src/face_recognizer.py` 中的 provider 設定：

```python
self.detector.prepare(ctx_id=0, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
```

確認已安裝 `onnxruntime-gpu`：
```powershell
pip install onnxruntime-gpu
```

### 8. Streamlit 防火牆提示

首次執行 `streamlit run` 時，Windows 防火牆可能彈出網路存取提示：
- 選擇 **「允許存取」**
- 勾選「私人網路」即可，不需要勾選「公用網路」

---

## 六、常見問題排解

| 問題 | 解決方案 |
|------|----------|
| `python` 指令找不到 | 安裝時未勾選「Add Python to PATH」，重新安裝或手動加入環境變數 |
| `pip install` 編譯失敗 | 安裝 Visual C++ Build Tools（見前置需求 #3） |
| 相機畫面全黑 | 檢查 Windows 相機權限設定，或嘗試防毒軟體白名單 |
| Streamlit 網頁打不開 | 檢查防火牆設定，或手動打開瀏覽器訪問 `http://localhost:8501` |
| 中文顯示亂碼 | 修改 `main.py` 字型路徑為 Windows 字型（見注意事項 #1） |
| `.\venv\Scripts\activate` 被擋 | 修改 PowerShell 執行政策（見注意事項 #3） |
| `main.py` 按 q 無效 | 確認終端機視窗是前景視窗，焦點在終端機上 |

---

## 七、系統架構

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
                                           ┌──────▼───────┐
                                           │  FaceDatabase │
                                           │  (SQLite)     │
                                           └──────┬───────┘
                                                  │
                                           ┌──────▼───────┐
                                           │ AttendanceLog│
                                           │  (SQLite)    │
                                           └──────────────┘
```

## 八、技術堆疊

| 層級 | 技術 |
|------|------|
| 偵測 | Ultralytics YOLOv8 + Supervision (BYTETrack) |
| 辨識 | InsightFace ArcFace (buffalo_l) |
| 活體檢測 | Mini-FASNet (ONNX) |
| 儲存 | SQLite（人臉資料、打卡記錄、例外單據） |
| UI | Streamlit（中英雙語儀表板） |
| API | FastAPI + Uvicorn（ERP 串接） |
| 視訊 | OpenCV + Pillow（中文字型渲染） |
| 日誌 | Loguru |

---

*文件由 Hermes (小愛) 於 2026-05-18 製作，基於實際安裝測試驗證。*

# Spec: attendance-system × ERP_V4 整合

> Phase: 4-HR (考勤薪資連動)
> Date: 2026-05-18
> Author: 小愛 (Hermes)
> Status: Draft → Review

---

## 0. 技術約束與已知陷阱（Shift-Left 防呆清單）

> ⚠️ 此段落為每次 AI 實作前必讀。

1. ⚠️ **員工名稱對照**：attendance-system 用 `name`（如 "Bruce"），ERP_V4 用 `employee_code`（如 "EMP-20260514-000001"）。必須建立對照表，不能假設 name = code。
2. ⚠️ **資料來源單一**：attendance-system 是打卡資料來源（Source of Truth），ERP_V4 是消費者。ERP_V4 不應有自己的打卡輸入 UI。
3. ⚠️ **時間格式差異**：attendance-system 存 ISO 字串（`2026-05-18T08:30:00.123456`），ERP_V4 存 Date + Time 欄位。轉換時需注意時區。
4. ⚠️ **ERP_V4 使用 SQLite（開發）/ PostgreSQL（生產）**：sync service 必須同時相容兩種 DB。
5. ⚠️ **ERP_V4 前端使用 i18n（zh-TW / vi-VN，無英文）**：所有新增的 UI 字串必須走 i18n。
6. ⚠️ **FSD 架構**：ERP_V4 後端遵循 Feature-Sliced Design，HR 模組位於 `backend/app/modules/hr/`。
7. ⚠️ **禁止裸 `except Exception`**：sync 邏輯需明確處理連線失敗、超時、資料不一致等情境。
8. ⚠️ **Pydantic v2**：ERP_V4 使用 Pydantic v2，response 欄位需用 `model_dump()` 而非 `.dict()`。
9. ⚠️ **考勤狀態 ENUM**：ERP_V4 使用 CHECK('normal','late','absent','leave')，attendance-system 使用 GuardStatus enum（NORMAL/ABNORMAL/EXEMPTED/LUNCH/LATE/EARLY_LEAVE），需要對映。
10. ⚠️ **不修改 attendance-system 核心邏輯**：只在 attendance-system 加一個 sync webhook 或 API endpoint，不更動其打卡、辨識、活體檢測等核心流程。

---

## 1. 概述

將 **attendance-system**（AI 人臉打卡）與 **ERP_V4**（企業資源規劃）的 HR 模組串接，實現：

1. **自動同步打卡記錄**：ERP_V4 定期或即時從 attendance-system 拉取打卡資料，寫入考勤表
2. **員工資料同步**：attendance-system 註冊員工時，自動在 ERP_V4 建立對應員工記錄
3. **考勤狀態轉換**：attendance-system 的 Guard Mode 狀態（遲到/早退/請假）轉換為 ERP_V4 考勤狀態
4. **薪資連動**：同步後的考勤資料自動流入薪資計算（遲到扣款、工時統計、缺勤判斷）

---

## 2. 系統架構

```
┌─────────────────────────────────┐      ┌──────────────────────────────┐
│     attendance-system           │      │       ERP_V4                 │
│  (AI Face Attendance)           │      │  (Enterprise Resource Plan)  │
│                                 │      │                              │
│  ┌─────────────┐                │      │  ┌────────────────────────┐  │
│  │ YOLOv8 +    │                │      │  │   Employee DB          │  │
│  │ InsightFace │                │      │  │   (employee_code ↔     │  │
│  └──────┬──────┘                │      │  │    att_system_name)    │  │
│         │                       │      │  └──────────┬─────────────┘  │
│  ┌──────▼──────┐                │      │             │                │
│  │ Attendance  │───────┐        │      │  ┌──────────▼─────────────┐  │
│  │ Logger      │       │ GET    │      │  │   Attendance Sync      │  │
│  │ (SQLite)    │       │ /api/  │      │  │   Service              │  │
│  └─────────────┘       │ v1/    │      │   (Periodic + On-demand)  │  │
│                         │ atten  │      └──────────┬─────────────┘  │
│  ┌─────────────┐       │ dance/ │                 │                │
│  │ Guard Mode  │       │ history│      ┌──────────▼─────────────┐  │
│  │ + Exceptions│       └────────┘      │   Attendance DB        │  │
│  └─────────────┘                       │   (check_in/out, hours) │  │
│                                         └──────────┬─────────────┘  │
│  ┌─────────────┐                                   │                │
│  │ Employee    │───────┐       POST                 │                │
│  │ Registration│       │────── /api/hr/employees    │                │
│  │ Webhook     │───────┘                            │                │
│  └─────────────┘                       ┌────────────▼─────────────┐  │
│                                         │   Payroll Service        │  │
│                                         │   (連動考勤 + 計件獎金)   │  │
│                                         └──────────────────────────┘  │
└─────────────────────────────────┘      └──────────────────────────────┘
```

**資料流向**：
- attendance-system → ERP_V4：打卡記錄、員工註冊、例外單據
- ERP_V4 → attendance-system：無（單向資料流）

---

## 3. 員工對照表 (Employee Mapping)

### 3.1 對照表設計

在 ERP_V4 的 `employees` 表新增欄位：

| 欄位 | 類型 | 約束 | 說明 |
|------|------|------|------|
| `att_system_name` | string(128) | UNIQUE, NULL | attendance-system 註冊的員工名稱（用於 API 查詢） |
| `att_system_id` | string(64) | NULL, UNIQUE | attendance-system 的員工 ID（如 EMP001） |

> 如果 `att_system_name` 為 NULL，表示該員工不使用 AI 人臉打卡。

### 3.2 員工註冊同步

**流程**：
1. 管理員在 attendance-system Streamlit UI 註冊員工（name: "張三", id: "EMP003"）
2. attendance-system 呼叫 ERP_V4 API 建立/更新員工
3. ERP_V4 回傳 `employee_code`，attendance-system 儲存對應關係

**新增 API（ERP_V4）**：

```
POST /api/hr/employees/external
Content-Type: application/json

{
    "att_system_name": "張三",
    "att_system_id": "EMP003",
    "name": "張三",
    "department": "生產部",
    "position": "作業員",
    "base_salary": 35000,
    "hire_date": "2026-05-18"
}
```

**Response**：
```json
{
    "employee_code": "EMP-20260518-000003",
    "id": 3,
    "name": "張三",
    "att_system_name": "張三",
    "att_system_id": "EMP003",
    "message": "員工已建立"
}
```

> 如果 `att_system_name` 已存在，則更新而非建立（idempotent）。

---

## 4. 打卡記錄同步 (Attendance Sync)

### 4.1 資料格式對映

| attendance-system | ERP_V4 | 轉換規則 |
|---|---|---|
| `employee` (name) | `employee_id` (FK) | 透過 `att_system_name` 查找 |
| `event_type: "checkin"` | `check_in` (Time) | 取當天最早的 checkin timestamp |
| `event_type: "checkout"` | `check_out` (Time) | 取當天最晚的 checkout timestamp |
| — | `work_hours` (Decimal) | `(check_out - check_in) - 1h 午休`，小於 0 則為 0 |
| `status: NORMAL` | `status: "normal"` | 直接對映 |
| GuardStatus.LATE | `status: "late"` | checkin > 09:00 + grace_period |
| GuardStatus.EXEMPTED | `status: "leave"` | 有請假/公出單據 |
| GuardStatus.LUNCH | `status: "normal"` | 午休時段，不算異常 |
| GuardStatus.EARLY_LEAVE | `status: "late"` | 共用 status，可加 notes 註記 |
| 無任何記錄 | `status: "absent"` | 當天無打卡記錄 |

### 4.2 Sync API（attendance-system 端擴充）

**新增 API endpoint**：

```
GET /api/v1/attendance/sync?since=2026-05-01&until=2026-05-31
```

**Response**：
```json
{
    "period": { "start": "2026-05-01", "end": "2026-05-31" },
    "records": [
        {
            "employee": "張三",
            "employee_id": "EMP003",
            "date": "2026-05-18",
            "events": [
                { "type": "checkin", "timestamp": "2026-05-18T08:45:00", "confidence": 0.6 },
                { "type": "checkout", "timestamp": "2026-05-18T17:30:00", "confidence": 0.6 }
            ],
            "guard_status": "LATE",
            "guard_message": "遲到 15 分鐘"
        }
    ],
    "exceptions": [
        {
            "employee": "李四",
            "type": "leave",
            "start_date": "2026-05-20",
            "end_date": "2026-05-22",
            "reason": "事假",
            "status": "approved"
        }
    ]
}
```

### 4.3 Sync Service（ERP_V4 端）

**排程同步**（推薦每小時執行一次）：

```python
# backend/app/modules/hr/services/attendance_sync.py

class AttendanceSyncService:
    """Synchronize attendance records from attendance-system to ERP_V4."""
    
    ATTENDANCE_SYSTEM_API = "http://localhost:8000"  # configurable
    
    def sync_period(self, start_date: date, end_date: date) -> dict:
        """Pull records from attendance-system and write to ERP_V4."""
        # 1. Fetch from attendance-system API
        response = requests.get(
            f"{self.ATTENDANCE_SYSTEM_API}/api/v1/attendance/sync",
            params={"since": start_date.isoformat(), "until": end_date.isoformat()},
            timeout=30
        )
        data = response.json()
        
        # 2. Map employee names to ERP employee IDs
        # 3. Transform checkin/checkout events into daily records
        # 4. Upsert into ERP_V4 attendance table (idempotent)
        # 5. Return summary
        pass
```

**手動觸發 API**：

```
POST /api/hr/attendance/sync
Content-Type: application/json

{
    "start_date": "2026-05-01",
    "end_date": "2026-05-31"
}
```

**Response**：
```json
{
    "synced": 15,
    "updated": 3,
    "skipped": 2,
    "errors": 0,
    "details": [...]
}
```

### 4.4 轉換邏輯細節

```python
def transform_daily_record(att_record: dict, employee_id: int) -> AttendanceCreate:
    """Transform attendance-system daily record into ERP_V4 format."""
    
    events = sorted(att_record["events"], key=lambda e: e["timestamp"])
    
    checkin_time = None
    checkout_time = None
    
    for event in events:
        ts = datetime.fromisoformat(event["timestamp"])
        if event["type"] == "checkin" and checkin_time is None:
            checkin_time = ts.time()
        elif event["type"] == "checkout":
            checkout_time = ts.time()  # Keep latest checkout
    
    # Calculate work hours
    work_hours = None
    if checkin_time and checkout_time:
        delta = datetime.combine(date.today(), checkout_time) - \
                datetime.combine(date.today(), checkin_time)
        total_hours = delta.total_seconds() / 3600
        # Subtract 1 hour lunch break if worked > 6 hours
        lunch_deduct = 1.0 if total_hours > 6 else 0
        work_hours = max(0, round(total_hours - lunch_deduct, 2))
    
    # Map status
    status_map = {
        "NORMAL": "normal",
        "LATE": "late",
        "EARLY_LEAVE": "late",
        "EXEMPTED": "leave",
        "LUNCH": "normal",
        "ABNORMAL": "absent",
    }
    status = status_map.get(att_record.get("guard_status", "NORMAL"), "normal")
    
    return AttendanceCreate(
        employee_id=employee_id,
        date=att_record["date"],
        check_in=checkin_time,
        check_out=checkout_time,
        work_hours=work_hours,
        status=status,
    )
```

---

## 5. 考勤狀態與薪資連動

### 5.1 考勤狀態影響薪資計算

| 考勤狀態 | 薪資影響 |
|---|---|
| `normal` | 無扣款，正常計薪 |
| `late` | 遲到扣款 = `base_salary / 22 / 8 * 遲到時數 * 扣款倍率` |
| `absent` | 缺勤扣款 = `base_salary / 22 * 缺勤天數` |
| `leave` | 有薪假不扣款，無薪假按比例扣款（需區假別） |

### 5.2 薪資計算連動考勤

```python
def calculate_payroll(employee_id: int, period_start: date, period_end: date) -> PayrollCreate:
    """Calculate payroll with attendance-based deductions."""
    
    employee = get_employee(employee_id)
    
    # Base salary (pro-rated for partial month)
    base_salary = employee.base_salary
    
    # Attendance deductions
    attendance_records = get_attendance_in_period(employee_id, period_start, period_end)
    
    late_deduction = 0
    absent_deduction = 0
    for record in attendance_records:
        if record.status == "late":
            # Late deduction: (base_salary / 22 days / 8 hours) * late_hours * 1.0
            daily_rate = base_salary / 22
            hourly_rate = daily_rate / 8
            late_hours = calculate_late_hours(record.check_in)
            late_deduction += hourly_rate * late_hours
        elif record.status == "absent":
            absent_deduction += base_salary / 22
    
    deductions = late_deduction + absent_deduction
    
    # Piece bonus (from Production module)
    piece_bonus = calculate_piece_bonus(employee_id, period_start, period_end)
    
    # Overtime
    overtime_pay = calculate_overtime(employee_id, period_start, period_end)
    
    total = base_salary + piece_bonus + overtime_pay - deductions
    
    return PayrollCreate(
        employee_id=employee_id,
        period_start=period_start,
        period_end=period_end,
        base_salary=base_salary,
        piece_bonus=piece_bonus,
        overtime_pay=overtime_pay,
        dedutions=deductions,
        total_amount=total,
    )
```

---

## 6. 需要實作的 API 端點總覽

### 6.1 attendance-system 端新增

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/v1/attendance/sync` | 期間打卡記錄（供 ERP_V4 拉取） |
| POST | `/api/v1/webhook/employee-registered` | 員工註冊通知（可選 push 模式） |

### 6.2 ERP_V4 端新增

| Method | Path | 說明 |
|--------|------|------|
| POST | `/api/hr/employees/external` | 建立/更新外部系統員工對照 |
| POST | `/api/hr/attendance/sync` | 手動觸發考勤同步 |
| GET | `/api/hr/attendance/sync/status` | 查看最近一次同步狀態 |

### 6.3 ERP_V4 端修改

| Method | Path | 修改內容 |
|--------|------|------|
| POST | `/api/hr/employees` | 新增 `att_system_name`、`att_system_id` 欄位 |
| GET | `/api/hr/attendance` | 回傳資料加入同步來源標記 |
| POST | `/api/hr/payroll/calculate` | 納入考勤扣款邏輯 |

---

## 7. 前端頁面變更

### 7.1 EmployeeForm 修改

- 新增欄位：`att_system_name`（可選）、`att_system_id`（可選）
- 標籤：「AI 打卡名稱」、「AI 打卡編號」
- 提示文字：「若使用人臉打卡系統，請填入對應名稱」

### 7.2 AttendanceList 修改

- 打卡記錄加入「來源」欄位（手動 / AI 人臉）
- 同步按鈕：「🔄 從人臉打卡系統同步」
- 同步狀態提示：「上次同步：2026-05-18 14:30，同步 15 筆」

### 7.3 PayrollList 修改

- 薪資明細加入「考勤扣款」區塊（遲到扣款、缺勤扣款）
-  Tooltip 說明扣款計算方式

---

## 8. 配置設定

### 8.1 ERP_V4 config.yaml 新增

```yaml
attendance_sync:
  enabled: true
  attendance_system_url: "http://localhost:8000"
  sync_interval_minutes: 60  # 每小時同步一次
  auto_create_employees: true  # 自動建立不存在的員工
  default_department: "生產部"
  default_position: "作業員"
  default_base_salary: 35000
```

### 8.2 attendance-system config.yaml 新增（可選）

```yaml
webhook:
  enabled: true
  erp_url: "http://localhost:5000/api/hr/employees/external"
```

---

## 9. 錯誤處理

| 情境 | 處理方式 |
|------|------|
| attendance-system API 離線 | 記錄錯誤日誌，下次同步時補抓（since 使用上次成功時間） |
| 員工名稱找不到對應 | 若 `auto_create_employees=true` 則自動建立，否則跳過並記錄警告 |
| 重複打卡記錄 | 使用 `employee_id + date` 作為 unique key，存在則 UPDATE |
| 時間格式錯誤 | 記錄原始資料到 error_log 表，跳過該筆 |
| 同步中途斷線 | 事務回滾，確保不會只寫入部分資料 |

---

## 10. 驗證標準

### 10.1 功能驗證

1. ✅ 在 attendance-system 註冊員工 → ERP_V4 自動出現對應員工記錄
2. ✅ 人臉打卡 checkin → 1 小時內同步到 ERP_V4，check_in 欄位正確
3. ✅ 人臉打卡 checkout → ERP_V4 check_out 欄位更新，work_hours 正確計算
4. ✅ 遲到打卡（09:16 後）→ ERP_V4 status = "late"
5. ✅ 請假期間打卡 → ERP_V4 status = "leave"（例外單據優先）
6. ✅ 全天無打卡 → ERP_V4 status = "absent"
7. ✅ 薪資計算納入考勤扣款
8. ✅ 手動觸發同步 API 正常工作

### 10.2 效能驗證

- 單次同步 100 筆記錄 < 5 秒
- 同步失敗自動重試 3 次

---

## 11. 實作順序（Serial Dispatch）

> 按 SDD 規定，依序派遣，每批間隔 5-10 分鐘。

1. **第一批**：ERP_V4 employees 表加 `att_system_name` + `att_system_id` 欄位（Alembic migration + model + schema）
2. **第二批**：ERP_V4 `POST /api/hr/employees/external` API + service
3. **第三批**：attendance-system `GET /api/v1/attendance/sync` API
4. **第四批**：ERP_V4 AttendanceSyncService + `POST /api/hr/attendance/sync`
5. **第五批**：ERP_V4 薪資計算納入考勤扣款邏輯
6. **第六批**：前端頁面修改（EmployeeForm、AttendanceList、PayrollList）

---

## 12. MVP 範圍控制

**MVP 先做**：
- 員工對照表 + 手動同步 + 基本考勤狀態轉換
- 薪資計算加入遲到扣款

**延後到 v3**：
- Webhook 自動推送（改為排程拉取即可）
- 前端 UI 美化
- 詳細的假別分類（有薪假/無薪假）
- 加班費自動計算

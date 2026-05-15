# Phase 2: Guard Mode & Access Control Implementation Plan

## Goal
升級打卡系統為企業級門禁管制工具，支援「上下班時間判斷」、「異常狀態警示」、「請假/外出單豁免」，並保留可開關的模組化設計。

## Scope
1.  **Config**: 新增 Guard Mode 開關與上下班時間設定。
2.  **Database**: 新增「例外申請 (Exceptions)」資料表 (請假/公出)。
3.  **Logic**: 建立狀態判斷引擎 (Status Engine)，根據時間與例外申請判定狀態。
4.  **UI (Video)**: 根據狀態顯示不同視覺提示 (正常/異常/豁免)。
5.  **UI (Streamlit)**: 新增「單據管理 (Exception Management)」頁面。
6.  **API**: 更新 API 支援查詢例外申請與人員進出狀態。

## Tech Stack Updates
- **Database**: SQLite (New table: `exceptions`)
- **Config**: `yaml` (New section: `guard_mode`)
- **UI**: Streamlit (New page/tab for Exception Management)
- **Main**: `main.py` (Logic update)

## Tasks

### 1. Configuration & Database Schema
- Update `config.yaml`: Add `guard_mode.enabled`, `guard_mode.work_hours`, `guard_mode.grace_period`.
- Update `src/face_db.py` or create `src/exception_manager.py`: Add `exceptions` table CRUD.
- Table structure: `id`, `employee_id`, `type` (leave/out), `start_time`, `end_time`, `status`, `reason`.

### 2. Status Engine (Core Logic)
- Create `src/guard_engine.py`:
    - `get_status(name, current_time)`:
        - Check if currently in an approved exception. -> Return `Exempted` (Green/Blue).
        - Check current time vs `work_hours`.
            - Before start + grace -> `Late`.
            - After end -> `Early Leave` (if before leaving limit) or `Overtime` (optional).
            - Within hours -> `Normal` (Green).
        - Return status object with `color` and `message`.

### 3. Main Pipeline Update
- Modify `main.py` loop:
    - Load `GuardEngine`.
    - When face detected: Call `get_status()`.
    - Overlay logic:
        - `Normal`: "打卡成功 - 正常進出" (Green)
        - `Exempted`: "已核准 - 公出/請假中" (Blue)
        - `Late/Abnormal`: "異常進出 - 請聯繫警衛" (Red)
        - `Cooldown`: Keep existing logic but integrate status colors.

### 4. Streamlit UI Updates
- Add "Guard Mode" tab in `streamlit_app.py`.
- Form: Select Employee -> Select Type (Leave/Business) -> Set Time Range -> Submit.
- Table: Show active exceptions.

### 5. API Server Updates
- Add `GET /api/v1/guard/status/{employee_id}`: Returns current access status.
- Add `GET /api/v1/exceptions`: List active exceptions.

## Verification
- **Test 1**: Enable Guard Mode, set work hours 09:00-18:00. Test at 08:50 -> Should show Red/Late.
- **Test 2**: Add Leave Request for 08:50. Test again -> Should show Blue/Exempted.
- **Test 3**: Disable Guard Mode in config. System should revert to standard logging.

## Timeline
- Estimated effort: ~2-3 hours.
- Priority: High (User requested).

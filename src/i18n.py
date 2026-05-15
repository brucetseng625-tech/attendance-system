"""Internationalization (i18n) module for the Attendance System UI."""

# Translation dictionary
TRANSLATIONS = {
    # Sidebar & Nav
    "nav_dashboard": {"en": "Dashboard", "zh": "數據看板"},
    "nav_register": {"en": "Register Employee", "zh": "員工註冊"},
    "nav_reports": {"en": "Reports", "zh": "報表查詢"},
    "nav_camera": {"en": "Live Camera", "zh": "視訊預覽"},
    "nav_guard": {"en": "🛡️ Guard Mode", "zh": "🛡️ 門警模式"},
    
    # Sidebar Elements
    "sidebar_title": {"en": "AI Attendance", "zh": "AI 打卡系統"},
    "sidebar_caption": {"en": "v2.0.0 | Powered by InsightFace", "zh": "v2.0.0 | 基於 InsightFace"},
    "nav_label": {"en": "Navigation", "zh": "功能導覽"},
    "lang_label": {"en": "Language", "zh": "語言"},

    # Dashboard
    "dash_title": {"en": "📊 Attendance Dashboard", "zh": "📊 打卡數據看板"},
    "dash_date": {"en": "Date", "zh": "日期"},
    "dash_total_checkins": {"en": "Total Check-ins", "zh": "總打卡數"},
    "dash_total_checkouts": {"en": "Total Check-outs", "zh": "總登出數"},
    "dash_unique_today": {"en": "Unique Employees Today", "zh": "今日出勤人數"},
    "dash_registered_emp": {"en": "👥 Registered Employees", "zh": "👥 已註冊員工"},
    "dash_total_registered": {"en": "Total registered", "zh": "總計註冊"},
    "dash_no_emp_registered": {"en": "No employees registered yet. Go to Register Employee to add someone.", "zh": "尚未註冊員工。請前往「員工註冊」頁面新增。"},
    "dash_today_records": {"en": "🕒 Today's Records", "zh": "🕒 今日記錄"},
    "dash_no_records_today": {"en": "No attendance records for today yet.", "zh": "今日尚無打卡記錄。"},
    "col_employee": {"en": "Employee", "zh": "員工"},
    "col_event": {"en": "Event", "zh": "事件"},
    "col_time": {"en": "Time", "zh": "時間"},
    "col_confidence": {"en": "Confidence", "zh": "信心度"},

    # Registration
    "reg_title": {"en": "🆔 Employee Registration", "zh": "🆔 員工註冊"},
    "reg_caption": {"en": "Add a new employee to the face database.", "zh": "將新員工加入人臉資料庫。"},
    "reg_name": {"en": "Employee Name", "zh": "員工姓名"},
    "reg_id": {"en": "Employee ID", "zh": "員工編號"},
    "reg_placeholder_name": {"en": "e.g. Bruce", "zh": "例如：Bruce"},
    "reg_placeholder_id": {"en": "e.g. EMP001", "zh": "例如：EMP001"},
    "reg_tab_upload": {"en": "Upload Photo", "zh": "上傳照片"},
    "reg_tab_camera": {"en": "Take Photo", "zh": "現場拍攝"},
    "reg_upload_label": {"en": "Upload a clear face photo", "zh": "上傳清晰的正面人臉照片"},
    "reg_btn_upload": {"en": "Register from Upload", "zh": "從上傳照片註冊"},
    "reg_camera_caption": {"en": "Ensure good lighting and remove masks/sunglasses.", "zh": "請確保光線充足，並取下口罩/眼鏡。"},
    "reg_btn_camera": {"en": "Register from Camera", "zh": "從視訊註冊"},
    "reg_error_fields": {"en": "Please provide both name and employee ID.", "zh": "請填寫員工姓名與編號。"},
    "reg_error_face": {"en": "Could not detect exactly one face in the image. Please upload a clear photo with a single face.", "zh": "無法偵測到單一清晰人臉。請上傳一張只有單一正面的清晰照片。"},
    "reg_success": {"en": "registered successfully!", "zh": "註冊成功！"},

    # Reports
    "rep_title": {"en": "Attendance Reports", "zh": "打卡報表查詢"},
    "rep_no_records": {"en": "No attendance records found.", "zh": "查無打卡記錄。"},
    "rep_filters": {"en": "Filters", "zh": "篩選條件"},
    "rep_filter_emp": {"en": "Employee", "zh": "員工"},
    "rep_filter_event": {"en": "Event Type", "zh": "事件類型"},
    "rep_all": {"en": "All", "zh": "全部"},
    "rep_showing": {"en": "Showing", "zh": "顯示"},
    "rep_records": {"en": "records", "zh": "筆記錄"},
    "rep_export": {"en": "Export", "zh": "匯出"},
    "rep_btn_download": {"en": "Download CSV", "zh": "下載 CSV"},

    # Live Camera
    "cam_title": {"en": "Live Camera Preview", "zh": "即時視訊預覽"},
    "cam_info": {"en": "Use your webcam to preview the camera feed. For real-time attendance tracking, run `python main.py` from the project root.", "zh": "使用您的網路攝影機預覽畫面。若要執行即時打卡，請在專案目錄下執行 `python main.py`。"},
    "cam_source": {"en": "Camera source", "zh": "視訊來源"},
    "cam_snapshot": {"en": "Take a snapshot", "zh": "拍攝快照"},
    "cam_caption": {"en": "Camera preview", "zh": "視訊預覽"},
    "cam_detecting": {"en": "Detecting faces...", "zh": "正在偵測人臉..."},
    "cam_detected": {"en": "Detected", "zh": "偵測到"},
    "cam_face_s": {"en": "face(s)", "zh": "張人臉"},
    "cam_no_face": {"en": "No faces detected in the frame.", "zh": "畫面中未偵測到人臉。"},

    # Guard Mode
    "guard_title": {"en": "🛡️ Access Control & Exceptions", "zh": "🛡️ 門禁管制與例外管理"},
    "guard_caption": {"en": "Manage work hours, leave requests, and business trips.", "zh": "管理上下班時間、請假與公出差勤。"},
    "guard_status": {"en": "System Status", "zh": "系統狀態"},
    "guard_mode_on": {"en": "**Guard Mode ON**", "zh": "**門警模式：已開啟**"},
    "guard_mode_off": {"en": "**Standard Mode**", "zh": "**標準模式**"},
    "guard_work_hours": {"en": "Work Hours", "zh": "上下班時間"},
    "guard_grace": {"en": "Grace Period", "zh": "緩衝期"},
    "guard_info_toggle": {"en": "To toggle Guard Mode, edit `config.yaml` and restart the camera process.", "zh": "欲切換門警模式，請編輯 `config.yaml` 並重啟打卡程式。"},
    
    "guard_exc_title": {"en": "Employee Exceptions (Leave / Business)", "zh": "員工例外單據 (請假 / 公出)"},
    "guard_sel_emp": {"en": "Select Employee", "zh": "選擇員工"},
    "guard_type": {"en": "Type", "zh": "類型"},
    "guard_type_leave": {"en": "leave", "zh": "請假"},
    "guard_type_business": {"en": "business", "zh": "公出"},
    "guard_start": {"en": "Start Date", "zh": "開始日期"},
    "guard_end": {"en": "End Date", "zh": "結束日期"},
    "guard_reason": {"en": "Reason (Optional)", "zh": "事由 (選填)"},
    "guard_btn_submit": {"en": "Submit Exception", "zh": "提交例外單據"},
    "guard_err_emp": {"en": "Please select an employee.", "zh": "請選擇員工。"},
    "guard_success_exc": {"en": "Exception added for", "zh": "已成功為"},
    "guard_success_exc_to": {"en": "from", "zh": "建立例外期間："},
    
    "guard_exc_list": {"en": "Active & Pending Exceptions", "zh": "目前有效的例外單據"},
    "col_from": {"en": "From", "zh": "開始"},
    "col_to": {"en": "To", "zh": "結束"},
    "col_status": {"en": "Status", "zh": "狀態"},
    "col_reason": {"en": "Reason", "zh": "事由"},
    "guard_no_exc": {"en": "No exceptions currently recorded.", "zh": "目前尚無例外單據。"},
}

# Current language state (default to Traditional Chinese)
current_lang = "zh"

def set_language(lang: str):
    """Set the current language ('en' or 'zh')."""
    global current_lang
    if lang in ["en", "zh"]:
        current_lang = lang

def get(key: str) -> str:
    """Get translation for the given key."""
    if key not in TRANSLATIONS:
        return key
    return TRANSLATIONS[key].get(current_lang, key)

# Alias for convenience
_ = get

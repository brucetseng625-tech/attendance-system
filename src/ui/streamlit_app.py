"""Streamlit UI for the AI Face Attendance System.

Provides Role-Based Access: Admin vs Employee.
- Admin: Dashboard, Reports, Settings, Approvals.
- Employee: Request Portal, My History.
"""

import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st
import yaml

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_project_root, load_config
from src.face_db import FaceDatabase
from src.attendance_logger import AttendanceLogger
from src.face_recognizer import FaceRecognizer
from src.exception_manager import ExceptionManager
from src.user_manager import UserManager
import src.i18n as T

ROOT = get_project_root()

# Default Admin Password
ADMIN_PASSWORD = "admin"


def set_page_design():
    """Inject custom CSS for Linear-style Dark Mode design."""
    st.markdown(
        """
        <style>
        /* --- Global Theme --- */
        :root {
            --bg-color: #0f1115;
            --surface-color: #161a21;
            --surface-hover: #1c2128;
            --border-color: #2a2e37;
            --text-primary: #f0f0f5;
            --text-secondary: #8b949e;
            --accent-color: #5e6ad2;
            --accent-gradient: linear-gradient(135deg, #5e6ad2 0%, #8b5cf6 100%);
            --danger-color: #d73a49;
            --success-color: #2ea44f;
        }

        .stApp { background-color: var(--bg-color); color: var(--text-primary); }
        h1, h2, h3 { color: var(--text-primary) !important; font-weight: 600; }
        
        /* Sidebar */
        [data-testid="stSidebar"] { background-color: #0b0d10; border-right: 1px solid var(--border-color); }
        [data-testid="stSidebar"] .stRadio > label { color: var(--text-primary) !important; }
        
        /* Cards */
        .card {
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }

        /* Buttons */
        .stButton > button {
            background: var(--accent-gradient);
            color: white !important;
            border: none !important;
            border-radius: 6px;
            font-weight: 600;
        }
        
        /* Inputs */
        .stTextInput > div > div > input, .stSelectbox > div > div > select, .stTextArea > div > div > textarea {
            background-color: var(--surface-hover) !important;
            border: 1px solid var(--border-color) !important;
            color: var(--text-primary) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# CACHE RESOURCES
# =============================================================================
@st.cache_resource
def get_face_recognizer():
    config = load_config()
    return FaceRecognizer(model_name=config["face_recognition"]["model"])

@st.cache_resource
def get_face_database():
    return FaceDatabase(db_path=str(ROOT / "data" / "faces.db"))

@st.cache_resource
def get_attendance_logger():
    config = load_config()
    return AttendanceLogger(
        db_path=str(ROOT / config["attendance"]["database"]),
        cooldown_seconds=config["attendance"]["cooldown_seconds"]
    )

@st.cache_resource
def get_exception_manager():
    config = load_config()
    return ExceptionManager(db_path=str(ROOT / config["guard_mode"]["exception_db"]))


def format_timestamp(ts_str: str) -> str:
    if ts_str is None: return ""
    try: return datetime.fromisoformat(ts_str).strftime("%Y-%m-%d %H:%M:%S")
    except: return str(ts_str)


# =============================================================================
# PAGE: LOGIN
# =============================================================================
def page_login():
    # Center the login box
    st.markdown("""
    <style>
        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 80vh;
            flex-direction: column;
        }
        .login-box {
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 2rem;
            width: 100%;
            max-width: 500px;
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.image("https://img.icons8.com/ios-filled/50/8b5cf6/fingerprint.png", width=60)
        st.title(T._("login_title"))
        st.caption("AI Face Attendance System | v2.0")
        st.divider()

        tab_admin, tab_emp = st.tabs([T._("admin_login"), T._("employee_portal")])

        with tab_admin:
            pw = st.text_input(T._("password"), type="password", key="admin_pw_input", placeholder="Password")
            if st.button(T._("btn_login"), type="primary", use_container_width=True):
                if pw == ADMIN_PASSWORD:
                    st.session_state.logged_in = True
                    st.session_state.role = "admin"
                    st.rerun()
                else:
                    st.error(T._("wrong_pw"))
        
        with tab_emp:
            # Fetch employee list for selection
            try:
                face_db = get_face_database()
                employees = face_db.get_all_employees()
                emp_names = [e["name"] for e in employees]
            except:
                emp_names = []

            if emp_names:
                selected_emp = st.selectbox("👤 選擇您的姓名", emp_names)
                pw = st.text_input(T._("emp_password"), type="password", key="emp_pw_input", placeholder="Enter password")
                
                if st.button(T._("btn_enter"), type="primary", use_container_width=True):
                    # Check password dynamically using hashed verification
                    user_mgr = UserManager()
                    if user_mgr.check_password(selected_emp, pw):
                        st.session_state.logged_in = True
                        st.session_state.role = "employee"
                        st.session_state.current_employee = selected_emp
                        st.rerun()
                    else:
                        st.error(T._("wrong_pw"))
            else:
                st.warning("No employees registered. Contact Admin.")
        
        # Language Switcher at bottom of Login
        st.divider()
        lang_opt = st.radio(
            T._("lang_label"), 
            ["繁體中文", "English"],
            horizontal=True,
            index=0 if st.session_state.language == "zh" else 1,
            key="lang_radio_login"
        )
        if (lang_opt == "English" and st.session_state.language != "en") or \
           (lang_opt == "繁體中文" and st.session_state.language != "zh"):
            st.session_state.language = "en" if lang_opt == "English" else "zh"
            T.set_language(st.session_state.language)
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# PAGE: ADMIN DASHBOARD
# =============================================================================
def render_admin_dashboard():
    st.title(T._("dash_title"))
    st.caption(f"{T._('dash_date')}: {datetime.now().strftime('%Y-%m-%d')}")
    
    att_logger = get_attendance_logger()
    face_db = get_face_database()
    records = att_logger.get_today_records()
    employees = face_db.get_all_employees()
    
    c1, c2, c3 = st.columns(3)
    with c1: 
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric(T._("dash_total_checkins"), len([r for r in records if r['event']=='checkin']))
        st.markdown('</div>', unsafe_allow_html=True)
    with c2: 
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric(T._("dash_unique_today"), len(set(r['employee'] for r in records)))
        st.markdown('</div>', unsafe_allow_html=True)
    with c3: 
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric(T._("dash_total_registered"), len(employees))
        st.markdown('</div>', unsafe_allow_html=True)

    st.subheader(T._("dash_today_records"))
    if records:
        df = pd.DataFrame(records)
        df["timestamp"] = df["timestamp"].apply(format_timestamp)
        df = df.rename(columns={"employee": T._("col_employee"), "event": T._("col_event"), "timestamp": T._("col_time")})
        st.dataframe(df, use_container_width=True)
    else:
        st.info(T._("dash_no_records_today"))


# =============================================================================
# PAGE: ADMIN REGISTER
# =============================================================================
def render_register():
    st.title(T._("reg_title"))
    st.markdown('<div class="card">', unsafe_allow_html=True)
    face_rec = get_face_recognizer()
    face_db = get_face_database()
    
    c1, c2 = st.columns(2)
    with c1: name = st.text_input(T._("reg_name"), placeholder="e.g. Bruce")
    with c2: emp_id = st.text_input(T._("reg_id"), placeholder="e.g. EMP001")
    
    if not name or not emp_id:
        st.warning(T._("reg_error_fields"))
        st.markdown('</div>', unsafe_allow_html=True)
        return

    tab_upload, tab_camera = st.tabs([T._("reg_tab_upload"), T._("reg_tab_camera")])

    with tab_upload:
        uploaded = st.file_uploader(T._("reg_upload_label"), type=["jpg", "png"])
        if uploaded:
            f_bytes = np.frombuffer(uploaded.read(), np.uint8)
            frame = cv2.imdecode(f_bytes, cv2.IMREAD_COLOR)
            st.image(frame, channels="BGR", caption="Preview")
            if st.button(T._("reg_btn_upload"), type="primary", use_container_width=True):
                emb = face_rec.register_from_frame(frame, name)
                if emb is None:
                    st.error(T._("reg_error_face"))
                else:
                    face_db.register(name, emp_id, emb)
                    st.success(T._("reg_success"))

    with tab_camera:
        st.caption(T._("reg_camera_caption"))
        camera_img = st.camera_input(T._("reg_tab_camera"))
        if camera_img:
            f_bytes = np.frombuffer(camera_img.read(), np.uint8)
            frame = cv2.imdecode(f_bytes, cv2.IMREAD_COLOR)
            frame = cv2.flip(frame, 1) # Non-mirror
            st.image(frame, channels="BGR", caption="Live Capture")
            if st.button(T._("reg_btn_camera"), type="primary", use_container_width=True):
                emb = face_rec.register_from_frame(frame, name)
                if emb is None:
                    st.error(T._("reg_error_face"))
                else:
                    face_db.register(name, emp_id, emb)
                    st.success(T._("reg_success"))
    
    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# PAGE: ADMIN REPORTS
# =============================================================================
def render_reports():
    st.title(T._("rep_title"))
    
    att_logger = get_attendance_logger()
    records = att_logger.get_all_records()
    
    if not records:
        st.info(T._("rep_no_records"))
        return

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"]) # Convert to datetime for filtering
    
    # --- Filters ---
    st.markdown('<div class="card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        # Date Filter
        min_date = df["timestamp"].min().date()
        max_date = df["timestamp"].max().date()
        date_range = st.date_input("📅 Date Range", value=(min_date, max_date))
    with c2:
        # Employee Filter
        employees = sorted(df["employee"].unique())
        selected_emp = st.selectbox("👤 Employee", ["All"] + employees)
    with c3:
        # Event Type Filter
        selected_event = st.selectbox("📝 Event Type", ["All", "checkin", "checkout"])
    st.markdown('</div>', unsafe_allow_html=True)

    # Apply Filters
    filtered_df = df.copy()
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df["timestamp"].dt.date >= start_date) & 
            (filtered_df["timestamp"].dt.date <= end_date)
        ]
    if selected_emp != "All":
        filtered_df = filtered_df[filtered_df["employee"] == selected_emp]
    if selected_event != "All":
        filtered_df = filtered_df[filtered_df["event"] == selected_event]

    # Display
    display_df = filtered_df.sort_values("timestamp", ascending=False)
    display_df["timestamp"] = display_df["timestamp"].apply(format_timestamp)
    display_df = display_df.rename(columns={"employee": T._("col_employee"), "event": T._("col_event"), "timestamp": T._("col_time")})
    
    st.dataframe(display_df, use_container_width=True)
    st.caption(f"Showing {len(display_df)} records")


# =============================================================================
# PAGE: SETTINGS (Admin Only)
# =============================================================================
def page_settings():
    st.title(T._("settings_title"))
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    config_path = ROOT / "config.yaml"
    config = load_config()
    guard = config.get("guard_mode", {})
    
    # 1. Guard Mode Toggle
    enabled = st.toggle(
        T._("settings_guard_toggle"), 
        value=guard.get("enabled", False)
    )
    
    # 2. Work Hours
    work_hours = guard.get("work_hours", {"start": "09:00", "end": "18:00"})
    c1, c2 = st.columns(2)
    with c1:
        start_val = datetime.strptime(work_hours["start"], "%H:%M").time()
        new_start = st.time_input(T._("settings_work_start"), value=start_val)
    with c2:
        end_val = datetime.strptime(work_hours["end"], "%H:%M").time()
        new_end = st.time_input(T._("settings_work_end"), value=end_val)
        
    # 3. Grace Period
    grace = st.number_input(T._("settings_grace"), value=guard.get("grace_period_minutes", 15))
    
    st.divider()
    
    # 4. Lunch Break Settings
    st.subheader("🍽️ Lunch Break Window")
    lunch_config = config.get("lunch_break", {"enabled": False, "start": "12:00", "end": "13:00"})
    lunch_enabled = st.toggle(
        "Enable Lunch Break", 
        value=lunch_config.get("enabled", False)
    )
    
    if lunch_enabled:
        l_c1, l_c2 = st.columns(2)
        with l_c1:
            lunch_start_val = datetime.strptime(lunch_config.get("start", "12:00"), "%H:%M").time()
            lunch_start = st.time_input("Start", value=lunch_start_val)
        with l_c2:
            lunch_end_val = datetime.strptime(lunch_config.get("end", "13:00"), "%H:%M").time()
            lunch_end = st.time_input("End", value=lunch_end_val)
    else:
        lunch_start = None
        lunch_end = None
    
    # Save Button
    if st.button(T._("btn_save_config"), type="primary", use_container_width=True):
        # Update dict
        config["guard_mode"]["enabled"] = enabled
        config["guard_mode"]["work_hours"] = {
            "start": new_start.strftime("%H:%M"),
            "end": new_end.strftime("%H:%M")
        }
        config["guard_mode"]["grace_period_minutes"] = int(grace)
        
        # Save Lunch Break config
        config["lunch_break"] = {
            "enabled": lunch_enabled,
            "start": lunch_start.strftime("%H:%M") if lunch_start else "12:00",
            "end": lunch_end.strftime("%H:%M") if lunch_end else "13:00"
        }
        
        # Write to YAML
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
        st.success(T._("msg_config_saved"))
        st.info("Please restart the `main.py` process for changes to take effect in the camera view.")

    st.markdown('</div>', unsafe_allow_html=True)

    # --- User Password Management ---
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("👥 Employee Password Management")
    
    face_db = get_face_database()
    employees = face_db.get_all_employees()
    emp_names = [e["name"] for e in employees]
    
    user_mgr = UserManager()
    
    if emp_names:
        c1, c2 = st.columns(2)
        with c1:
            target_emp = st.selectbox("Select Employee", emp_names)
        with c2:
            new_admin_pw = st.text_input("Set New Password", type="password")
            
        if st.button("Reset Password", type="primary", use_container_width=True):
            if new_admin_pw:
                user_mgr.set_password(target_emp, new_admin_pw)
                st.success(f"Password for '{target_emp}' has been reset.")
            else:
                st.error("Please enter a new password.")
    else:
        st.info("No employees registered yet.")
        
    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# PAGE: APPROVALS (Admin Only)
# =============================================================================
def page_approvals():
    st.title(T._("approval_title"))
    
    exc_mgr = get_exception_manager()
    pending = exc_mgr.get_pending_exceptions()
    
    if not pending:
        st.info(T._("no_pending"))
        return

    for req in pending:
        st.markdown(f'<div class="card">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"👤 {req['employee_id']}")
            st.write(f"**Type:** {req['type'].capitalize()}")
            st.write(f"**Time:** {req['start_time']} ➡️ {req['end_time']}")
            st.write(f"**Reason:** {req['reason'] or '-'}")
        
        with col2:
            st.write(f"**Status:** {req['status']}")
            if st.button(T._("action_approve"), key=f"approve_{req['id']}", type="primary", use_container_width=True):
                exc_mgr.update_status(req['id'], "approved")
                st.rerun()
            if st.button(T._("action_reject"), key=f"reject_{req['id']}", use_container_width=True):
                exc_mgr.update_status(req['id'], "rejected")
                st.rerun()
                
        st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# PAGE: EMPLOYEE PORTAL
# =============================================================================
def page_employee_portal():
    st.title(T._("portal_title"))
    # Removed card wrapper to fix black box artifact
    
    # Get current employee from session state
    if "current_employee" not in st.session_state:
        st.error("Session error. Please log in again.")
        return

    emp_name = st.session_state.current_employee
    
    # Tabs for Request vs Password Change
    tab_req, tab_pw = st.tabs([T._("portal_title"), T._("change_password")])

    with tab_req:
        st.subheader(f"👋 Hello, {emp_name}")
        
        # Config for hours
        config = load_config()
        guard_config = config.get("guard_mode", {})
        
        # Success Message Handling
        if st.session_state.get("request_submitted"):
            st.success("✅ 單據已送出！")
            st.session_state.request_submitted = False

        # Form with Date AND Time (Using Keys to enable clearing)
        c1, c2 = st.columns(2)
        with c1:
            exc_type = st.selectbox(T._("guard_type"), [T._("guard_type_leave"), T._("guard_type_business")], key="exc_type_key")
            start_dt = st.date_input(T._("guard_start"), key="start_dt_key")
            start_tm = st.time_input(T._("start_time"), value=datetime.strptime("09:00", "%H:%M").time(), key="start_tm_key")
        with c2:
            end_dt = st.date_input(T._("guard_end"), key="end_dt_key")
            end_tm = st.time_input(T._("end_time"), value=datetime.strptime("18:00", "%H:%M").time(), key="end_tm_key")
        
        reason = st.text_area(T._("guard_reason"), key="reason_key")
        
        if st.button(T._("btn_submit_request"), type="primary", use_container_width=True):
            type_key = "leave" if exc_type == T._("guard_type_leave") else "business"
            # Combine date and time explicitly
            start_str = f"{start_dt.strftime('%Y-%m-%d')} {start_tm.strftime('%H:%M')}:00"
            end_str = f"{end_dt.strftime('%Y-%m-%d')} {end_tm.strftime('%H:%M')}:00"
            
            exc_mgr = get_exception_manager()
            exc_mgr.add_exception(
                employee_id=emp_name,
                exception_type=type_key,
                start_time=start_str,
                end_time=end_str,
                reason=reason,
                status="pending"
            )
            st.session_state.request_submitted = True
            
            # Clear form keys to reset inputs
            for key in ["exc_type_key", "start_dt_key", "start_tm_key", "end_dt_key", "end_tm_key", "reason_key"]:
                if key in st.session_state:
                    del st.session_state[key]
                    
            st.rerun()
        
        # History
        st.subheader(T._("my_requests"))
        exc_mgr = get_exception_manager()
        history = exc_mgr.get_exceptions_by_employee(emp_name)
        
        if history:
            df = pd.DataFrame(history)
            df = df.rename(columns={
                "type": T._("guard_type"),
                "start_time": T._("col_from"),
                "end_time": T._("col_to"),
                "status": T._("col_status"),
                "reason": T._("col_reason")
            })
            st.dataframe(df, use_container_width=True)
        else:
            st.info(T._("history_empty"))

    with tab_pw:
        st.subheader(T._("change_password"))
        user_mgr = UserManager()
        
        new_pw = st.text_input(T._("new_password"), type="password", key="new_pw_emp")
        confirm_pw = st.text_input(T._("confirm_password"), type="password", key="confirm_pw_emp")
        
        if st.button(T._("btn_change_pw"), type="primary", use_container_width=True):
            if new_pw != confirm_pw:
                st.error(T._("pw_mismatch"))
            elif not new_pw:
                st.error(T._("wrong_pw")) # generic error for empty
            else:
                user_mgr.set_password(emp_name, new_pw)
                st.success(T._("pw_updated"))

# =============================================================================
# MAIN APP
# =============================================================================
def main():
    st.set_page_config(page_title="AI Attendance", page_icon="👤", layout="wide")
    set_page_design()
    
    # Initialize State
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "language" not in st.session_state:
        st.session_state.language = "zh"
        
    T.set_language(st.session_state.language)

    # LOGIN GATE
    if not st.session_state.logged_in:
        page_login()
        return

    # --- LOGGED IN ---
    
    # Language Selector in Sidebar
    with st.sidebar:
        lang_opt = st.radio(
            T._("lang_label"), 
            ["繁體中文", "English"],
            index=0 if st.session_state.language == "zh" else 1,
            key="lang_radio"
        )
        if (lang_opt == "English" and st.session_state.language != "en") or \
           (lang_opt == "繁體中文" and st.session_state.language != "zh"):
            st.session_state.language = "en" if lang_opt == "English" else "zh"
            T.set_language(st.session_state.language)
            st.rerun()

        st.divider()
        
        if st.button(T._("logout"), use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.rerun()

    # ROUTER
    if st.session_state.role == "admin":
        page = st.sidebar.radio(
            T._("nav_label"),
            [T._("nav_dashboard"), T._("nav_register"), T._("nav_reports"), T._("settings_title"), T._("approval_title")]
        )
        
        st.divider()
        
        if page == T._("nav_dashboard"):
            render_admin_dashboard()
        elif page == T._("nav_register"):
            render_register()
        elif page == T._("nav_reports"):
            render_reports()
        elif page == T._("settings_title"):
            page_settings()
        elif page == T._("approval_title"):
            page_approvals()

    else: # Employee
        # Employee Portal
        page_employee_portal()


if __name__ == "__main__":
    main()

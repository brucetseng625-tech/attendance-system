"""Streamlit UI for the AI Face Attendance System.

Provides 5 pages: Dashboard, Register Employee, Reports, Live Camera, Guard Mode.
Uses st.cache_resource for heavy model/database objects.
Designed with Linear-style Dark Mode theme and Bilingual (EN/ZH) support.
"""

import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_project_root, load_config
from src.face_db import FaceDatabase
from src.attendance_logger import AttendanceLogger
from src.face_recognizer import FaceRecognizer
from src.exception_manager import ExceptionManager
import src.i18n as T

ROOT = get_project_root()


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

        /* Apply dark theme to body and main containers */
        .stApp, .stApp > header, .stApp > .main .block-container {
            background-color: var(--bg-color);
            color: var(--text-primary);
        }

        h1, h2, h3 {
            color: var(--text-primary) !important;
            font-family: 'Inter', system-ui, sans-serif;
            font-weight: 600;
            letter-spacing: -0.02em;
        }

        p, label, span, div {
            color: var(--text-secondary) !important;
        }

        /* --- Sidebar --- */
        [data-testid="stSidebar"] {
            background-color: #0b0d10;
            border-right: 1px solid var(--border-color);
        }
        [data-testid="stSidebar"] .stRadio > label {
            font-weight: 500;
            color: var(--text-primary) !important;
        }
        [data-testid="stSidebar"] .stRadio > div {
            background-color: transparent !important;
        }
        .stRadio > div > label {
            padding: 0.5rem 0.8rem !important;
            margin-bottom: 0.2rem !important;
            border-radius: 6px;
            transition: all 0.2s;
        }
        .stRadio > div > label:hover {
            background-color: var(--surface-hover);
            color: var(--text-primary) !important;
        }
        .stRadio > div > [aria-checked="true"] {
            background-color: var(--accent-color) !important;
            color: #fff !important;
            font-weight: 600;
        }

        /* --- Cards / Containers --- */
        .card {
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1.2rem;
            margin-bottom: 1rem;
        }

        /* --- Inputs & Buttons --- */
        .stTextInput > div > div > input, .stSelectbox > div > div > select {
            background-color: var(--surface-hover) !important;
            border: 1px solid var(--border-color) !important;
            color: var(--text-primary) !important;
            border-radius: 6px;
        }
        .stTextInput > div > div > input:focus {
            border-color: var(--accent-color) !important;
            box-shadow: 0 0 0 2px rgba(94, 106, 210, 0.2);
        }
        
        .stButton > button {
            background: var(--accent-gradient);
            color: white !important;
            border: none !important;
            border-radius: 6px;
            font-weight: 600;
            padding: 0.5rem 1rem;
            transition: transform 0.1s, box-shadow 0.2s;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(94, 106, 210, 0.3);
        }
        .stButton > button[kind="secondary"] {
            background: var(--surface-hover) !important;
            border: 1px solid var(--border-color) !important;
            color: var(--text-secondary) !important;
        }

        /* --- Metrics & Dataframes --- */
        [data-testid="stMetricValue"] {
            color: var(--text-primary) !important;
            font-size: 2rem !important;
        }
        [data-testid="stMetricLabel"] {
            color: var(--text-secondary) !important;
        }
        .stDataFrame {
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
        }
        table.dataframe {
            color: var(--text-primary) !important;
        }
        
        /* --- Tabs --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 40px;
            white-space: pre-wrap;
            background-color: var(--surface-color);
            border-radius: 4px 4px 0 0;
            border: 1px solid var(--border-color);
            padding: 0.5rem 1rem;
            color: var(--text-secondary);
        }
        .stTabs [aria-selected="true"] {
            background-color: var(--accent-color) !important;
            color: #fff !important;
            border: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource
def get_face_recognizer():
    """Load and cache the InsightFace recognition model."""
    config = load_config()
    model_name = config["face_recognition"]["model"]
    return FaceRecognizer(model_name=model_name)


@st.cache_resource
def get_face_database():
    """Load and cache the employee face database."""
    db_path = str(ROOT / "data" / "faces.db")
    return FaceDatabase(db_path=db_path)


@st.cache_resource
def get_attendance_logger():
    """Load and cache the attendance logger."""
    config = load_config()
    db_path = str(ROOT / config["attendance"]["database"])
    cooldown = config["attendance"]["cooldown_seconds"]
    return AttendanceLogger(db_path=db_path, cooldown_seconds=cooldown)


def format_timestamp(ts_str: str) -> str:
    """Format an ISO timestamp string for display."""
    if ts_str is None:
        return ""
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return str(ts_str)


def page_dashboard():
    """Dashboard: today's attendance records + summary statistics."""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title(T._("dash_title"))
    st.caption(f"{T._('dash_date')}: {datetime.now().strftime('%Y-%m-%d')}")
    st.markdown('</div>', unsafe_allow_html=True)

    att_logger = get_attendance_logger()
    face_db = get_face_database()
    records = att_logger.get_today_records()
    employees = face_db.get_all_employees()

    # Metrics Row
    checkins = [r for r in records if r["event"] == "checkin"]
    checkouts = [r for r in records if r["event"] == "checkout"]
    unique_today = set(r["employee"] for r in records)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric(T._("dash_total_checkins"), len(checkins))
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric(T._("dash_total_checkouts"), len(checkouts))
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.metric(T._("dash_unique_today"), len(unique_today))
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader(T._("dash_registered_emp"))
    st.caption(f"{T._('dash_total_registered')}: {len(employees)}")
    if employees:
        emp_df = pd.DataFrame(employees)
        st.dataframe(emp_df, use_container_width=True)
    else:
        st.info(T._("dash_no_emp_registered"))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader(T._("dash_today_records"))
    if records:
        df = pd.DataFrame(records)
        df["timestamp"] = df["timestamp"].apply(format_timestamp)
        df = df.rename(columns={
            "employee": T._("col_employee"),
            "event": T._("col_event"),
            "timestamp": T._("col_time"),
            "confidence": T._("col_confidence"),
        })
        st.dataframe(df, use_container_width=True)
    else:
        st.info(T._("dash_no_records_today"))
    st.markdown('</div>', unsafe_allow_html=True)


def page_register():
    """Register Employee: upload photo or use camera, extract embedding, save."""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    st.title(T._("reg_title"))
    st.caption(T._("reg_caption"))
    
    face_rec = get_face_recognizer()
    face_db = get_face_database()

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input(T._("reg_name"), placeholder=T._("reg_placeholder_name"))
    with col2:
        employee_id = st.text_input(T._("reg_id"), placeholder=T._("reg_placeholder_id"))

    tab_upload, tab_camera = st.tabs([T._("reg_tab_upload"), T._("reg_tab_camera")])

    with tab_upload:
        uploaded_file = st.file_uploader(
            T._("reg_upload_label"),
            type=["jpg", "jpeg", "png"],
        )
        if uploaded_file is not None:
            file_bytes = np.frombuffer(uploaded_file.read(), np.uint8)
            frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if frame is not None:
                st.image(frame, channels="BGR", caption=T._("reg_tab_upload"))
                if st.button(T._("reg_btn_upload"), type="primary", use_container_width=True):
                    _process_registration(name, employee_id, frame, face_rec, face_db)

    with tab_camera:
        st.caption(T._("reg_camera_caption"))
        camera_img = st.camera_input(T._("reg_tab_camera"))
        if camera_img is not None:
            file_bytes = np.frombuffer(camera_img.read(), np.uint8)
            frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if frame is not None:
                frame = cv2.flip(frame, 1)
                st.image(frame, channels="BGR", caption=T._("reg_tab_camera"))
                if st.button(T._("reg_btn_camera"), type="primary", use_container_width=True):
                    _process_registration(name, employee_id, frame, face_rec, face_db)
    
    st.markdown('</div>', unsafe_allow_html=True)


def _process_registration(name, employee_id, frame, face_rec, face_db):
    """Extract face embedding and register employee."""
    if not name or not employee_id:
        st.error(T._("reg_error_fields"))
        return

    embedding = face_rec.register_from_frame(frame, name)
    if embedding is None:
        st.error(T._("reg_error_face"))
        return

    face_db.register(name, employee_id, embedding)
    st.success(f"{T._('reg_name')} '{name}' ({employee_id}) {T._('reg_success')}")


def page_reports():
    """Reports: view all attendance records, filter, export CSV."""
    st.title(T._("rep_title"))

    att_logger = get_attendance_logger()
    records = att_logger.get_all_records()

    if not records:
        st.info(T._("rep_no_records"))
        return

    df = pd.DataFrame(records)
    df["timestamp"] = df["timestamp"].apply(format_timestamp)

    st.subheader(T._("rep_filters"))
    col1, col2 = st.columns(2)
    with col1:
        all_employees = sorted(set(r["employee"] for r in records))
        selected_emp = st.selectbox(T._("rep_filter_emp"), [T._("rep_all")] + all_employees)
    with col2:
        event_type = st.selectbox(T._("rep_filter_event"), [T._("rep_all"), "checkin", "checkout"])

    filtered = df.copy()
    emp_label = T._("rep_filter_emp")
    evt_label = T._("rep_filter_event")
    
    if selected_emp != T._("rep_all"):
        filtered = filtered[filtered["employee"] == selected_emp]
    if event_type != T._("rep_all"):
        filtered = filtered[filtered["event"] == event_type]

    st.subheader(f"{T._('rep_showing')} {len(filtered)} {T._('rep_records')}")
    display_df = filtered.rename(columns={
        "employee": T._("col_employee"),
        "event": T._("col_event"),
        "timestamp": T._("col_time"),
        "confidence": T._("col_confidence"),
    })
    st.dataframe(display_df, use_container_width=True)

    st.subheader(T._("rep_export"))
    csv_data = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=T._("rep_btn_download"),
        data=csv_data,
        file_name=f"attendance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )


def page_live_camera():
    """Live Camera: preview camera feed using Streamlit's camera_input."""
    st.title(T._("cam_title"))
    st.info(T._("cam_info"))

    config = load_config()
    camera_source = config["camera"]["source"]
    st.write(f"{T._('cam_source')}: {camera_source}")

    camera_img = st.camera_input(T._("cam_snapshot"))
    if camera_img is not None:
        file_bytes = np.frombuffer(camera_img.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if frame is not None:
            frame = cv2.flip(frame, 1)
            st.image(frame, channels="BGR", caption=T._("cam_caption"))
            st.write(f"Frame size: {frame.shape[1]}x{frame.shape[0]}")

            face_rec = get_face_recognizer()
            with st.spinner(T._("cam_detecting")):
                faces = face_rec.detect_faces(frame)
            if faces:
                st.success(f"{T._('cam_detected')} {len(faces)} {T._('cam_face_s')}")
                for i, face in enumerate(faces):
                    bbox = face["bbox"]
                    st.write(f"Face {i+1}: bbox=({bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f})")
            else:
                st.warning(T._("cam_no_face"))


def page_guard_mode():
    """Guard Mode: Manage access control rules and employee exceptions."""
    st.title(T._("guard_title"))
    st.caption(T._("guard_caption"))

    config = load_config()
    guard_config = config.get("guard_mode", {})

    # Settings Card
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader(T._("guard_status"))
    
    is_enabled = guard_config.get("enabled", False)
    st.write(T._("guard_mode_on") if is_enabled else T._("guard_mode_off"))
    st.write(f"{T._('guard_work_hours')}: {guard_config.get('work_hours', {}).get('start')} - {guard_config.get('work_hours', {}).get('end')}")
    st.write(f"{T._('guard_grace')}: {guard_config.get('grace_period_minutes')} minutes")
    
    st.info(T._("guard_info_toggle"))
    st.markdown('</div>', unsafe_allow_html=True)

    # Exception Management Card
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader(T._("guard_exc_title"))
    
    face_db = get_face_database()
    exception_mgr = ExceptionManager(db_path=str(ROOT / guard_config["exception_db"]))
    
    all_employees = face_db.get_all_employees()
    emp_names = [e["name"] for e in all_employees]

    col1, col2 = st.columns(2)
    with col1:
        emp_name = st.selectbox(T._("guard_sel_emp"), emp_names)
        exc_type = st.selectbox(
            T._("guard_type"), 
            [T._("guard_type_leave"), T._("guard_type_business")],
            format_func=lambda x: x
        )
        # Map translated type back to database key
        type_key = "leave" if exc_type == T._("guard_type_leave") else "business"
    with col2:
        start_dt = st.date_input(T._("guard_start"))
        end_dt = st.date_input(T._("guard_end"))
    
    reason = st.text_area(T._("guard_reason"))

    if st.button(T._("guard_btn_submit"), type="primary", use_container_width=True):
        if not emp_name:
            st.error(T._("guard_err_emp"))
        else:
            start_str = f"{start_dt} {guard_config.get('work_hours', {}).get('start', '09:00')}:00"
            end_str = f"{end_dt} {guard_config.get('work_hours', {}).get('end', '18:00')}:00"
            
            exception_mgr.add_exception(
                employee_id=emp_name,
                exception_type=type_key,
                start_time=start_str,
                end_time=end_str,
                reason=reason
            )
            st.success(f"{T._('guard_success_exc')} {emp_name} {T._('guard_success_exc_to')} {start_str} {T._('guard_success_exc_to')} {end_str}")

    st.markdown('</div>', unsafe_allow_html=True)

    # Active Exceptions Table
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader(T._("guard_exc_list"))
    
    exceptions = exception_mgr.get_all_exceptions(limit=50)
    if exceptions:
        df = pd.DataFrame(exceptions)
        df = df[["employee_id", "type", "start_time", "end_time", "status", "reason"]]
        df = df.rename(columns={
            "employee_id": T._("col_employee"),
            "type": T._("guard_type"),
            "start_time": T._("col_from"),
            "end_time": T._("col_to"),
            "status": T._("col_status"),
            "reason": T._("col_reason")
        })
        st.dataframe(df, use_container_width=True)
    else:
        st.info(T._("guard_no_exc"))
    st.markdown('</div>', unsafe_allow_html=True)


def main():
    """Main entry point for the Streamlit app."""
    st.set_page_config(
        page_title=T._("sidebar_title"),
        page_icon="👤",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Apply the Linear-style Dark Mode design
    set_page_design()

    # Language State Management
    if "language" not in st.session_state:
        st.session_state.language = "zh"

    # Sidebar Navigation
    with st.sidebar:
        st.image("https://img.icons8.com/ios-filled/50/8b5cf6/fingerprint.png", width=50)
        st.title(T._("sidebar_title"))
        st.caption(T._("sidebar_caption"))
        st.divider()

        # Language Selector
        lang_option = st.radio(
            T._("lang_label"),
            ["繁體中文", "English"],
            index=0 if st.session_state.language == "zh" else 1,
            key="lang_selector"
        )
        
        if lang_option == "English" and st.session_state.language != "en":
            st.session_state.language = "en"
            st.rerun()
        elif lang_option == "繁體中文" and st.session_state.language != "zh":
            st.session_state.language = "zh"
            st.rerun()
        
        T.set_language(st.session_state.language)

    page = st.sidebar.radio(
        T._("nav_label"),
        [T._("nav_dashboard"), T._("nav_register"), T._("nav_reports"), T._("nav_camera"), T._("nav_guard")],
    )
    
    st.divider()

    if page == T._("nav_dashboard"):
        page_dashboard()
    elif page == T._("nav_register"):
        page_register()
    elif page == T._("nav_reports"):
        page_reports()
    elif page == T._("nav_camera"):
        page_live_camera()
    elif page == T._("nav_guard"):
        page_guard_mode()


if __name__ == "__main__":
    main()

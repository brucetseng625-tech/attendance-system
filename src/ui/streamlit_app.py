"""Streamlit UI for the AI Face Attendance System.

Provides 4 pages: Dashboard, Register Employee, Reports, Live Camera.
Uses st.cache_resource for heavy model/database objects.
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

ROOT = get_project_root()


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
    st.title("Attendance Dashboard")
    st.caption(f"Today: {datetime.now().strftime('%Y-%m-%d')}")

    att_logger = get_attendance_logger()
    face_db = get_face_database()
    records = att_logger.get_today_records()
    employees = face_db.get_all_employees()

    st.subheader("Summary")
    col1, col2, col3 = st.columns(3)

    checkins = [r for r in records if r["event"] == "checkin"]
    checkouts = [r for r in records if r["event"] == "checkout"]
    unique_today = set(r["employee"] for r in records)

    with col1:
        st.metric("Total Check-ins", len(checkins))
    with col2:
        st.metric("Total Check-outs", len(checkouts))
    with col3:
        st.metric("Unique Employees Today", len(unique_today))

    st.subheader("Registered Employees")
    st.write(f"Total registered: {len(employees)}")
    if employees:
        emp_df = pd.DataFrame(employees)
        st.dataframe(emp_df, use_container_width=True)
    else:
        st.info("No employees registered yet. Go to Register Employee to add someone.")

    st.subheader("Today's Records")
    if records:
        df = pd.DataFrame(records)
        df["timestamp"] = df["timestamp"].apply(format_timestamp)
        df = df.rename(columns={
            "employee": "Employee",
            "event": "Event",
            "timestamp": "Time",
            "confidence": "Confidence",
        })
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No attendance records for today yet.")


def page_register():
    """Register Employee: upload photo or use camera, extract embedding, save."""
    st.title("Register Employee")

    face_rec = get_face_recognizer()
    face_db = get_face_database()

    name = st.text_input("Employee Name", placeholder="e.g. Bruce")
    employee_id = st.text_input("Employee ID", placeholder="e.g. EMP001")

    tab_upload, tab_camera = st.tabs(["Upload Photo", "Take Photo"])

    with tab_upload:
        uploaded_file = st.file_uploader(
            "Upload a clear face photo",
            type=["jpg", "jpeg", "png"],
        )
        if uploaded_file is not None:
            file_bytes = np.frombuffer(uploaded_file.read(), np.uint8)
            frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if frame is not None:
                st.image(frame, channels="BGR", caption="Uploaded photo")
                if st.button("Register from Upload", type="primary"):
                    _process_registration(name, employee_id, frame, face_rec, face_db)

    with tab_camera:
        camera_img = st.camera_input("Take a photo")
        if camera_img is not None:
            file_bytes = np.frombuffer(camera_img.read(), np.uint8)
            frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if frame is not None:
                # Flip horizontally to match main.py behavior (non-mirror mode)
                frame = cv2.flip(frame, 1)
                st.image(frame, channels="BGR", caption="Captured photo")
                if st.button("Register from Camera", type="primary"):
                    _process_registration(name, employee_id, frame, face_rec, face_db)


def _process_registration(name, employee_id, frame, face_rec, face_db):
    """Extract face embedding and register employee."""
    if not name or not employee_id:
        st.error("Please provide both name and employee ID.")
        return

    embedding = face_rec.register_from_frame(frame, name)
    if embedding is None:
        st.error(
            "Could not detect exactly one face in the image. "
            "Please upload a clear photo with a single face."
        )
        return

    face_db.register(name, employee_id, embedding)
    st.success(f"Employee '{name}' ({employee_id}) registered successfully!")


def page_reports():
    """Reports: view all attendance records, filter, export CSV."""
    st.title("Attendance Reports")

    att_logger = get_attendance_logger()
    records = att_logger.get_all_records()

    if not records:
        st.info("No attendance records found.")
        return

    df = pd.DataFrame(records)
    df["timestamp"] = df["timestamp"].apply(format_timestamp)

    st.subheader("Filters")
    col1, col2 = st.columns(2)
    with col1:
        all_employees = sorted(set(r["employee"] for r in records))
        selected_emp = st.selectbox("Employee", ["All"] + all_employees)
    with col2:
        event_type = st.selectbox("Event Type", ["All", "checkin", "checkout"])

    filtered = df.copy()
    if selected_emp != "All":
        filtered = filtered[filtered["employee"] == selected_emp]
    if event_type != "All":
        filtered = filtered[filtered["event"] == event_type]

    st.subheader(f"Showing {len(filtered)} records")
    display_df = filtered.rename(columns={
        "employee": "Employee",
        "event": "Event",
        "timestamp": "Time",
        "confidence": "Confidence",
    })
    st.dataframe(display_df, use_container_width=True)

    st.subheader("Export")
    csv_data = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name=f"attendance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )


def page_live_camera():
    """Live Camera: preview camera feed using Streamlit's camera_input."""
    st.title("Live Camera Preview")
    st.info(
        "Use your webcam to preview the camera feed. "
        "For real-time attendance tracking, run `python main.py` from the project root."
    )

    config = load_config()
    camera_source = config["camera"]["source"]
    st.write(f"Camera source: {camera_source}")

    camera_img = st.camera_input("Take a snapshot")
    if camera_img is not None:
        file_bytes = np.frombuffer(camera_img.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if frame is not None:
            # Flip horizontally to match main.py behavior (non-mirror mode)
            frame = cv2.flip(frame, 1)
            st.image(frame, channels="BGR", caption="Camera preview")
            st.write(f"Frame size: {frame.shape[1]}x{frame.shape[0]}")

            face_rec = get_face_recognizer()
            with st.spinner("Detecting faces..."):
                faces = face_rec.detect_faces(frame)
            if faces:
                st.success(f"Detected {len(faces)} face(s)")
                for i, face in enumerate(faces):
                    bbox = face["bbox"]
                    st.write(f"Face {i+1}: bbox=({bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f})")
            else:
                st.warning("No faces detected in the frame.")


def main():
    """Main entry point for the Streamlit app."""
    st.set_page_config(
        page_title="Face Attendance System",
        page_icon="👤",
        layout="wide",
    )

    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Register Employee", "Reports", "Live Camera"],
    )

    if page == "Dashboard":
        page_dashboard()
    elif page == "Register Employee":
        page_register()
    elif page == "Reports":
        page_reports()
    elif page == "Live Camera":
        page_live_camera()


if __name__ == "__main__":
    main()

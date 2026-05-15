"""API Server for ERP/HR System Integration.

Usage:
    /Users/brucetseng/Projects/ComfyUI/venv/bin/python3 -m src.api_server
"""

import json
from pathlib import Path
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Query
from loguru import logger

from src.config import get_project_root, load_config
from src.exception_manager import ExceptionManager

app = FastAPI(title="Attendance System API", version="1.1.0")


def get_attendance_db_connection():
    """Get a connection to the attendance database."""
    import sqlite3
    config = load_config()
    root = get_project_root()
    db_path = root / config["attendance"]["database"]
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "service": "attendance-api"}


@app.get("/api/v1/attendance/today")
async def get_todays_attendance():
    """Get all attendance records for today."""
    conn = get_attendance_db_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM attendance WHERE date(timestamp) = date('now') ORDER BY timestamp DESC"
        )
        rows = cursor.fetchall()
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "count": len(rows),
            "records": [dict(row) for row in rows],
        }
    finally:
        conn.close()


@app.get("/api/v1/attendance/history")
async def get_attendance_history(days: int = 7):
    """Get attendance records for the last N days."""
    conn = get_attendance_db_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM attendance WHERE timestamp > datetime('now', '-{} days') ORDER BY timestamp DESC".format(days)
        )
        rows = cursor.fetchall()
        return {
            "days": days,
            "count": len(rows),
            "records": [dict(row) for row in rows],
        }
    finally:
        conn.close()


@app.get("/api/v1/guard/status")
async def get_guard_status(employee_id: str = Query(..., description="Employee Name or ID")):
    """Get current access status for an employee."""
    config = load_config()
    guard_config = config.get("guard_mode", {})
    
    if not guard_config.get("enabled", False):
        return {"status": "disabled", "message": "Guard mode is currently disabled."}

    root = get_project_root()
    exc_mgr = ExceptionManager(db_path=str(root / guard_config["exception_db"]))
    
    is_exempted = exc_mgr.is_exempted(employee_id)
    if is_exempted:
        return {"status": "exempted", "message": "Employee has an active leave/trip request."}

    from src.guard_engine import GuardEngine
    engine = GuardEngine(config)
    status = engine.get_status(employee_id)
    
    return {
        "status": status.status,
        "message": status.message,
        "is_abnormal": status.is_abnormal
    }


@app.get("/api/v1/exceptions")
async def list_exceptions(status: str = "approved"):
    """List all approved exceptions."""
    config = load_config()
    root = get_project_root()
    exc_mgr = ExceptionManager(db_path=str(root / config["guard_mode"]["exception_db"]))
    exceptions = exc_mgr.get_all_exceptions()
    if status:
        exceptions = [e for e in exceptions if e["status"] == status]
    return {"count": len(exceptions), "exceptions": exceptions}


if __name__ == "__main__":
    config = load_config()
    port = config.get("api", {}).get("port", 8000)
    logger.info(f"Starting Attendance API Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

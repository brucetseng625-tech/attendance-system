"""API Server for ERP/HR System Integration.

Usage:
    /Users/brucetseng/Projects/ComfyUI/venv/bin/python3 -m src.api_server
"""

import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from loguru import logger

# We need to access the attendance logger directly or just read the DB.
# Reading the DB directly is safer to avoid circular imports or thread issues.
import sqlite3
from datetime import datetime

from src.config import get_project_root, load_config

app = FastAPI(title="Attendance System API", version="1.0.0")


def get_attendance_db_connection():
    """Get a connection to the attendance database."""
    config = load_config()
    root = get_project_root()
    db_path = root / config["attendance"]["database"]
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Return dictionary-like rows
    return conn


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "service": "attendance-api"}


@app.get("/api/v1/attendance/today")
async def get_todays_attendance():
    """Get all attendance records for today."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    conn = get_attendance_db_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM attendance WHERE date(timestamp) = date('now') ORDER BY timestamp DESC"
        )
        rows = cursor.fetchall()
        return {
            "date": today_str,
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


if __name__ == "__main__":
    config = load_config()
    port = config.get("api", {}).get("port", 8000)
    logger.info(f"Starting Attendance API Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

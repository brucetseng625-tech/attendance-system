"""Employee face embedding database with SQLite backend."""

import sqlite3
from pathlib import Path
from typing import Optional

import numpy as np


class FaceDatabase:
    """Stores employee face embeddings and handles matching."""

    def __init__(self, db_path: str = "data/faces.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        """Get a new connection for thread safety."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                name TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                embedding BLOB NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def register(self, name: str, employee_id: str, embedding: np.ndarray):
        """Register an employee with their face embedding."""
        conn = self._get_conn()
        try:
            emb_bytes = embedding.tobytes()
            conn.execute(
                "INSERT OR REPLACE INTO employees (name, employee_id, embedding) VALUES (?, ?, ?)",
                (name, employee_id, emb_bytes),
            )
            conn.commit()
        finally:
            conn.close()

    def get_employee(self, name: str) -> Optional[dict]:
        """Get employee by name."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT name, employee_id, embedding, registered_at FROM employees WHERE name = ?",
                (name,),
            ).fetchone()
            if row is None:
                return None
            return {
                "name": row[0],
                "employee_id": row[1],
                "embedding": np.frombuffer(row[2], dtype=np.float32),
                "registered_at": row[3],
            }
        finally:
            conn.close()

    def close(self) -> None:
        """Safely close the database connection if it exists."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def get_all_employees(self) -> list[dict]:
        """Get all registered employees (without embeddings to save memory)."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT name, employee_id, registered_at FROM employees ORDER BY name"
            ).fetchall()
            return [
                {"name": r[0], "employee_id": r[1], "registered_at": r[2]}
                for r in rows
            ]
        finally:
            conn.close()

    def remove_employee(self, name: str):
        """Remove an employee."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM employees WHERE name = ?", (name,))
            conn.commit()
        finally:
            conn.close()

    def match(self, embedding: np.ndarray, threshold: float = 0.4) -> Optional[str]:
        """Match a face embedding against all registered employees.

        Returns employee name if match found, None otherwise.
        Uses cosine similarity: similarity >= (1 - threshold) counts as match.
        """
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT name, embedding FROM employees").fetchall()
            if not rows:
                return None

            best_name = None
            best_sim = 0.0

            for name, emb_blob in rows:
                stored = np.frombuffer(emb_blob, dtype=np.float32)
                sim = cosine_similarity(embedding, stored)
                if sim > best_sim:
                    best_sim = sim
                    best_name = name

            if best_sim >= (1.0 - threshold):
                return best_name
            return None
        finally:
            conn.close()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))

"""Tests for the employee face database."""

import os
import numpy as np
import pytest
from src.face_db import FaceDatabase


@pytest.fixture
def db(tmp_path):
    return FaceDatabase(db_path=str(tmp_path / "faces.db"))


def test_register_employee(db):
    """Register an employee with a face embedding."""
    embedding = np.random.randn(512).astype(np.float32)
    db.register("Bruce", "EMP001", embedding)
    emp = db.get_employee("Bruce")
    assert emp is not None
    assert emp["name"] == "Bruce"
    assert emp["employee_id"] == "EMP001"


def test_get_all_employees(db):
    """Get all registered employees."""
    db.register("Alice", "EMP001", np.random.randn(512).astype(np.float32))
    db.register("Bob", "EMP002", np.random.randn(512).astype(np.float32))
    employees = db.get_all_employees()
    assert len(employees) == 2
    names = [e["name"] for e in employees]
    assert "Alice" in names
    assert "Bob" in names


def test_remove_employee(db):
    """Remove an employee from the database."""
    embedding = np.random.randn(512).astype(np.float32)
    db.register("Charlie", "EMP003", embedding)
    assert db.get_employee("Charlie") is not None
    db.remove_employee("Charlie")
    assert db.get_employee("Charlie") is None


def test_match_face_exact(db):
    """Match an exact embedding returns the correct employee."""
    embedding = np.random.randn(512).astype(np.float32)
    db.register("Dave", "EMP004", embedding)
    name = db.match(embedding, threshold=0.4)
    assert name == "Dave"


def test_match_face_no_match(db):
    """Completely different embedding should not match."""
    db.register("Eve", "EMP005", np.random.randn(512).astype(np.float32))
    # Random embedding unlikely to match
    random_emb = np.random.randn(512).astype(np.float32)
    name = db.match(random_emb, threshold=0.1)
    assert name is None


def test_match_empty_db(db):
    """Match against an empty database returns None."""
    embedding = np.random.randn(512).astype(np.float32)
    name = db.match(embedding, threshold=0.4)
    assert name is None


def test_register_overwrite(db):
    """Re-registering same name updates the embedding."""
    emb1 = np.ones(512, dtype=np.float32)
    emb2 = np.full(512, 2.0, dtype=np.float32)
    db.register("Frank", "EMP006", emb1)
    db.register("Frank", "EMP007", emb2)
    emp = db.get_employee("Frank")
    assert emp["employee_id"] == "EMP007"
    # Check embedding was updated
    np.testing.assert_array_almost_equal(emp["embedding"], emb2)

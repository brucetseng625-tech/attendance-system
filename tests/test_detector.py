"""Tests for the detection pipeline."""

import numpy as np
import pytest
from src.detector import ZoneChecker


def test_zone_checker_point_inside():
    """Center of square zone should be inside."""
    checker = ZoneChecker(points=[(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)])
    assert checker.is_inside(0.5, 0.5) is True


def test_zone_checker_point_outside():
    """Points outside the zone should return False."""
    checker = ZoneChecker(points=[(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)])
    assert checker.is_inside(0.1, 0.1) is False
    assert checker.is_inside(0.9, 0.9) is False


def test_zone_checker_on_edge():
    """Points exactly on the edge should be considered inside."""
    checker = ZoneChecker(points=[(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)])
    assert checker.is_inside(0.5, 0.2) is True


def test_zone_checker_triangle():
    """ZoneChecker works with triangular zones."""
    checker = ZoneChecker(points=[(0.5, 0.0), (1.0, 1.0), (0.0, 1.0)])
    assert checker.is_inside(0.5, 0.6) is True
    assert checker.is_inside(0.5, -0.1) is False

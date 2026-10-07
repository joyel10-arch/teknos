"""
test_geometry.py — Unit tests for geometry utility functions.

Tests point_in_polygon and scale_polygon with inside/outside/edge cases.
No YOLO required.
"""

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.utils.geometry import point_in_polygon, scale_polygon, polygon_centroid


# ── Fixtures: simple square [0,0] to [10,10] ─────────────────────────────────
SQUARE = [[0, 0], [10, 0], [10, 10], [0, 10]]
TRIANGLE = [[0, 0], [10, 0], [5, 10]]


class TestPointInPolygon:

    def test_centre_inside_square(self):
        assert point_in_polygon([5, 5], SQUARE) is True

    def test_corner_point_is_on_edge(self):
        # cv2.pointPolygonTest returns >= 0 for on-edge
        assert point_in_polygon([0, 0], SQUARE) is True

    def test_point_on_edge_midpoint(self):
        assert point_in_polygon([5, 0], SQUARE) is True

    def test_outside_right(self):
        assert point_in_polygon([15, 5], SQUARE) is False

    def test_outside_above(self):
        assert point_in_polygon([5, -1], SQUARE) is False

    def test_outside_diagonal(self):
        assert point_in_polygon([11, 11], SQUARE) is False

    def test_centre_inside_triangle(self):
        assert point_in_polygon([5, 5], TRIANGLE) is True

    def test_outside_triangle(self):
        assert point_in_polygon([9, 9], TRIANGLE) is False

    def test_fewer_than_3_points_returns_false(self):
        # Degenerate polygon — must not crash
        assert point_in_polygon([5, 5], [[0, 0], [10, 10]]) is False

    def test_negative_coordinates(self):
        poly = [[-5, -5], [5, -5], [5, 5], [-5, 5]]
        assert point_in_polygon([0, 0], poly) is True
        assert point_in_polygon([10, 10], poly) is False

    def test_float_coords(self):
        assert point_in_polygon([5.5, 5.5], SQUARE) is True
        assert point_in_polygon([10.5, 5.0], SQUARE) is False


class TestScalePolygon:

    def test_scale_identity(self):
        scaled = scale_polygon(SQUARE, 640, 360, 640, 360)
        assert scaled == SQUARE

    def test_scale_double_width(self):
        scaled = scale_polygon([[100, 100], [200, 100], [200, 200], [100, 200]],
                                640, 360, 1280, 360)
        # x should double, y should stay
        assert scaled[0] == [200.0, 100.0]
        assert scaled[1] == [400.0, 100.0]

    def test_scale_half_resolution(self):
        scaled = scale_polygon([[400, 200]], 640, 360, 320, 180)
        assert scaled[0][0] == pytest.approx(200.0, abs=0.01)
        assert scaled[0][1] == pytest.approx(100.0, abs=0.01)

    def test_scale_preserves_polygon_length(self):
        scaled = scale_polygon(SQUARE, 640, 360, 1920, 1080)
        assert len(scaled) == len(SQUARE)

    def test_scaled_point_is_inside_scaled_polygon(self):
        """A point inside the original should be inside the scaled polygon too."""
        orig_poly = [[100, 100], [200, 100], [200, 200], [100, 200]]
        orig_pt   = [150, 150]
        # Scale 2x
        scaled_poly = scale_polygon(orig_poly, 640, 360, 1280, 720)
        scaled_pt   = [orig_pt[0] * 2, orig_pt[1] * 2]
        assert point_in_polygon(scaled_pt, scaled_poly) is True


class TestPolygonCentroid:

    def test_square_centroid(self):
        cx, cy = polygon_centroid(SQUARE)
        assert cx == pytest.approx(5.0)
        assert cy == pytest.approx(5.0)

    def test_triangle_centroid(self):
        cx, cy = polygon_centroid(TRIANGLE)
        assert cx == pytest.approx(5.0)
        assert cy == pytest.approx(10 / 3, abs=0.01)

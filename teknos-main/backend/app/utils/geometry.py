"""
geometry.py — Point-in-polygon and polygon scaling utilities.

WHAT: Provides reusable, dependency-free geometry helpers:
  - point_in_polygon: uses cv2.pointPolygonTest (internally handles the
    even-odd / winding math so we don't need shapely)
  - scale_polygon: scale polygon coords from reference resolution to
    actual video resolution
  - polygon_centroid: arithmetic mean of vertices (for label placement)

WHY cv2.pointPolygonTest?  It is already available (OpenCV is a hard
dependency), well-tested, and handles edge cases.  No need to add shapely.
"""

from __future__ import annotations

import numpy as np
import cv2


def point_in_polygon(point: list[float] | tuple[float, float],
                     polygon: list[list[float]]) -> bool:
    """Return True if *point* (x, y) is inside or on the edge of *polygon*.

    Uses cv2.pointPolygonTest which implements the ray-casting algorithm.
    A return value >= 0 means inside or on edge; < 0 means outside.

    Parameters
    ----------
    point   : [x, y] or (x, y)
    polygon : list of [x, y] vertices (>= 3 points)

    Example
    -------
    >>> point_in_polygon([5, 5], [[0,0],[10,0],[10,10],[0,10]])
    True
    >>> point_in_polygon([15, 5], [[0,0],[10,0],[10,10],[0,10]])
    False
    """
    if len(polygon) < 3:
        return False
    # cv2.pointPolygonTest needs a float32 numpy array of shape (N, 1, 2)
    contour = np.array(polygon, dtype=np.float32).reshape((-1, 1, 2))
    px, py = float(point[0]), float(point[1])
    # >= 0: inside or on edge; < 0: outside
    result = cv2.pointPolygonTest(contour, (px, py), measureDist=False)
    return bool(result >= 0)


def scale_polygon(
    polygon: list[list[float]],
    ref_width: int,
    ref_height: int,
    actual_width: int,
    actual_height: int,
) -> list[list[float]]:
    """Scale polygon vertices from reference resolution to actual resolution.

    Each point is scaled independently:
        x_scaled = x * (actual_width  / ref_width)
        y_scaled = y * (actual_height / ref_height)

    This lets a single zone JSON template serve multiple video resolutions.

    Parameters
    ----------
    polygon       : list of [x, y] vertices in reference coordinates
    ref_width     : reference frame width (px)
    ref_height    : reference frame height (px)
    actual_width  : actual frame width (px)
    actual_height : actual frame height (px)

    Returns
    -------
    New list of scaled [x, y] vertices (floats).
    """
    sx = actual_width  / ref_width
    sy = actual_height / ref_height
    return [[pt[0] * sx, pt[1] * sy] for pt in polygon]


def polygon_centroid(polygon: list[list[float]]) -> tuple[float, float]:
    """Return the arithmetic centroid (mean x, mean y) of a polygon.

    Used to position zone labels in rendered frames.
    """
    arr = np.array(polygon, dtype=np.float32)
    cx = float(arr[:, 0].mean())
    cy = float(arr[:, 1].mean())
    return cx, cy


def polygon_bounding_box(polygon: list[list[float]]) -> tuple[int, int, int, int]:
    """Return (x_min, y_min, x_max, y_max) bounding box of a polygon."""
    arr = np.array(polygon, dtype=np.float32)
    return (
        int(arr[:, 0].min()),
        int(arr[:, 1].min()),
        int(arr[:, 0].max()),
        int(arr[:, 1].max()),
    )

"""
time_utils.py — Timestamp formatting helpers.
"""

from __future__ import annotations


def format_timestamp(seconds: float) -> str:
    """Return mm:ss.s format, e.g. 01:04.3.

    >>> format_timestamp(64.3)
    '01:04.3'
    >>> format_timestamp(0.0)
    '00:00.0'
    """
    seconds = max(0.0, seconds)
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m:02d}:{s:04.1f}"


def seconds_to_hms(seconds: float) -> str:
    """Return hh:mm:ss format.

    >>> seconds_to_hms(3661.0)
    '01:01:01'
    """
    seconds = max(0.0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

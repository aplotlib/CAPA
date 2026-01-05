# src/time_windows.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta

@dataclass(frozen=True)
class DateWindow:
    start: date
    end: date  # inclusive

def preset_window(days: int, today: date | None = None) -> DateWindow:
    today = today or date.today()
    return DateWindow(start=today - timedelta(days=days), end=today)

def custom_window(start: date, end: date) -> DateWindow:
    if start > end:
        raise ValueError("Start date must be <= end date")
    return DateWindow(start=start, end=end)

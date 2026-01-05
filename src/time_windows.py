from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional


@dataclass(frozen=True)
class TimeWindow:
    label: str
    start: datetime
    end: datetime
    preset_days: Optional[int]
    google_days_back: Optional[int]
    note: str


def _dt_floor(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 0, 0, 0)


def _dt_ceil(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 23, 59, 59)


def build_time_window(
    preset: str,
    custom_start: Optional[date],
    custom_end: Optional[date],
    now: Optional[datetime] = None,
) -> TimeWindow:
    now = now or datetime.utcnow()
    end = now

    presets = {
        "Last 30 days": 30,
        "Last 60 days": 60,
        "Last 90 days": 90,
        "Last 180 days": 180,
        "Last 365 days": 365,
        "Custom": None,
    }

    if preset not in presets:
        preset = "Last 90 days"

    days = presets[preset]
    if days is not None:
        start = end - timedelta(days=days)
        return TimeWindow(
            label=preset,
            start=start,
            end=end,
            preset_days=days,
            google_days_back=days,
            note="Google uses a rolling window (dateRestrict=dN). APIs use strict date filters where supported.",
        )

    # Custom
    if not custom_start or not custom_end:
        # fallback
        days = 90
        start = end - timedelta(days=days)
        return TimeWindow(
            label="Custom (fallback to last 90 days)",
            start=start,
            end=end,
            preset_days=days,
            google_days_back=days,
            note="Custom dates were incomplete; using last 90 days.",
        )

    start = _dt_floor(custom_start)
    custom_end_dt = _dt_ceil(custom_end)

    # Google limitation: only rolling windows from "now". Approximate by using days back to custom_start.
    google_days_back = max(1, (end.date() - custom_start).days)

    note = (
        "Google Custom Search does not support strict start/end date ranges. "
        f"Using an approximation: results from the last {google_days_back} days, "
        "then relying on API strict date filters where supported."
    )
    return TimeWindow(
        label=f"Custom: {custom_start.isoformat()} → {custom_end.isoformat()}",
        start=start,
        end=custom_end_dt,
        preset_days=None,
        google_days_back=google_days_back,
        note=note,
    )

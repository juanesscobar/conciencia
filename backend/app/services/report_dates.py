"""Strict, locale-independent date parsing for report periods."""

from __future__ import annotations

from datetime import date, datetime, timezone


_FORMATS = ("%Y-%m-%d", "%d.%m.%y", "%d.%m.%Y", "%d/%m/%Y")


def parse_report_date(value: str | date | datetime | None) -> date | None:
    """Parse only unambiguous report formats; never guess month/day order."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip().casefold()
    if not raw:
        return None
    if raw == "today":
        return datetime.now(timezone.utc).date()
    for fmt in _FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date '{value}'. Use YYYY-MM-DD, DD.MM.YY, or DD/MM/YYYY.")

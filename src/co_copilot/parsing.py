"""Canonical parsers for dates and commercial numbers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%d %B %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %b %Y",
)


@dataclass(frozen=True)
class ParsedDate:
    """Parsed date plus any ambiguity warning."""

    value: date | None
    warning: str | None = None


def parse_date(value: object, day_first: bool | None = None) -> ParsedDate:
    """Parse common contract-register dates and Excel serial values.

    Ambiguous numeric dates are accepted with a warning so the UI can ask the
    user to confirm the interpretation.

    Args:
        value: String, date, datetime, number, or missing value.
        day_first: Preferred ordering for ambiguous slash dates.

    Returns:
        Parsed date and optional ambiguity warning.
    """
    if value is None:
        return ParsedDate(None)
    if isinstance(value, datetime):
        return ParsedDate(value.date())
    if isinstance(value, date):
        return ParsedDate(value)
    if isinstance(value, int | float) and 1 <= float(value) <= 100000:
        excel_epoch = date(1899, 12, 30)
        return ParsedDate(excel_epoch + timedelta(days=int(float(value))))

    raw = str(value).strip()
    if not raw or raw.lower() in {"not provided", "not required", "n/a", "none"}:
        return ParsedDate(None)

    numeric = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)
    warning = None
    formats = list(_DATE_FORMATS)
    if numeric:
        first, second = int(numeric.group(1)), int(numeric.group(2))
        if first <= 12 and second <= 12:
            assumed_day_first = day_first is not False
            chosen = "%d/%m/%Y" if assumed_day_first else "%m/%d/%Y"
            formats.remove(chosen)
            formats.insert(0, chosen)
            label = "DD/MM/YYYY" if assumed_day_first else "MM/DD/YYYY"
            warning = f"Ambiguous date '{raw}' interpreted as {label}."

    for fmt in formats:
        try:
            return ParsedDate(datetime.strptime(raw, fmt).date(), warning)
        except ValueError:
            continue
    return ParsedDate(None, f"Could not parse date '{raw}'.")


def parse_currency_amount(raw: str) -> float | None:
    """Parse signed amounts with commas and K/M/B unit suffixes."""
    cleaned = raw.upper().replace(",", "").replace(" ", "")
    cleaned = cleaned.replace("US$", "").replace("$", "").replace("USD", "")
    match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)([KMB])?", cleaned)
    if not match:
        return None
    multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(match.group(2), 1)
    try:
        return float(Decimal(match.group(1)) * multiplier)
    except InvalidOperation:
        return None

#!/usr/bin/env python3
"""
Which edition a run is making.

GitHub often starts scheduled runs hours late (6–9 hours in November 2026),
so the digest is made the evening before: a run on Sunday or Wednesday
afternoon/evening (Athens time) makes the next morning's Monday or Thursday
edition. A run that is so late it starts after midnight still makes that
same edition, because by then it is Monday or Thursday.

Everything that depends on the date (name days, joke, weather, news
look-back, file names, the date on the page) uses edition_date().

Run directly, it prints the edition date as YYYYMMDD (used by the workflow).
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

ATHENS = ZoneInfo("Europe/Athens")


def edition_date(now: datetime | None = None) -> date:
    """The date of the edition being made (Athens time)."""
    now = now.astimezone(ATHENS) if now else datetime.now(ATHENS)
    # Sunday (6) or Wednesday (2) from noon on → tomorrow's edition.
    if now.weekday() in (6, 2) and now.hour >= 12:
        return now.date() + timedelta(days=1)
    return now.date()


if __name__ == "__main__":
    print(edition_date().strftime("%Y%m%d"))

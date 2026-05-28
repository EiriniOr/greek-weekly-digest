#!/usr/bin/env python3
"""
Greek Orthodox nameday calendar.
Fixed feasts are keyed by (month, day).
Moveable feasts (Easter-relative) are computed at runtime.
"""

from datetime import date, timedelta

# (month, day) → list of names celebrated
NAMEDAYS: dict[tuple[int, int], list[str]] = {
    # January
    (1, 1): ["Βασίλης", "Βασίλειος", "Βασιλική", "Βάσω"],
    (1, 2): ["Σίλβεστρος"],
    (1, 6): ["Φώτης", "Φωτεινή", "Φώτιος"],
    (1, 7): ["Ιωάννης", "Γιάννης", "Ιωάννα", "Γιαννούλα"],
    (1, 11): ["Θεοδόσιος", "Θεοδοσία"],
    (1, 14): ["Σάββας"],
    (1, 17): ["Αντώνης", "Αντώνιος", "Αντωνία"],
    (1, 18): ["Αθανάσιος", "Αθανασία", "Θανάσης", "Κύριλλος"],
    (1, 20): ["Ευθύμιος", "Ευθυμία"],
    (1, 25): ["Γρηγόριος", "Γρηγόρης", "Γρηγορία"],
    (1, 27): ["Ιωάννης Χρυσόστομος"],
    (1, 28): ["Εφραίμ"],
    (1, 30): ["Βασίλης", "Γρηγόρης", "Ιωάννης"],
    # February
    (2, 9): ["Νικηφόρος"],
    (2, 10): ["Χαράλαμπος", "Χαραλαμπία", "Λάμπης"],
    (2, 11): ["Βλάσιος", "Βλασία"],
    # Θεόδωρος: Feb 17 is a fixed feast, but the main Greek nameday
    # (St. Theodore Tyron) is the first Saturday of Great Lent — handled below.
    (2, 17): ["Θεόδωρος", "Θεοδώρα", "Θοδωρής"],
    # March
    (3, 25): ["Ευάγγελος", "Ευαγγελία", "Βαγγέλης", "Βαγγελιώ", "Αγγελική", "Άγγελος"],
    # April — Γεώργιος is April 23 unless it falls in Holy Week (see moveable section)
    (4, 23): ["Γεώργιος", "Γιώργης", "Γιώργος", "Γεωργία", "Γεωργίνα"],
    # May
    (5, 2): ["Αθανάσιος", "Αθανασία"],
    (5, 5): ["Ειρήνη", "Ειρηνούλα"],
    (5, 8): ["Ιωάννης", "Γιάννης"],
    (5, 9): ["Νικόλαος", "Νίκος"],
    (5, 11): ["Κύριλλος", "Μεθόδιος"],
    (5, 15): ["Αχίλλειος", "Αχίλλας"],
    (5, 21): ["Κωνσταντίνος", "Κώστας", "Κωνσταντίνα", "Ελένη", "Νίνα"],
    (5, 27): ["Ιωάννης ο Ρώσος", "Ιωάννης", "Γιάννης"],
    (5, 29): ["Θεοδόσιος", "Θεοδοσία"],
    (5, 31): ["Ερμείας", "Ερμής"],
    # June
    (6, 2): ["Νικηφόρος"],
    (6, 3): ["Υπατία"],
    (6, 4): ["Μάρθα"],
    (6, 5): ["Δωροθέα", "Νίκη"],
    (6, 24): ["Ιωάννης", "Γιάννης"],
    (6, 29): ["Πέτρος", "Παύλος", "Πέτρα", "Παυλίνα"],
    # July
    (7, 1): ["Κοσμάς", "Δαμιανός", "Δαμιανή"],
    (7, 17): ["Μαρίνα", "Μαριλένα"],
    (7, 20): ["Ηλίας", "Ηλιάνα"],
    (7, 22): ["Μαρία Μαγδαληνή"],
    (7, 24): ["Χριστίνα", "Χριστίνη"],
    (7, 25): ["Άννα"],
    (7, 26): ["Παρασκευή", "Βούλα"],
    (7, 27): ["Παντελεήμων", "Παντελής"],
    # August
    (8, 6): ["Σωτήρης", "Σωτηρία", "Χριστόδουλος"],
    (8, 15): ["Παναγιώτης", "Παναγιώτα", "Μαρία", "Δέσποινα", "Δέσπω", "Λίτσα"],
    (8, 16): ["Γεράσιμος", "Γερασιμούλα"],
    (8, 29): ["Ιωάννης"],
    (8, 30): ["Αλέξανδρος", "Αλεξάνδρα", "Αλέξης", "Αλέκος"],
    # September
    (9, 8): ["Μαρία"],
    (9, 14): ["Σταύρος", "Σταυρούλα"],
    (9, 17): ["Σοφία", "Ελπίδα", "Πίστη", "Αγάπη"],
    (9, 26): ["Ιωάννης"],
    # October
    (10, 6): ["Θωμάς"],
    (10, 18): ["Λουκάς"],
    (10, 26): ["Δημήτριος", "Δημήτρης", "Δήμητρα", "Δημητρία"],
    # November
    (11, 8): ["Μιχάλης", "Μιχαήλ", "Γαβριήλ", "Αγγελική", "Άγγελος", "Αγγελίνα"],
    (11, 9): ["Νεκτάριος", "Νεκτάρια"],
    (11, 11): ["Μηνάς", "Βίκτωρ"],
    (11, 14): ["Φίλιππος", "Φιλίππα"],
    (11, 21): ["Παναγιώτης", "Παναγιώτα"],
    (11, 25): ["Αικατερίνη", "Κατερίνα"],
    (11, 26): ["Στυλιανός", "Στέλιος"],
    (11, 30): ["Ανδρέας", "Ανδρέα"],
    # December
    (12, 4): ["Βαρβάρα"],
    (12, 5): ["Σάββας"],
    (12, 6): ["Νικόλαος", "Νίκος", "Νικολέτα"],
    (12, 9): ["Άννα"],
    (12, 12): ["Σπυρίδων", "Σπύρος", "Σπυριδούλα"],
    (12, 15): ["Ελευθέριος", "Ελευθερία", "Λευτέρης"],
    (12, 17): ["Δανιήλ"],
    (12, 25): ["Εμμανουήλ", "Μανώλης"],
    (12, 27): ["Στέφανος", "Στεφανία"],
    (12, 31): ["Μελάνη", "Μελανία"],
}

GREEK_DAYS = [
    "Δευτέρα",
    "Τρίτη",
    "Τετάρτη",
    "Πέμπτη",
    "Παρασκευή",
    "Σάββατο",
    "Κυριακή",
]

GREEK_MONTHS = [
    "",
    "Ιανουαρίου",
    "Φεβρουαρίου",
    "Μαρτίου",
    "Απριλίου",
    "Μαΐου",
    "Ιουνίου",
    "Ιουλίου",
    "Αυγούστου",
    "Σεπτεμβρίου",
    "Οκτωβρίου",
    "Νοεμβρίου",
    "Δεκεμβρίου",
]

_GEORGE_NAMES = ["Γεώργιος", "Γιώργης", "Γιώργος", "Γεωργία", "Γεωργίνα"]
_THEODORE_NAMES = ["Θεόδωρος", "Θεοδώρα", "Θοδωρής"]
_ANASTASIOS_NAMES = ["Αναστάσιος", "Αναστασία", "Τάσος", "Τασία"]
_LAZAROS_NAMES = ["Λάζαρος", "Λαζαρίνα"]


def _orthodox_easter(year: int) -> date:
    """Compute Orthodox (Julian→Gregorian) Easter for the given year."""
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    f = d + e + 114
    month = f // 31
    day = (f % 31) + 1
    # Add 13 days to convert Julian → Gregorian (valid 1900–2099)
    return date(year, month, day) + timedelta(days=13)


def _moveable_namedays(year: int) -> dict[date, list[str]]:
    """Return {date: [names]} for moveable feasts in the given year."""
    easter = _orthodox_easter(year)
    result: dict[date, list[str]] = {}

    # Easter Sunday → Αναστάσιος/Αναστασία
    result[easter] = _ANASTASIOS_NAMES

    # Lazarus Saturday (Easter - 8 days)
    result[easter - timedelta(days=8)] = _LAZAROS_NAMES

    # First Saturday of Great Lent (Easter - 43 days)
    lent_saturday = easter - timedelta(days=43)
    result[lent_saturday] = _THEODORE_NAMES

    # St. George: April 23, but shifts to Bright Monday (Easter+1) if Holy Week
    george_date = date(year, 4, 23)
    palm_sunday = easter - timedelta(days=7)
    holy_saturday = easter - timedelta(days=1)
    if palm_sunday <= george_date <= holy_saturday:
        george_date = easter + timedelta(days=1)
        # Remove from fixed calendar for this year (handled here instead)
        result[george_date] = result.get(george_date, []) + _GEORGE_NAMES
    # If April 23 is NOT in Holy Week, the fixed entry in NAMEDAYS handles it.
    # We still emit it here when it's moved so the caller can skip the fixed entry.

    return result


def get_week_namedays(monday) -> list[dict]:
    """Return nameday entries for the 7 days starting from monday."""
    result = []
    # Compute moveable feasts for all years that could appear in this week
    years = {(monday + timedelta(days=i)).year for i in range(7)}
    moveable: dict[date, list[str]] = {}
    for yr in years:
        moveable.update(_moveable_namedays(yr))

    # Dates where George was moved — skip the fixed April 23 entry for those years
    george_moved_years = set()
    for yr in years:
        easter = _orthodox_easter(yr)
        george_fixed = date(yr, 4, 23)
        palm_sunday = easter - timedelta(days=7)
        holy_saturday = easter - timedelta(days=1)
        if palm_sunday <= george_fixed <= holy_saturday:
            george_moved_years.add(yr)

    for i in range(7):
        day = monday + timedelta(days=i)
        day_str = f"{GREEK_DAYS[i]} {day.day} {GREEK_MONTHS[day.month]}"

        # Fixed namedays (skip George on April 23 when it moved this year)
        fixed = list(NAMEDAYS.get((day.month, day.day), []))
        if day.month == 4 and day.day == 23 and day.year in george_moved_years:
            fixed = [n for n in fixed if n not in _GEORGE_NAMES]

        # Moveable namedays
        extra = moveable.get(day, [])

        for name in fixed + extra:
            result.append({"name": name, "date": day_str})

    return result

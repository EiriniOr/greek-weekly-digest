#!/usr/bin/env python3
"""
Greek Orthodox nameday calendar.

Fixed feasts come from namedays_data.json (vendored from
github.com/stavros-melidoniotis/greek-namedays, scraped from eortologio.net)
— names are never generated, only read from that dataset, so they cannot be
hallucinated. The dataset lists every obscure variant (up to 88 names/day),
so COMMON_NAMES filters announcements down to names people actually have.
The filter can only omit a name, never invent one.

Moveable feasts (Easter-relative) are computed at runtime from the same
dataset's moving-namedays rules, expressed here as day offsets from Easter.

USER_OVERRIDES holds corrections supplied by the listener's own calendar and
always wins over the dataset.
"""

import json
from datetime import date, timedelta
from pathlib import Path

_DATA_PATH = Path(__file__).parent / "namedays_data.json"
with open(_DATA_PATH, encoding="utf-8") as _f:
    _FIXED: dict[str, dict] = json.load(_f)

# Names worth announcing on air. Extend freely; a name missing here is
# silently skipped, never replaced with something else.
COMMON_NAMES = {
    # Α
    "Αγάπη",
    "Αγγελική",
    "Άγγελος",
    "Αγγελίνα",
    "Αγαθή",
    "Αθανάσιος",
    "Αθανασία",
    "Θανάσης",
    "Αικατερίνη",
    "Κατερίνα",
    "Καίτη",
    "Αλέξανδρος",
    "Αλεξάνδρα",
    "Αλέξης",
    "Αλέκος",
    "Αλέκα",
    "Αλίκη",
    "Αναστάσιος",
    "Αναστασία",
    "Τάσος",
    "Τασούλα",
    "Ανέστης",
    "Νατάσα",
    "Ανάργυρος",
    "Ανδρέας",
    "Ανδριανή",
    "Άννα",
    "Αντώνης",
    "Αντώνιος",
    "Αντωνία",
    "Απόστολος",
    "Αποστολία",
    "Αχιλλέας",
    "Αχίλλειος",
    # Β
    "Βαγγέλης",
    "Βαγγελιώ",
    "Ευάγγελος",
    "Ευαγγελία",
    "Βαρβάρα",
    "Βαρνάβας",
    "Βασίλειος",
    "Βασίλης",
    "Βασιλική",
    "Βάσω",
    "Βίκτωρ",
    "Βικτωρία",
    "Βλάσης",
    "Βλάσιος",
    "Βούλα",
    # Γ
    "Γαβριήλ",
    "Γεράσιμος",
    "Γεώργιος",
    "Γιώργος",
    "Γιώργης",
    "Γεωργία",
    "Γιάννης",
    "Γιάννα",
    "Ιωάννης",
    "Ιωάννα",
    "Γιαννούλα",
    "Γρηγόρης",
    "Γρηγόριος",
    "Γρηγορία",
    # Δ
    "Δαβίδ",
    "Δαμιανός",
    "Δανιήλ",
    "Δάφνη",
    "Δέσποινα",
    "Δημήτριος",
    "Δημήτρης",
    "Δήμητρα",
    "Δημητρία",
    "Δήμος",
    "Δωρόθεος",
    "Δωροθέα",
    # Ε
    "Ειρήνη",
    "Ειρηναίος",
    "Έκτορας",
    "Ελένη",
    "Έλενα",
    "Ελευθέριος",
    "Ελευθερία",
    "Λευτέρης",
    "Ελισάβετ",
    "Ελπίδα",
    "Εμμανουήλ",
    "Μανώλης",
    "Εμμανουέλα",
    "Ερρίκος",
    "Ευγενία",
    "Ευγένιος",
    "Ευθύμιος",
    "Ευθυμία",
    "Ευσέβιος",
    "Ευστάθιος",
    "Στάθης",
    "Εφραίμ",
    # Ζ
    "Ζαφείρης",
    "Ζαφειρία",
    "Ζήσης",
    "Ζωή",
    "Ζώης",
    # Η/Θ
    "Ηλίας",
    "Ηλιάνα",
    "Θεόδωρος",
    "Θοδωρής",
    "Θεοδώρα",
    "Δώρα",
    "Ντόρα",
    "Θεοδόσης",
    "Θεοδοσία",
    "Θεοφάνης",
    "Φάνης",
    "Θωμάς",
    "Θωμαή",
    # Κ
    "Καλλιόπη",
    "Πόπη",
    "Κοσμάς",
    "Κυριακή",
    "Κυριάκος",
    "Κύριλλος",
    "Κωνσταντίνος",
    "Κώστας",
    "Κωνσταντίνα",
    "Ντίνα",
    "Κορίνα",
    # Λ
    "Λάζαρος",
    "Λάμπρος",
    "Λουκάς",
    "Λουκία",
    "Λυδία",
    # Μ
    "Μαγδαληνή",
    "Μακάριος",
    "Μανουήλ",
    "Μαργαρίτα",
    "Μαρία",
    "Μάριος",
    "Μαριάννα",
    "Μαρίνα",
    "Μαρίνος",
    "Μάρθα",
    "Μάρκος",
    "Ματθαίος",
    "Μελίνα",
    "Μεθόδιος",
    "Μηνάς",
    "Μιχαήλ",
    "Μιχάλης",
    "Μυρτώ",
    # Ν
    "Νεκτάριος",
    "Νεκταρία",
    "Νεφέλη",
    "Νίκη",
    "Νικηφόρος",
    "Νικόλαος",
    "Νίκος",
    "Νικολέτα",
    "Νικόλας",
    # Ξ/Ο/Π
    "Ξένια",
    "Ορέστης",
    "Παναγιώτης",
    "Πάνος",
    "Παναγιώτα",
    "Γιώτα",
    "Παντελής",
    "Παντελεήμων",
    "Παρασκευή",
    "Παύλος",
    "Παυλίνα",
    "Πελαγία",
    "Πέτρος",
    "Πετρούλα",
    "Πηνελόπη",
    "Πολύκαρπος",
    # Ρ/Σ
    "Ραφαήλ",
    "Ραφαέλα",
    "Ρωξάνη",
    "Σάββας",
    "Σεραφείμ",
    "Σοφία",
    "Σπυρίδων",
    "Σπύρος",
    "Σπυριδούλα",
    "Σταμάτης",
    "Σταματία",
    "Σταύρος",
    "Σταυρούλα",
    "Στέλιος",
    "Στέλλα",
    "Στυλιανός",
    "Στυλιανή",
    "Στέφανος",
    "Στεφανία",
    "Σωτήρης",
    "Σωτηρία",
    # Τ/Υ/Φ
    "Τατιάνα",
    "Τιμόθεος",
    "Τριάδα",
    "Υπατία",
    "Φίλιππος",
    "Φιλίππα",
    "Φωτεινή",
    "Φώτης",
    "Φώτιος",
    # Χ
    "Χαράλαμπος",
    "Χάρης",
    "Χαρά",
    "Χαρούλα",
    "Χρήστος",
    "Χριστίνα",
    "Χριστόδουλος",
    "Χριστόφορος",
    "Χρυσούλα",
    "Χρύσα",
    # moveable-only names
    "Βάιος",
    "Βάια",
}

# Listener-supplied corrections; always included for their day.
USER_OVERRIDES: dict[tuple[int, int], list[str]] = {
    (6, 20): ["Έκτορας"],
    (6, 24): ["Ερρίκος"],
}

# Moveable feasts as offsets (days) from Orthodox Easter Sunday, taken from
# the dataset's moving_namedays rules. Only commonly held names included.
EASTER_OFFSET_NAMES: dict[int, list[str]] = {
    -43: ["Θεόδωρος", "Θοδωρής", "Θεοδώρα", "Δώρα", "Ντόρα"],
    -42: ["Μάριος", "Ρωξάνη"],
    -8: ["Λάζαρος"],
    -7: ["Βάιος", "Βάια", "Δάφνη"],
    0: ["Αναστάσιος", "Τάσος", "Ανέστης", "Αναστασία", "Τασούλα", "Νατάσα"],
    2: ["Ραφαήλ", "Ραφαέλα"],
    5: ["Ζώης", "Ζωή"],
    7: ["Θωμάς", "Θωμαή"],
    50: ["Τριάδα", "Κορίνα"],
}

_GEORGE_NAMES = ["Γεώργιος", "Γιώργος", "Γιώργης", "Γεωργία"]
_MARKOS_NAMES = ["Μάρκος"]

MAX_NAMES_PER_DAY = 8

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

    for offset, names in EASTER_OFFSET_NAMES.items():
        d = easter + timedelta(days=offset)
        result.setdefault(d, []).extend(names)

    # St. George: April 23, moved to Bright Monday when Easter falls on/after it.
    # St. Mark: April 25, moved to Bright Tuesday under the same condition.
    george = date(year, 4, 23)
    if easter >= george:
        result.setdefault(easter + timedelta(days=1), []).extend(_GEORGE_NAMES)
        result.setdefault(easter + timedelta(days=2), []).extend(_MARKOS_NAMES)
    else:
        result.setdefault(george, []).extend(_GEORGE_NAMES)
        result.setdefault(date(year, 4, 25), []).extend(_MARKOS_NAMES)

    return result


def _names_for_day(day: date, moveable: dict[date, list[str]]) -> list[str]:
    """Common names celebrating on this day, dataset order, deduped."""
    raw = list(_FIXED.get(f"{day.day}/{day.month}", {}).get("names", []))
    raw += moveable.get(day, [])
    raw += USER_OVERRIDES.get((day.month, day.day), [])

    seen = set()
    names = []
    for n in raw:
        if n in COMMON_NAMES and n not in seen:
            seen.add(n)
            names.append(n)
    return names[:MAX_NAMES_PER_DAY]


def get_week_namedays(monday) -> list[dict]:
    """Return nameday entries for the 7 days starting from monday."""
    if hasattr(monday, "date"):
        monday = monday.date()

    years = {(monday + timedelta(days=i)).year for i in range(7)}
    moveable: dict[date, list[str]] = {}
    for yr in years:
        moveable.update(_moveable_namedays(yr))

    result = []
    for i in range(7):
        day = monday + timedelta(days=i)
        names = _names_for_day(day, moveable)
        if names:
            day_str = f"{GREEK_DAYS[i]} {day.day} {GREEK_MONTHS[day.month]}"
            result.append({"name": ", ".join(names), "date": day_str})
    return result


if __name__ == "__main__":
    d = date.today()
    monday = d - timedelta(days=d.weekday())
    for entry in get_week_namedays(monday):
        print(f"{entry['date']}: {entry['name']}")

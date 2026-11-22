#!/usr/bin/env python3
"""
Greek Orthodox name days ("ποιοι γιορτάζουν").

HOW IT WORKS
------------
FIXED below is a short, hand-picked list: for each date, the everyday names
people actually celebrate. It is written the way you'd say it out loud
("Γιώργος", not "Γεώργιος").

Every name in FIXED is double-checked against namedays_data.json (the full
eortologio.net calendar, vendored from github.com/stavros-melidoniotis/
greek-namedays). If a name is NOT listed in that dataset for that date, it is
dropped and a warning is printed. So a typo or a wrong date can only make a
name disappear, never announce a wrong one.

Why not just read the whole dataset? It lists up to 88 names a day, including
nicknames shared by several saints ("Δώρα", "Νίκη", "Ντίνα"...). Matching those
produced false announcements in the old version (e.g. "Δώρα" on 4 February).

TO ADD A NAME: put it under the right (month, day) in FIXED, then run
    python scripts/namedays.py --check
which prints anything the dataset does not confirm.

Moveable feasts (Easter-based: Λάζαρος, Βάιος, Τάσος, Γιώργος when Easter is
late, Θωμάς...) are computed each year in MOVEABLE.

The digest goes out twice a week, so each edition covers the days until the
next one: Monday → Mon–Wed, Thursday → Thu–Sun.
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

_DATA_PATH = Path(__file__).parent / "namedays_data.json"
with open(_DATA_PATH, encoding="utf-8") as _f:
    _DATASET: dict[str, dict] = json.load(_f)

# (month, day): names as spoken. Keep it to names people really have.
FIXED: dict[tuple[int, int], list[str]] = {
    # Ιανουάριος
    (1, 1): ["Βασίλης", "Βασιλική"],
    (1, 2): ["Σεραφείμ"],
    (1, 6): ["Φώτης", "Φωτεινή", "Θεοφάνης", "Ιορδάνης", "Ουρανία"],
    (1, 7): ["Γιάννης", "Γιάννα", "Πρόδρομος"],
    (1, 11): ["Θεοδόσης"],
    (1, 12): ["Τατιάνα"],
    (1, 17): ["Αντώνης", "Αντωνία"],
    (1, 18): ["Θανάσης", "Αθανασία", "Κύριλλος"],
    (1, 19): ["Μακάριος"],
    (1, 20): ["Ευθύμιος", "Ευθυμία"],
    (1, 21): ["Ευγένιος", "Μάξιμος", "Αγνή"],
    (1, 22): ["Τιμόθεος"],
    (1, 25): ["Γρηγόρης", "Γρηγορία"],
    # Φεβρουάριος
    (2, 1): ["Τρύφων"],
    (2, 3): ["Συμεών", "Σταμάτης", "Σταματία"],
    (2, 4): ["Ισίδωρος", "Ισιδώρα"],
    (2, 6): ["Φώτης"],
    (2, 10): ["Χαράλαμπος", "Χαραλαμπία", "Χαρίκλεια"],
    (2, 11): ["Βλάσης", "Θεοδώρα"],
    (2, 12): ["Μελέτιος"],
    (2, 14): ["Βαλεντίνος", "Βαλεντίνη"],
    (2, 17): ["Θεόδωρος"],
    (2, 18): ["Λέων"],
    (2, 23): ["Πολύκαρπος"],
    (2, 26): ["Φωτεινή", "Πορφύριος"],
    # Μάρτιος
    (3, 1): ["Ευδοκία"],
    (3, 4): ["Γεράσιμος"],
    (3, 9): ["Ηλιάνα", "Ξανθή", "Σμαράγδα"],
    (3, 17): ["Αλέξης"],
    (3, 19): ["Χρύσανθος", "Χρυσάνθη"],
    (3, 25): ["Βαγγέλης", "Ευαγγελία"],
    # Απρίλιος
    (4, 15): ["Λεωνίδας"],
    (4, 21): ["Αλεξάνδρα"],
    (4, 24): ["Ελισάβετ"],
    (4, 30): ["Ιάκωβος"],
    # Μάιος
    (5, 5): ["Ειρήνη"],
    (5, 8): ["Θεολόγος", "Αρσένιος"],
    (5, 11): ["Μεθόδιος", "Αργύρης", "Ολυμπία"],
    (5, 15): ["Αχιλλέας"],
    (5, 21): ["Κωνσταντίνος", "Κωνσταντίνα", "Ελένη"],
    # Ιούνιος
    (6, 8): ["Καλλιόπη"],
    (6, 11): ["Βαρθολομαίος", "Βαρνάβας"],
    (6, 29): ["Πέτρος", "Παύλος"],
    (6, 30): ["Απόστολος", "Αποστολία"],
    # Ιούλιος
    (7, 1): ["Κοσμάς", "Δαμιανός", "Ανάργυρος"],
    (7, 7): ["Κυριακή"],
    (7, 8): ["Προκόπης", "Θεόφιλος"],
    (7, 11): ["Όλγα", "Ευφημία"],
    (7, 17): ["Μαρίνα"],
    (7, 20): ["Ηλίας"],
    (7, 22): ["Μαγδαληνή"],
    (7, 24): ["Χριστίνα"],
    (7, 25): ["Άννα"],
    (7, 26): ["Παρασκευή", "Παρασκευάς"],
    (7, 27): ["Παντελής"],
    (7, 28): ["Ειρήνη"],
    # Αύγουστος
    (8, 6): ["Σωτήρης", "Σωτηρία"],
    (8, 15): ["Μαρία", "Παναγιώτης", "Παναγιώτα", "Δέσποινα"],
    (8, 16): ["Γεράσιμος"],
    (8, 30): ["Αλέξανδρος", "Αλεξάνδρα"],
    # Σεπτέμβριος
    (9, 5): ["Ζαχαρίας"],
    (9, 8): ["Δέσποινα"],
    (9, 14): ["Σταύρος", "Σταυρούλα"],
    (9, 17): ["Σοφία", "Ελπίδα", "Αγάπη", "Πίστη"],
    (9, 20): ["Ευστάθιος"],
    (9, 24): ["Θέκλα", "Μυρτώ"],
    # Οκτώβριος
    (10, 3): ["Διονύσης", "Διονυσία"],
    (10, 6): ["Θωμάς"],
    (10, 18): ["Λουκάς"],
    (10, 19): ["Κλεοπάτρα"],
    (10, 20): ["Γεράσιμος", "Άρτεμις"],
    (10, 23): ["Ιάκωβος"],
    (10, 26): ["Δημήτρης", "Δήμητρα"],
    # Νοέμβριος
    (11, 1): ["Κοσμάς", "Δαμιανός", "Ανάργυρος"],
    (11, 8): ["Μιχάλης", "Γαβριήλ", "Άγγελος", "Αγγελική", "Ταξιάρχης"],
    (11, 9): ["Νεκτάριος", "Νεκταρία"],
    (11, 11): ["Μηνάς", "Βίκτωρας", "Βικτωρία"],
    (11, 13): ["Χρυσόστομος"],
    (11, 14): ["Φίλιππος"],
    (11, 16): ["Ματθαίος"],
    (11, 21): ["Μαρία", "Δέσποινα"],
    (11, 25): ["Κατερίνα", "Μερκούριος"],
    (11, 26): ["Στέλιος", "Στέλλα"],
    (11, 30): ["Ανδρέας", "Ανδριάνα"],
    # Δεκέμβριος
    (12, 4): ["Βαρβάρα"],
    (12, 5): ["Σάββας"],
    (12, 6): ["Νίκος", "Νικολέτα"],
    (12, 9): ["Άννα"],
    (12, 12): ["Σπύρος", "Σπυριδούλα"],
    (12, 13): ["Ευστράτιος", "Λουκία"],
    (12, 15): ["Λευτέρης", "Ελευθερία"],
    (12, 17): ["Διονύσης", "Δανιήλ"],
    (12, 20): ["Ιγνάτιος"],
    (12, 21): ["Ιουλία", "Θεμιστοκλής"],
    (12, 22): ["Αναστασία"],
    (12, 25): ["Χρήστος", "Χριστίνα", "Μανώλης", "Εμμανουέλα"],
    (12, 26): ["Ιωσήφ"],
    (12, 27): ["Στέφανος", "Στεφανία"],
}

# Corrections from the listener's own calendar. Always used, never checked.
USER_OVERRIDES: dict[tuple[int, int], list[str]] = {
    (6, 20): ["Έκτορας"],
    (6, 24): ["Ερρίκος"],
}

# Moveable feasts: days from Orthodox Easter Sunday → names.
MOVEABLE: dict[int, list[str]] = {
    -43: ["Θεόδωρος"],  # Σάββατο του Αγίου Θεοδώρου
    -8: ["Λάζαρος"],  # Σάββατο του Λαζάρου
    -7: ["Βάιος", "Βάια"],  # Κυριακή των Βαΐων
    0: ["Τάσος", "Αναστασία", "Ανέστης", "Λάμπρος", "Λαμπρινή"],  # Πάσχα
    2: ["Ραφαήλ"],  # Τρίτη του Πάσχα
    5: ["Ζωή"],  # Ζωοδόχου Πηγής
    7: ["Θωμάς"],  # Κυριακή του Θωμά
    50: ["Τριαντάφυλλος", "Τριανταφυλλιά"],  # Αγίου Πνεύματος
}

GREEK_DAYS = ["Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο", "Κυριακή"]
# Same day names with the article, as used in a sentence ("την Τρίτη").
GREEK_DAYS_ARTICLE = [
    "τη Δευτέρα",
    "την Τρίτη",
    "την Τετάρτη",
    "την Πέμπτη",
    "την Παρασκευή",
    "το Σάββατο",
    "την Κυριακή",
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


def orthodox_easter(year: int) -> date:
    """Orthodox Easter Sunday (Gregorian date), valid 1900–2099."""
    a, b, c = year % 4, year % 7, year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = (d + e + 114) % 31 + 1
    return date(year, month, day) + timedelta(days=13)


def _moveable(year: int) -> dict[date, list[str]]:
    easter = orthodox_easter(year)
    result: dict[date, list[str]] = {}
    for offset, names in MOVEABLE.items():
        result.setdefault(easter + timedelta(days=offset), []).extend(names)

    # Άγιος Γεώργιος (23/4) and Άγιος Μάρκος (25/4) move to Easter Monday /
    # Tuesday when Easter falls on or after 23 April.
    george = date(year, 4, 23)
    if easter >= george:
        result.setdefault(easter + timedelta(days=1), []).extend(["Γιώργος", "Γεωργία"])
        result.setdefault(easter + timedelta(days=2), []).append("Μάρκος")
    else:
        result.setdefault(george, []).extend(["Γιώργος", "Γεωργία"])
        result.setdefault(date(year, 4, 25), []).append("Μάρκος")
    return result


def _confirmed(month: int, day: int, names: list[str]) -> list[str]:
    """Keep only names the dataset lists for that date."""
    listed = set(_DATASET.get(f"{day}/{month}", {}).get("names", []))
    return [n for n in names if n in listed]


def names_for(d: date) -> list[str]:
    """Everyday names celebrating on date d (deduplicated, in order)."""
    names = _confirmed(d.month, d.day, FIXED.get((d.month, d.day), []))
    names += _moveable(d.year).get(d, [])
    names += USER_OVERRIDES.get((d.month, d.day), [])
    return list(dict.fromkeys(names))


def edition_days(today: date) -> int:
    """How many days this edition covers: until the next edition."""
    return {0: 3, 3: 4}.get(today.weekday(), 4)  # Mon→Mon-Wed, Thu→Thu-Sun


def get_edition_namedays(today: date) -> list[dict]:
    """Name days from today until the next edition.

    Each entry: {"date": "Δευτέρα 23 Νοεμβρίου", "name": "Κατερίνα, ...",
                 "names": [...], "when": "σήμερα" | "την Τρίτη 24 Νοεμβρίου"}
    """
    result = []
    for i in range(edition_days(today)):
        d = today + timedelta(days=i)
        names = names_for(d)
        if not names:
            continue
        date_str = f"{GREEK_DAYS[d.weekday()]} {d.day} {GREEK_MONTHS[d.month]}"
        when = (
            "σήμερα"
            if i == 0
            else f"{GREEK_DAYS_ARTICLE[d.weekday()]} {d.day} {GREEK_MONTHS[d.month]}"
        )
        result.append(
            {"date": date_str, "name": ", ".join(names), "names": names, "when": when}
        )
    return result


def _with_article(name: str) -> str:
    """'η Ειρήνη', 'ο Γιώργος'. Greek women's names end in a vowel."""
    female = name[-1] in "αάηήωώιίεέοόυύ" or name in ("Ελισάβετ", "Άρτεμις")
    return ("η " if female else "ο ") + name


def _join(names: list[str]) -> str:
    named = [_with_article(n) for n in names]
    return named[0] if len(named) == 1 else ", ".join(named[:-1]) + " και " + named[-1]


def spoken_text(entries: list[dict]) -> str:
    """The exact sentence(s) read out in the podcast. Empty if no name days."""
    if not entries:
        return ""
    lines = []
    for e in entries:
        when = e["when"][0].upper() + e["when"][1:]
        verb = "γιορτάζει" if len(e["names"]) == 1 else "γιορτάζουν"
        lines.append(f"{when} {verb} {_join(e['names'])}.")
    lines.append("Χρόνια πολλά σε όλους!")
    return " ".join(lines)


def check() -> int:
    """Print every FIXED name the dataset does not confirm. Returns count."""
    problems = 0
    for (m, d), names in sorted(FIXED.items()):
        for n in names:
            if n not in _confirmed(m, d, [n]):
                print(f"NOT CONFIRMED: {d}/{m} {n}")
                problems += 1
    print("All names confirmed." if not problems else f"{problems} name(s) will be skipped.")
    return problems


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(1 if check() else 0)
    entries = get_edition_namedays(date.today())
    for e in entries:
        print(f"{e['date']}: {e['name']}")
    print()
    print(spoken_text(entries))

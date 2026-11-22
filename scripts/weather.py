#!/usr/bin/env python3
"""
Weather forecast for the podcast and the page.

Uses Open-Meteo (open-meteo.com): free, no account or API key needed.
The town is set in config.yaml under `weather:`.

Covers the same days as the name days: from today until the next edition
(Monday → Mon–Wed, Thursday → Thu–Sun).

If the forecast can't be fetched for any reason, the weather section is
simply left out. It never stops the digest from being made.
"""

import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from namedays import GREEK_DAYS, GREEK_DAYS_ARTICLE, edition_days  # noqa: E402

API_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes (what Open-Meteo returns) → (said in Greek, emoji).
# The Greek fits "θα έχουμε ___".
CODES: dict[int, tuple[str, str]] = {
    0: ("λιακάδα", "☀️"),
    1: ("κυρίως λιακάδα", "🌤️"),
    2: ("λίγα σύννεφα", "⛅"),
    3: ("συννεφιά", "☁️"),
    45: ("ομίχλη", "🌫️"),
    48: ("ομίχλη", "🌫️"),
    51: ("ψιχάλες", "🌦️"),
    53: ("ψιχάλες", "🌦️"),
    55: ("ψιχάλες", "🌦️"),
    56: ("παγωμένες ψιχάλες", "🌧️"),
    57: ("παγωμένες ψιχάλες", "🌧️"),
    61: ("λίγη βροχή", "🌧️"),
    63: ("βροχή", "🌧️"),
    65: ("δυνατή βροχή", "🌧️"),
    66: ("παγωμένη βροχή", "🌧️"),
    67: ("παγωμένη βροχή", "🌧️"),
    71: ("λίγο χιόνι", "🌨️"),
    73: ("χιόνι", "🌨️"),
    75: ("πυκνό χιόνι", "❄️"),
    77: ("χιόνι", "🌨️"),
    80: ("μπόρες", "🌦️"),
    81: ("μπόρες", "🌦️"),
    82: ("δυνατές μπόρες", "⛈️"),
    85: ("χιονόνερο", "🌨️"),
    86: ("χιονόνερο", "🌨️"),
    95: ("καταιγίδες", "⛈️"),
    96: ("καταιγίδες με χαλάζι", "⛈️"),
    99: ("καταιγίδες με χαλάζι", "⛈️"),
}

# Codes where an umbrella tip makes sense (rain, showers, storms).
_RAINY = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}


def _fetch(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "timezone": "Europe/Athens",
        "forecast_days": 7,
    }
    last_error = None
    for attempt in range(2):  # one retry, after a short pause
        if attempt:
            time.sleep(5)
        try:
            r = requests.get(API_URL, params=params, timeout=15)
            r.raise_for_status()
            return r.json()["daily"]
        except Exception as e:  # network, bad JSON, missing field...
            last_error = e
    raise RuntimeError(f"weather fetch failed: {last_error}")


def get_edition_weather(today: date, cfg: dict) -> dict | None:
    """Forecast for this edition's days, or None if unavailable/disabled.

    Returns {"place": "στην Αθήνα", "days": [{"date", "when", "label",
             "desc", "emoji", "min", "max", "rainy"}, ...]}
    """
    if not cfg or not cfg.get("enabled"):
        return None
    try:
        daily = _fetch(cfg["latitude"], cfg["longitude"])
        by_date = {
            d: (code, tmin, tmax)
            for d, code, tmin, tmax in zip(
                daily["time"],
                daily["weather_code"],
                daily["temperature_2m_min"],
                daily["temperature_2m_max"],
            )
        }
        days = []
        for i in range(edition_days(today)):
            d = today + timedelta(days=i)
            if d.isoformat() not in by_date:
                continue
            code, tmin, tmax = by_date[d.isoformat()]
            if code is None or tmin is None or tmax is None:
                continue
            desc, emoji = CODES.get(int(code), ("μεταβλητός καιρός", "🌡️"))
            days.append(
                {
                    "date": d.isoformat(),
                    "when": "σήμερα" if i == 0 else GREEK_DAYS_ARTICLE[d.weekday()],
                    "label": "Σήμερα" if i == 0 else GREEK_DAYS[d.weekday()],
                    "desc": desc,
                    "emoji": emoji,
                    "min": round(tmin),
                    "max": round(tmax),
                    "rainy": int(code) in _RAINY,
                }
            )
        if not days:
            return None
        return {"place": cfg.get("place", ""), "days": days}
    except Exception as e:
        print(f"WARNING: no weather this time ({e})")
        return None


def _degrees(n: int) -> str:
    """Temperature as it should be read aloud."""
    return f"μείον {abs(n)}" if n < 0 else str(n)


def spoken_text(weather: dict | None) -> str:
    """The exact sentences read out in the podcast. Empty if no weather."""
    if not weather or not weather.get("days"):
        return ""
    parts = [f"Και πριν φύγουμε, ο καιρός {weather['place']}.".replace("  ", " ")]
    for i, d in enumerate(weather["days"]):
        when = d["when"][0].upper() + d["when"][1:]
        unit = "βαθμό" if d["max"] in (1, -1) else "βαθμούς"
        span = f"από {_degrees(d['min'])} έως {_degrees(d['max'])} {unit}"
        if i == 0:
            parts.append(f"{when} θα έχουμε {d['desc']}, με θερμοκρασία {span}.")
        else:
            parts.append(f"{when}, {d['desc']}, {span}.")
    if any(d["rainy"] for d in weather["days"]):
        parts.append("Αν βγείτε, μην ξεχάσετε την ομπρέλα σας!")
    return " ".join(parts)


if __name__ == "__main__":
    with open(Path(__file__).parent.parent / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f).get("weather", {})
    w = get_edition_weather(date.today(), cfg)
    print(w)
    print(spoken_text(w))

#!/usr/bin/env python3
import json
import sys
import yaml
import os
import anthropic
from datetime import datetime, timedelta
from pathlib import Path

JOKE_TOPICS = [
    "οικογένεια",
    "παιδιά",
    "φαγητό",
    "ζώα",
    "δουλειά",
    "σχολείο",
    "γιατρός",
    "τεχνολογία",
    "ταξίδια",
    "αγορές",
    "μαγείρεμα",
    "γείτονες",
    "καιρός",
    "μουσική",
    "κινηματογράφος",
    "διακοπές",
    "συνταξιούχοι",
]

sys.path.insert(0, str(Path(__file__).parent))


SYSTEM_PROMPT = """Είσαι επιμελητής ειδήσεων που επιλέγει αποκλειστικά θετικές, εμπνευστικές ή ενδιαφέρουσες ειδήσεις.

Γράφεις στα ΕΛΛΗΝΙΚΑ. Η τελική έξοδος είναι ελληνικό κείμενο για ελληνικό κοινό."""

CURATION_PROMPT = """Έχεις τις παρακάτω ειδήσεις της εβδομάδας. Επίλεξε τις καλύτερες θετικές/ενδιαφέρουσες.

## ΚΑΝΟΝΕΣ ΕΠΙΛΟΓΗΣ
- ΑΠΟΚΛΕΙΣΕ: θανάτους, πόλεμο, εγκλήματα, διαφθορά, σκάνδαλα, φυσικές καταστροφές, οικονομικές κρίσεις, ατυχήματα, ΑΘΛΗΤΙΣΜΟ (ποδόσφαιρο, μπάσκετ, πρωταθλήματα, αγώνες, σκορ, μεταγραφές)
- ΚΡΑΤΑ: επιτεύγματα, καινοτομίες, επιστήμη, πολιτισμό, περιβαλλοντικές επιτυχίες, ανθρώπινες ιστορίες, τουρισμό, τέχνη, εκπαίδευση, υγεία, τεχνολογία

## ΕΛΛΗΝΙΚΕΣ ΕΙΔΗΣΕΙΣ (επίλεξε {greek_n} ειδήσεις):
{greek_items}

## ΔΙΕΘΝΕΙΣ ΘΕΤΙΚΕΣ ΕΙΔΗΣΕΙΣ (επίλεξε {world_n} ειδήσεις):
{world_items}

## ΤΡΕΧΟΥΣΑ ΕΒΔΟΜΑΔΑ: {week_start} — {week_end}

## ΕΞΟΔΟΣ
Επίστρεψε ΜΟΝΟ έγκυρο JSON (χωρίς markdown):

{{
  "weekly_intro": "2-3 προτάσεις εισαγωγής που συνοψίζουν τα θέματα της εβδομάδας",
  "namedays": [
    {{"name": "Ελληνικό όνομα", "date": "π.χ. Δευτέρα 2 Ιουνίου"}}
  ],
  "joke": "Αστείο με θέμα: {joke_topic}. Πρέπει να είναι ΠΡΑΓΜΑΤΙΚΑ αστείο — με σαφή pointe, λογική αλληλουχία και απρόσμενη κατάληξη. Όχι παιδικά αστεία. Στυλ: έξυπνο χιούμορ, ανεκδοτάκι με ανατροπή. Χωρίς αναφορές σε θάνατο, αρρώστια ή προσβολές.",
  "greek_news": [
    {{
      "title": "τίτλος στα ελληνικά",
      "summary": "2-3 προτάσεις σύνοψης (max 200 χαρακτήρες)",
      "url": "url της πηγής",
      "source": "όνομα πηγής",
      "category": "μία από: Επιστήμη|Πολιτισμός|Περιβάλλον|Τεχνολογία|Κοινωνία|Οικονομία|Τουρισμός|Εκπαίδευση|Υγεία"
    }}
  ],
  "world_news": [
    {{
      "title": "τίτλος στα ελληνικά",
      "summary": "2-3 προτάσεις σύνοψης (max 200 χαρακτήρες)",
      "url": "url της πηγής",
      "source": "όνομα πηγής",
      "category": "μία από: Επιστήμη|Τεχνολογία|Περιβάλλον|Υγεία|Κοινωνία|Καινοτομία|Τέχνη"
    }}
  ]
}}"""


class ContentCurator:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        with open(self.base_dir / "config.yaml") as f:
            self.config = yaml.safe_load(f)
        self.data_dir = self.base_dir / "data"
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def get_latest_raw(self):
        files = sorted(self.data_dir.glob("raw_news_*.json"), reverse=True)
        if not files:
            raise FileNotFoundError(
                "No raw news files found. Run collect_news.py first."
            )
        return files[0]

    def _format_items(self, items):
        lines = []
        for i, item in enumerate(items, 1):
            lines.append(
                f"{i}. [{item['source']}] {item['title']}\n"
                f"   {item.get('summary', '')[:200]}\n"
                f"   URL: {item['url']}"
            )
        return "\n\n".join(lines)

    def curate(self):

        raw_path = self.get_latest_raw()
        with open(raw_path, encoding="utf-8") as f:
            raw = json.load(f)

        greek_items = raw.get("greek_news", [])
        world_items = raw.get("world_positive_news", [])
        print(f"Curating {len(greek_items)} Greek + {len(world_items)} world items...")

        now = datetime.now()
        # Week starts on Monday
        monday = now - timedelta(days=now.weekday())
        sunday = monday + timedelta(days=6)
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
        week_start = f"{monday.day} {GREEK_MONTHS[monday.month]}"
        week_end = f"{sunday.day} {GREEK_MONTHS[sunday.month]} {sunday.year}"

        import random

        cfg = self.config["curation"]
        prompt = CURATION_PROMPT.format(
            greek_n=cfg["greek_section_items"],
            world_n=cfg["world_section_items"],
            greek_items=self._format_items(greek_items),
            world_items=self._format_items(world_items),
            week_start=week_start,
            week_end=week_end,
            joke_topic=random.choice(JOKE_TOPICS),
        )

        response = self.client.messages.create(
            model=cfg["model"],
            max_tokens=cfg["max_tokens"],
            temperature=cfg.get("temperature", 0.3),
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = response.content[0].text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        curated = json.loads(raw_text.strip())

        # Replace Claude-generated namedays with calendar-sourced ones
        import importlib.util as _ilu

        _spec = _ilu.spec_from_file_location(
            "namedays", Path(__file__).parent / "namedays.py"
        )
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        curated["namedays"] = _mod.get_week_namedays(monday)

        date_str = datetime.now().strftime("%Y%m%d")
        out_path = self.data_dir / f"curated_{date_str}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(curated, f, ensure_ascii=False, indent=2)

        print(
            f"Curated: {len(curated['greek_news'])} Greek, {len(curated['world_news'])} world"
        )
        print(f"Namedays: {[n['name'] for n in curated.get('namedays', [])]}")
        print(f"Saved to {out_path}")
        return out_path


if __name__ == "__main__":
    curator = ContentCurator()
    curator.curate()

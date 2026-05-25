#!/usr/bin/env python3
"""
Generates Greek narration using OpenAI TTS (tts-1-hd, nova voice).
OpenAI's TTS is multilingual — passing Greek text produces Greek speech.
"""

import json
import yaml
import os
import anthropic
from openai import OpenAI
from pathlib import Path


SCRIPT_PROMPT = """Είσαι παρουσιαστής του podcast «Τα νέα στα ελληνικά!». Γράψε ένα ακουστικό σενάριο στα ελληνικά, διάρκειας ακριβώς 7 λεπτών (περίπου 900-1000 λέξεις σε φυσικό ρυθμό ομιλίας).

Στυλ: ζεστό, φιλικό, ενθαρρυντικό — σαν να μιλάς σε παρέα. Χωρίς bullet points, μόνο συνεχές, ρέον κείμενο. Χρησιμοποίησε φυσικές συνδετικές φράσεις και μεταβάσεις μεταξύ θεμάτων.

Δομή (7 λεπτά συνολικά):
1. Εισαγωγή (~30 δευτ.): Χαιρετισμός, τίτλος podcast, σύντομη περίληψη της εβδομάδας
2. Ελληνικά νέα (~3 λεπτά): Παρουσίασε ΟΛΑ τα ελληνικά highlights με λεπτομέρεια — επεξήγησε γιατί είναι σημαντικά, ποια η επίδρασή τους
3. Διεθνή θετικά νέα (~3 λεπτά): Παρουσίασε ΟΛΑ τα διεθνή highlights με πλαίσιο και σημασία για τον ακροατή
4. Αποχαιρετισμός (~30 δευτ.): Σύνοψη, αισιόδοξο κλείσιμο, «Καλή εβδομάδα!»

ΔΕΔΟΜΕΝΑ:
{data}

Επίστρεψε ΜΟΝΟ το κείμενο του σεναρίου, χωρίς τίτλους ή ετικέτες. Στόχος: ακριβώς 7 λεπτά."""


class AudioGenerator:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        with open(self.base_dir / "config.yaml") as f:
            self.config = yaml.safe_load(f)
        self.data_dir = self.base_dir / "data"
        self.audio_dir = self.base_dir / "audio"
        self.audio_dir.mkdir(exist_ok=True)
        self.claude = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def get_latest_curated(self):
        files = sorted(self.data_dir.glob("curated_*.json"), reverse=True)
        if not files:
            raise FileNotFoundError(
                "No curated files found. Run curate_content.py first."
            )
        return files[0]

    def _build_summary(self, curated):
        lines = [f"Εισαγωγή: {curated.get('weekly_intro', '')}", "", "ΕΛΛΗΝΙΚΑ ΝΕΑ:"]
        for item in curated.get("greek_news", []):
            lines.append(f"- {item['title']}: {item.get('summary', '')}")
        lines.append("\nΔΙΕΘΝΗ ΘΕΤΙΚΑ ΝΕΑ:")
        for item in curated.get("world_news", []):
            lines.append(f"- {item['title']}: {item.get('summary', '')}")
        return "\n".join(lines)

    def generate(self):
        curated_path = self.get_latest_curated()
        date_str = curated_path.stem.split("_")[1]
        with open(curated_path, encoding="utf-8") as f:
            curated = json.load(f)

        print("Generating Greek narration script with Claude...")
        summary = self._build_summary(curated)
        response = self.claude.messages.create(
            model=self.config["curation"]["model"],
            max_tokens=2048,
            messages=[{"role": "user", "content": SCRIPT_PROMPT.format(data=summary)}],
        )
        script = response.content[0].text.strip()

        script_path = self.audio_dir / f"script_{date_str}.txt"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)

        print("Generating audio with OpenAI TTS (Greek)...")
        cfg = self.config["audio"]
        tts_response = self.openai.audio.speech.create(
            model=cfg["model"],
            voice=cfg["voice"],
            input=script,
        )

        audio_path = self.audio_dir / f"narration_{date_str}.mp3"
        tts_response.stream_to_file(str(audio_path))
        print(f"Audio saved to {audio_path}")
        return audio_path


if __name__ == "__main__":
    gen = AudioGenerator()
    gen.generate()

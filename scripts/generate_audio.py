#!/usr/bin/env python3
"""
Generates Greek narration using OpenAI TTS (tts-1-hd, nova voice).
OpenAI TTS limit is 4096 chars per call — long scripts are split at sentence
boundaries and the MP3 chunks are concatenated as raw bytes (same CBR bitrate).
"""

import json
import re
import yaml
import os
import anthropic
from openai import OpenAI
from pathlib import Path


SCRIPT_PROMPT = """Είσαι η Βερόνικα, παρουσιάστρια του podcast «Τα νέα στα ελληνικά!».
Γράψε ένα σενάριο διάρκειας 7 λεπτών (περίπου 900-1000 λέξεις).

Το σενάριο ξεκινά ΑΚΡΙΒΩΣ έτσι, χωρίς καμία αλλαγή:
«Γεια σας, είμαι η Βερόνικα και αυτά είναι τα νέα στα ελληνικά.»

Μετά από αυτήν την πρώτη φράση, πήγαινε ΑΜΕΣΩΣ στην πρώτη είδηση — χωρίς περίληψη εβδομάδας, χωρίς εισαγωγή, χωρίς «σήμερα θα μιλήσουμε για».

Στυλ: ζεστό, φυσικό, σαν να μιλάς σε φίλο. Συνεχές κείμενο, φυσικές μεταβάσεις μεταξύ ειδήσεων.

Δομή:
- Χαιρετισμός (μία φράση μόνο)
- Ελληνικά νέα (~3,5 λεπτά): ΟΛΑ τα ελληνικά, με πλαίσιο και σημασία
- Διεθνή θετικά νέα (~3 λεπτά): ΟΛΑ τα διεθνή, με πλαίσιο
- Κλείσιμο (~15 δευτ.): «Καλή εβδομάδα!»

ΔΕΔΟΜΕΝΑ:
{data}

Επίστρεψε ΜΟΝΟ το κείμενο. Χωρίς τίτλους, ετικέτες ή παρενθέσεις."""

TTS_LIMIT = 4000  # chars — stay under OpenAI's 4096 hard limit


def split_into_chunks(text: str, limit: int = TTS_LIMIT) -> list[str]:
    """Split at sentence boundaries so no chunk exceeds limit chars."""
    sentences = re.split(r"(?<=[.!;])\s+", text)
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= limit:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            # sentence itself longer than limit — hard split at word boundary
            if len(sentence) > limit:
                words = sentence.split()
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= limit:
                        current = (current + " " + word).strip()
                    else:
                        chunks.append(current)
                        current = word
            else:
                current = sentence
    if current:
        chunks.append(current)
    return chunks


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
        lines = ["ΕΛΛΗΝΙΚΑ ΝΕΑ:"]
        for item in curated.get("greek_news", []):
            lines.append(f"- {item['title']}: {item.get('summary', '')}")
        lines.append("\nΔΙΕΘΝΗ ΘΕΤΙΚΑ ΝΕΑ:")
        for item in curated.get("world_news", []):
            lines.append(f"- {item['title']}: {item.get('summary', '')}")
        return "\n".join(lines)

    def _tts_chunk(self, text: str, cfg: dict) -> bytes:
        response = self.openai.audio.speech.create(
            model=cfg["model"],
            voice=cfg["voice"],
            input=text,
        )
        return response.read()

    def generate(self):
        curated_path = self.get_latest_curated()
        date_str = curated_path.stem.split("_")[1]
        with open(curated_path, encoding="utf-8") as f:
            curated = json.load(f)

        print("Generating narration script with Claude...")
        summary = self._build_summary(curated)
        response = self.claude.messages.create(
            model=self.config["curation"]["model"],
            max_tokens=3000,
            messages=[{"role": "user", "content": SCRIPT_PROMPT.format(data=summary)}],
        )
        script = response.content[0].text.strip()
        print(f"Script: {len(script)} chars, ~{len(script.split())} words")

        script_path = self.audio_dir / f"script_{date_str}.txt"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)

        chunks = split_into_chunks(script)
        print(f"TTS: {len(chunks)} chunk(s) — {[len(c) for c in chunks]} chars each")

        cfg = self.config["audio"]
        mp3_bytes = b""
        for i, chunk in enumerate(chunks, 1):
            print(f"  Chunk {i}/{len(chunks)}...")
            mp3_bytes += self._tts_chunk(chunk, cfg)

        audio_path = self.audio_dir / f"narration_{date_str}.mp3"
        audio_path.write_bytes(mp3_bytes)
        print(f"Audio saved to {audio_path}")
        return audio_path


if __name__ == "__main__":
    gen = AudioGenerator()
    gen.generate()

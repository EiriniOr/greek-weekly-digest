#!/usr/bin/env python3
"""
Generates Greek narration using OpenAI TTS (tts-1-hd, nova voice).
OpenAI TTS hard limit is 4096 chars per call. Script is split at sentence
boundaries into chunks, each converted separately, then concatenated as raw
MP3 bytes (safe for CBR streams from the same encoder/bitrate).
"""

import json
import re
import yaml
import os
import anthropic
from openai import OpenAI
from pathlib import Path

SCRIPT_PROMPT = """Είσαι η Βερόνικα, παρουσιάστρια του podcast «Τα νέα στα ελληνικά!».
Γράψε ένα σενάριο διάρκειας ΑΚΡΙΒΩΣ 5 λεπτών (600-650 λέξεις — μην ξεπεράσεις τις 650).

Το σενάριο ξεκινά ΑΚΡΙΒΩΣ με αυτή τη φράση, χωρίς καμία αλλαγή:
Γεια σας, είμαι η Βερόνικα και αυτά είναι τα νέα στα ελληνικά.

Μετά πήγαινε ΑΜΕΣΩΣ στην πρώτη είδηση — χωρίς εισαγωγή, χωρίς «σήμερα θα μιλήσουμε για», χωρίς περίληψη.

Στυλ: ζεστό, φυσικό, σαν συνομιλία. Συνεχές κείμενο, φυσικές μεταβάσεις.

Δομή:
- Χαιρετισμός (μία φράση)
- Ελληνικά νέα (~2,5 λεπτά): τα σημαντικότερα, με πλαίσιο
- Διεθνή θετικά νέα (~2 λεπτά): τα σημαντικότερα, με πλαίσιο
- Κλείσιμο (μία φράση): «Καλή εβδομάδα!»

ΔΕΔΟΜΕΝΑ:
{data}

Επίστρεψε ΜΟΝΟ το κείμενο. Χωρίς τίτλους, ετικέτες ή σχόλια. Μέγιστο 650 λέξεις."""

# Stay comfortably under OpenAI's 4096-char hard limit
TTS_LIMIT = 3800


def split_into_chunks(text: str, limit: int = TTS_LIMIT) -> list[str]:
    """Split at sentence boundaries so no chunk exceeds limit chars."""
    sentences = re.split(r"(?<=[.!?;])\s+", text)
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= limit:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            if len(sentence) > limit:
                # sentence itself too long — split at word boundary
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

    def _tts(self, text: str, cfg: dict) -> bytes:
        tmp = self.audio_dir / "_chunk_tmp.mp3"
        resp = self.openai.audio.speech.create(
            model=cfg["model"],
            voice=cfg["voice"],
            input=text,
        )
        resp.stream_to_file(str(tmp))
        data = tmp.read_bytes()
        tmp.unlink(missing_ok=True)
        return data

    def generate(self):
        curated_path = self.get_latest_curated()
        date_str = curated_path.stem.split("_")[1]
        with open(curated_path, encoding="utf-8") as f:
            curated = json.load(f)

        print("Generating narration script with Claude...")
        response = self.claude.messages.create(
            model=self.config["curation"]["model"],
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": SCRIPT_PROMPT.format(data=self._build_summary(curated)),
                }
            ],
        )
        script = response.content[0].text.strip()
        word_count = len(script.split())
        print(f"Script: {len(script)} chars, {word_count} words")

        script_path = self.audio_dir / f"script_{date_str}.txt"
        script_path.write_text(script, encoding="utf-8")

        chunks = split_into_chunks(script)
        print(f"TTS: {len(chunks)} chunk(s), sizes: {[len(c) for c in chunks]}")

        cfg = self.config["audio"]
        mp3_bytes = b""
        for i, chunk in enumerate(chunks, 1):
            print(f"  Chunk {i}/{len(chunks)} ({len(chunk)} chars)...")
            mp3_bytes += self._tts(chunk, cfg)

        audio_path = self.audio_dir / f"narration_{date_str}.mp3"
        audio_path.write_bytes(mp3_bytes)
        print(f"Audio saved to {audio_path} ({len(mp3_bytes):,} bytes)")
        return audio_path


if __name__ == "__main__":
    gen = AudioGenerator()
    gen.generate()

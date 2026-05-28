#!/usr/bin/env python3
"""
Greek TTS via OpenAI tts-1-hd.

Approach to avoid mid-sentence cutoff:
- Split script at paragraph boundaries into chunks of ≤2000 chars each
  (well under the 4096-char API limit, with margin)
- Generate each chunk via with_streaming_response.create() → stream_to_file()
  (the only fully-reliable way to get complete MP3 bytes from OpenAI)
- Concatenate with ffmpeg (handles ID3 headers cleanly)
- Fall back to raw byte concat if ffmpeg is absent
"""

import json
import re
import subprocess
import yaml
import os
import anthropic
from openai import OpenAI
from pathlib import Path

SCRIPT_PROMPT = """Είσαι η Βερόνικα, παρουσιάστρια του podcast «Τα νέα στα ελληνικά!».

Γράψε ένα podcast σενάριο στα ελληνικά, περίπου 7 λεπτά (χωρίς αυστηρό όριο λέξεων).

Ξεκίνα ΑΚΡΙΒΩΣ με:
Γεια σας, είμαι η Βερόνικα και αυτά είναι τα νέα στα ελληνικά.

Μετά πήγαινε ΑΜΕΣΩΣ στις ονομαστικές εορτές και το αστείο — χωρίς εισαγωγή.

Δομή:
1. Χαιρετισμός (μία φράση)
2. Ονομαστικές εορτές (~20 δευτ.): «Αυτή την εβδομάδα γιορτάζουν οι...» — ανέφερε όλα τα ονόματα
3. Αστείο (~30 δευτ.): πες το αστείο φυσικά, σαν να το λες σε παρέα
4. Ελληνικά νέα (~3 λεπτά): τα 4-5 σημαντικότερα, με πλαίσιο και σημασία
5. Παγκόσμια θετικά νέα (~2,5 λεπτά): τα 4-5 σημαντικότερα, με πλαίσιο
6. Αποχαιρετισμός: «Καλή εβδομάδα σε όλους!»

Στυλ: ζεστό, φυσικό, σαν να μιλάς σε φίλο. Συνεχές κείμενο με φυσικές μεταβάσεις.
ΣΗΜΑΝΤΙΚΟ: χώρισε το κείμενο σε παραγράφους (κενή γραμμή μεταξύ τους).

ΔΕΔΟΜΕΝΑ:
{data}

Επίστρεψε ΜΟΝΟ το κείμενο του σεναρίου."""

CHUNK_LIMIT = 2000  # chars — well under the 4096 hard limit


def split_paragraphs(text: str, limit: int = CHUNK_LIMIT) -> list[str]:
    """Split at blank lines; merge short adjacent paragraphs; hard-split long ones."""
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks, current = [], ""
    for para in paras:
        if len(current) + len(para) + 2 <= limit:
            current = (current + "\n\n" + para).strip() if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > limit:
                # paragraph itself too long — split at sentence boundary
                sentences = re.split(r"(?<=[.!?])\s+", para)
                current = ""
                for s in sentences:
                    if len(current) + len(s) + 1 <= limit:
                        current = (current + " " + s).strip() if current else s
                    else:
                        if current:
                            chunks.append(current)
                        current = s
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks


def ffmpeg_concat(files: list[Path], output: Path) -> bool:
    """Concatenate MP3 files with ffmpeg. Returns True on success."""
    try:
        list_txt = output.parent / "_concat_list.txt"
        list_txt.write_text(
            "\n".join(f"file '{f.resolve()}'" for f in files), encoding="utf-8"
        )
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_txt),
                "-c",
                "copy",
                str(output),
            ],
            capture_output=True,
            timeout=120,
        )
        list_txt.unlink(missing_ok=True)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


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

    def _build_data(self, curated):
        lines = []
        namedays = curated.get("namedays", [])
        if namedays:
            lines.append("ΟΝΟΜΑΣΤΙΚΕΣ ΕΟΡΤΕΣ:")
            for n in namedays:
                lines.append(f"  {n['name']} — {n['date']}")
        joke = curated.get("joke", "")
        if joke:
            lines.append(f"\nΑΣΤΕΙΟ: {joke}")
        lines.append("\nΕΛΛΗΝΙΚΑ ΝΕΑ:")
        for item in curated.get("greek_news", []):
            lines.append(f"- {item['title']}: {item.get('summary', '')}")
        lines.append("\nΠΑΓΚΟΣΜΙΑ ΘΕΤΙΚΑ ΝΕΑ:")
        for item in curated.get("world_news", []):
            lines.append(f"- {item['title']}: {item.get('summary', '')}")
        return "\n".join(lines)

    def _tts_to_file(self, text: str, cfg: dict, path: Path) -> None:
        """Stream TTS directly to file — the only fully-reliable method."""
        with self.openai.audio.speech.with_streaming_response.create(
            model=cfg["model"],
            voice=cfg["voice"],
            input=text,
        ) as response:
            response.stream_to_file(str(path))

    def generate(self):
        curated_path = self.get_latest_curated()
        date_str = curated_path.stem.split("_")[1]
        with open(curated_path, encoding="utf-8") as f:
            curated = json.load(f)

        print("Generating narration script with Claude...")
        response = self.claude.messages.create(
            model=self.config["curation"]["model"],
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": SCRIPT_PROMPT.format(data=self._build_data(curated)),
                }
            ],
        )
        script = response.content[0].text.strip()
        print(f"Script: {len(script)} chars, {len(script.split())} words")

        script_path = self.audio_dir / f"script_{date_str}.txt"
        script_path.write_text(script, encoding="utf-8")

        chunks = split_paragraphs(script)
        print(f"Chunks: {len(chunks)}, sizes: {[len(c) for c in chunks]}")
        assert all(len(c) <= 4096 for c in chunks), "A chunk exceeds 4096 chars!"

        cfg = self.config["audio"]
        chunk_files = []
        for i, chunk in enumerate(chunks, 1):
            p = self.audio_dir / f"_chunk_{i:03d}.mp3"
            print(f"  TTS chunk {i}/{len(chunks)} ({len(chunk)} chars)...")
            self._tts_to_file(chunk, cfg, p)
            chunk_files.append(p)

        audio_path = self.audio_dir / f"narration_{date_str}.mp3"

        if len(chunk_files) == 1:
            chunk_files[0].rename(audio_path)
        else:
            print("Concatenating with ffmpeg...")
            ok = ffmpeg_concat(chunk_files, audio_path)
            if ok:
                for f in chunk_files:
                    f.unlink(missing_ok=True)
            else:
                print("ffmpeg not found — falling back to raw byte concat")
                audio_path.write_bytes(b"".join(f.read_bytes() for f in chunk_files))
                for f in chunk_files:
                    f.unlink(missing_ok=True)

        size = audio_path.stat().st_size
        print(
            f"Audio saved: {audio_path} ({size:,} bytes, ~{size // 16000 // 60}m{size // 16000 % 60}s at 128kbps)"
        )
        return audio_path


if __name__ == "__main__":
    gen = AudioGenerator()
    gen.generate()

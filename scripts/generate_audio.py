#!/usr/bin/env python3
"""
Greek TTS via OpenAI (model set in config.yaml).

How we make sure nothing gets cut off:
- The script is split into chunks of at most 1500 characters, at paragraph
  breaks (or, for a very long paragraph, at sentence and then word breaks).
  The voice model reads at most 2000 tokens per request, and 1500 characters
  stays under that even in the worst case.
- Each chunk is streamed straight to a file (stream_to_file), the reliable
  way to get the complete MP3 from OpenAI.
- Each chunk's length is measured. Real episodes are read at about 14
  characters per second; if a chunk comes out much faster than that, words
  are missing, so it is generated again.
- Chunks are joined with ffmpeg (raw byte join if ffmpeg is missing).
"""

import json
import re
import subprocess
import yaml
import os
import anthropic
from openai import OpenAI
from pathlib import Path

import namedays
import weather

SCRIPT_PROMPT = """Είσαι η Βερόνικα, παρουσιάστρια του podcast «Τα νέα της μαμάς».

Γράψε ένα podcast σενάριο στα ελληνικά, περίπου 7 λεπτά συνολικά (χωρίς αυστηρό όριο λέξεων).

Ξεκίνα ΑΚΡΙΒΩΣ με (χρησιμοποίησε την ΕΚΔΟΣΗ από τα δεδομένα):
Γεια σας, είμαι η Βερόνικα και αυτά είναι τα νέα της μαμάς της [Δευτέρας ή Πέμπτης].

Δομή:
1. Χαιρετισμός (μία φράση)
2. Ονομαστικές εορτές: ΜΟΝΟ αν τα δεδομένα περιέχουν τη γραμμή «ΓΙΟΡΤΕΣ: ΝΑΙ» — σε ΔΙΚΗ ΤΟΥ παράγραφο γράψε ΑΚΡΙΒΩΣ τον δείκτη [ΓΙΟΡΤΕΣ] και τίποτα άλλο. ΜΗΝ γράψεις εσύ ονόματα ή ημερομηνίες — το κείμενο θα εισαχθεί αυτόματα. Αν δεν υπάρχει «ΓΙΟΡΤΕΣ: ΝΑΙ», παράλειψε το βήμα.
3. Αστείο: ΜΟΝΟ αν τα δεδομένα περιέχουν τη γραμμή «ΑΣΤΕΙΟ: ΝΑΙ» — γράψε μια σύντομη φυσική εισαγωγή (π.χ. «Και τώρα, το ανέκδοτο της ημέρας!») και αμέσως μετά, σε ΔΙΚΗ ΤΟΥ παράγραφο, γράψε ΑΚΡΙΒΩΣ τον δείκτη [ΑΣΤΕΙΟ] και τίποτα άλλο. ΜΗΝ γράψεις εσύ αστείο — το κείμενο θα εισαχθεί αυτόματα. Αν δεν υπάρχει «ΑΣΤΕΙΟ: ΝΑΙ», παράλειψε το βήμα.
4. Ελληνικά νέα (~2,5 λεπτά): τα 4-5 σημαντικότερα, με πλαίσιο και σημασία
5. Παγκόσμια θετικά νέα (~2 λεπτά): τα 4-5 σημαντικότερα, με πλαίσιο
6. Καιρός: ΜΟΝΟ αν τα δεδομένα περιέχουν τη γραμμή «ΚΑΙΡΟΣ: ΝΑΙ» — σε ΔΙΚΗ ΤΟΥ παράγραφο γράψε ΑΚΡΙΒΩΣ τον δείκτη [ΚΑΙΡΟΣ] και τίποτα άλλο. ΜΗΝ γράψεις εσύ πρόγνωση ή θερμοκρασίες — το κείμενο θα εισαχθεί αυτόματα. Αν δεν υπάρχει «ΚΑΙΡΟΣ: ΝΑΙ», παράλειψε το βήμα.
7. Αποχαιρετισμός: σε ΔΙΚΗ ΤΟΥ παράγραφο, ακριβώς η φράση ΑΠΟΧΑΙΡΕΤΙΣΜΟΣ από τα δεδομένα.

Στυλ: ζεστό, φυσικό, σαν να μιλάς σε φίλο. Συνεχές κείμενο με φυσικές μεταβάσεις.
ΣΗΜΑΝΤΙΚΟ: χώρισε το κείμενο σε παραγράφους (κενή γραμμή μεταξύ τους).

ΔΕΔΟΜΕΝΑ:
{data}

Επίστρεψε ΜΟΝΟ το κείμενο του σεναρίου."""

# The voice model reads at most 2000 tokens per request. 1500 characters is
# under that even in the worst case (one token per character).
CHUNK_LIMIT = 1500

# Real episodes (Nov 2026) were read at 13.3–14.0 characters per second.
# A chunk "read" faster than this has lost words, so it is made again.
TOO_FAST_CHARS_PER_SEC = 18

# Where a long paragraph may be broken: after . ! ? ; (the Greek question
# mark) · … or a closing quote.
_SENTENCE_BREAK = re.compile(r"(?<=[.!?;;·…»])\s+")


def _pieces(paragraph: str, limit: int) -> list[str]:
    """Break one too-long paragraph into pieces of at most `limit` chars:
    at sentence ends first, and only if a sentence is still too long, at
    the last space that fits."""
    pieces = []
    for sentence in _SENTENCE_BREAK.split(paragraph):
        while len(sentence) > limit:
            cut = sentence.rfind(" ", 0, limit)
            if cut <= 0:
                cut = limit
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if sentence:
            pieces.append(sentence)
    return pieces


def split_paragraphs(text: str, limit: int = CHUNK_LIMIT) -> list[str]:
    """Pack the script into chunks of at most `limit` chars, breaking only
    between paragraphs unless a single paragraph is longer than `limit`."""
    units: list[tuple[str, str]] = []  # (text, joiner to put before it)
    for para in (p.strip() for p in re.split(r"\n{2,}", text)):
        if not para:
            continue
        if len(para) <= limit:
            units.append((para, "\n\n"))
        else:
            for j, piece in enumerate(_pieces(para, limit)):
                units.append((piece, "\n\n" if j == 0 else " "))

    chunks, current = [], ""
    for piece, joiner in units:
        if current and len(current) + len(joiner) + len(piece) <= limit:
            current += joiner + piece
        else:
            if current:
                chunks.append(current)
            current = piece
    if current:
        chunks.append(current)
    return chunks


def audio_seconds(path: Path) -> float | None:
    """Length of an MP3 in seconds, or None if ffprobe isn't available."""
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1", str(path),
            ],
            capture_output=True, text=True, timeout=30,
        )
        return float(out.stdout.strip())
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
        return None


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
        from datetime import date

        # Mon–Wed belongs to the Monday edition, Thu–Sun to the Thursday one.
        edition = date.fromisoformat(
            curated.get("edition_date") or date.today().isoformat()
        )
        thursday = edition.weekday() >= 3
        edition = "Πέμπτης" if thursday else "Δευτέρας"
        goodbye = (
            "Καλό Σαββατοκύριακο σε όλους!" if thursday else "Καλή εβδομάδα σε όλους!"
        )
        lines = [f"ΕΚΔΟΣΗ: {edition}", f"ΑΠΟΧΑΙΡΕΤΙΣΜΟΣ: {goodbye}"]
        # Name days, the joke and the weather are deliberately NOT given to
        # Claude — it would paraphrase them (or add names, change numbers).
        # Claude only writes the [ΓΙΟΡΤΕΣ] / [ΑΣΤΕΙΟ] / [ΚΑΙΡΟΣ] placeholders;
        # the exact text is spliced in afterwards (see generate()).
        if curated.get("namedays"):
            lines.append("\nΓΙΟΡΤΕΣ: ΝΑΙ")
        if curated.get("joke", ""):
            lines.append("\nΑΣΤΕΙΟ: ΝΑΙ")
        if curated.get("weather"):
            lines.append("\nΚΑΙΡΟΣ: ΝΑΙ")
        lines.append("\nΕΛΛΗΝΙΚΑ ΝΕΑ:")
        for item in curated.get("greek_news", []):
            lines.append(f"- {item['title']}: {item.get('summary', '')}")
        lines.append("\nΠΑΓΚΟΣΜΙΑ ΘΕΤΙΚΑ ΝΕΑ:")
        for item in curated.get("world_news", []):
            lines.append(f"- {item['title']}: {item.get('summary', '')}")
        return "\n".join(lines)

    @staticmethod
    def _splice(
        script: str, marker: str, text: str, fallback_pos: int, lead_in: str = ""
    ) -> str:
        """Put `text` verbatim where Claude left `marker`. If Claude forgot the
        marker, insert it (with `lead_in`) as its own paragraph at
        `fallback_pos` so it still airs. Empty text removes stray markers."""
        if not text:
            return script.replace(marker, "").strip()
        if marker in script:
            script = script.replace(marker, text, 1)
            return script.replace(marker, "").strip()
        paras = re.split(r"\n{2,}", script)
        paras.insert(min(fallback_pos, len(paras)), f"{lead_in} {text}".strip())
        return "\n\n".join(paras)

    def _tts_to_file(self, text: str, cfg: dict, path: Path) -> None:
        """Stream TTS directly to file — the only fully-reliable method."""
        with self.openai.audio.speech.with_streaming_response.create(
            model=cfg["model"],
            voice=cfg["voice"],
            input=text,
        ) as response:
            response.stream_to_file(str(path))

    def _tts_checked(self, text: str, cfg: dict, path: Path) -> float | None:
        """Make one chunk, and make it again if it came out too short.
        Returns the chunk's length in seconds (None if it can't be measured)."""
        self._tts_to_file(text, cfg, path)
        secs = audio_seconds(path)
        if secs is None or len(text) / max(secs, 0.1) <= TOO_FAST_CHARS_PER_SEC:
            return secs

        print(
            f"    Chunk came out too short ({secs:.0f}s for {len(text)} chars), "
            "making it again..."
        )
        retry = path.with_name(path.stem + "_retry.mp3")
        self._tts_to_file(text, cfg, retry)
        retry_secs = audio_seconds(retry) or 0.0
        if retry_secs > secs:
            retry.replace(path)
            secs = retry_secs
        else:
            retry.unlink(missing_ok=True)
        if len(text) / max(secs, 0.1) > TOO_FAST_CHARS_PER_SEC:
            print(f"    WARNING: chunk may still be missing words ({secs:.0f}s)")
        else:
            print(f"    Fixed: now {secs:.0f}s")
        return secs

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
        nameday_text = namedays.spoken_text(curated.get("namedays", []))
        joke = curated.get("joke", "")
        script = self._splice(script, "[ΓΙΟΡΤΕΣ]", nameday_text, 1)
        script = self._splice(
            script, "[ΑΣΤΕΙΟ]", joke, 2 if nameday_text else 1,
            lead_in="Και τώρα, το ανέκδοτο της ημέρας!",
        )
        # Weather goes just before the goodbye (the last paragraph).
        script = self._splice(
            script, "[ΚΑΙΡΟΣ]", weather.spoken_text(curated.get("weather")), -1
        )
        print(f"Script: {len(script)} chars, {len(script.split())} words")

        script_path = self.audio_dir / f"script_{date_str}.txt"
        script_path.write_text(script, encoding="utf-8")

        chunks = split_paragraphs(script)
        print(f"Chunks: {len(chunks)}, sizes: {[len(c) for c in chunks]}")
        if any(len(c) > CHUNK_LIMIT for c in chunks):  # cannot happen, see split
            raise RuntimeError("A chunk is longer than CHUNK_LIMIT")

        cfg = self.config["audio"]
        chunk_files = []
        for i, chunk in enumerate(chunks, 1):
            p = self.audio_dir / f"_chunk_{i:03d}.mp3"
            print(f"  TTS chunk {i}/{len(chunks)} ({len(chunk)} chars)...")
            secs = self._tts_checked(chunk, cfg, p)
            if secs:
                print(f"    {secs:.0f}s ({len(chunk) / secs:.1f} chars/sec)")
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
        secs = audio_seconds(audio_path) or size / 16000  # 128 kbps estimate
        print(
            f"Audio saved: {audio_path} ({size:,} bytes, {int(secs) // 60}m{int(secs) % 60:02d}s, "
            f"{len(script) / secs:.1f} chars/sec — about 14 is normal)"
        )
        return audio_path


if __name__ == "__main__":
    gen = AudioGenerator()
    gen.generate()

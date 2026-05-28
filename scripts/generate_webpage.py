#!/usr/bin/env python3
import json
import yaml
from datetime import datetime
from pathlib import Path


CATEGORY_COLORS = {
    "Επιστήμη": "#2563eb",
    "Πολιτισμός": "#7c3aed",
    "Περιβάλλον": "#16a34a",
    "Τεχνολογία": "#0891b2",
    "Κοινωνία": "#d97706",
    "Οικονομία": "#0369a1",
    "Τουρισμός": "#0e7490",
    "Εκπαίδευση": "#6d28d9",
    "Υγεία": "#be185d",
    "Καινοτομία": "#059669",
    "Τέχνη": "#b45309",
}

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


def greek_date(dt):
    return f"{dt.day} {GREEK_MONTHS[dt.month]} {dt.year}"


def category_badge(cat):
    color = CATEGORY_COLORS.get(cat, "#6b7280")
    return f'<span class="badge" style="background:{color}">{cat}</span>'


def news_card(item):
    badge = category_badge(item.get("category", ""))
    return f"""
        <article class="card">
            <div class="card-header">
                {badge}
                <span class="source">{item.get("source", "")}</span>
            </div>
            <h3 class="card-title">{item["title"]}</h3>
            <p class="card-summary">{item.get("summary", "")}</p>
            <a href="{item.get("url", "#")}" class="read-more" target="_blank" rel="noopener">
                Διαβάστε περισσότερα →
            </a>
        </article>"""


def build_html(curated, date_str, has_audio):
    now = datetime.now()
    greek_dt = greek_date(now)
    cache_bust = now.strftime("%Y%m%d%H%M")
    intro = curated.get("weekly_intro", "")
    greek_news = curated.get("greek_news", [])
    world_news = curated.get("world_news", [])
    namedays = curated.get("namedays", [])
    joke = curated.get("joke", "")

    if has_audio:
        audio_player = f"""
        <div class="audio-bar" id="podcast-bar">
            <audio id="podcast-audio" preload="auto" playsinline>
                <source src="narration_{date_str}.mp3?v={cache_bust}" type="audio/mpeg">
            </audio>
            <button class="big-play-btn" id="play-btn">
                🔊 ΠΑΤΑ ΕΔΩ ΓΙΑ ΝΑ ΠΑΙΞΕΙ
            </button>
            <div class="progress-wrap" id="progress-wrap">
                <div class="progress-bar" id="progress-bar"></div>
            </div>
            <span class="audio-duration-label">🎙️ Τα νέα της μαμάς &nbsp;·&nbsp; ~5 λεπτά &nbsp;·&nbsp; {greek_dt}</span>
        </div>
        <script>
        (function() {{
            var audio = document.getElementById('podcast-audio');
            var btn   = document.getElementById('play-btn');
            var bar   = document.getElementById('progress-bar');
            var wrap  = document.getElementById('progress-wrap');

            function setBtn(playing) {{
                btn.textContent = playing ? '⏸ ΠΑΥΣΗ' : '🔊 ΠΑΤΑ ΕΔΩ ΓΙΑ ΝΑ ΠΑΙΞΕΙ';
            }}

            btn.addEventListener('click', function() {{
                if (audio.paused) {{ audio.play(); }} else {{ audio.pause(); }}
            }});

            wrap.addEventListener('click', function(e) {{
                var rect = wrap.getBoundingClientRect();
                audio.currentTime = ((e.clientX - rect.left) / rect.width) * audio.duration;
            }});

            audio.addEventListener('play',  function() {{ setBtn(true);  }});
            audio.addEventListener('pause', function() {{ setBtn(false); }});
            audio.addEventListener('ended', function() {{ setBtn(false); bar.style.width='100%'; }});
            audio.addEventListener('timeupdate', function() {{
                if (audio.duration) {{
                    bar.style.width = (audio.currentTime / audio.duration * 100) + '%';
                }}
            }});

            audio.play().catch(function() {{}});
        }})();
        </script>"""
    else:
        audio_player = f"""
        <div class="audio-bar audio-bar--pending">
            <span class="audio-pending">🎙️ Το podcast ετοιμάζεται… &nbsp;·&nbsp; {greek_dt}</span>
        </div>"""

    greek_cards = "\n".join(news_card(item) for item in greek_news)
    world_cards = "\n".join(news_card(item) for item in world_news)

    nameday_html = ""
    if namedays:
        items_html = "".join(
            f'<li><strong>{n["name"]}</strong> <span class="nd-date">— {n["date"]}</span></li>'
            for n in namedays
        )
        nameday_html = f"""
        <div class="extra-block nameday-block">
            <h3>🎂 Ονομαστικές εορτές εβδομάδας</h3>
            <ul class="nameday-list">{items_html}</ul>
        </div>"""

    joke_html = ""
    if joke:
        joke_html = f"""
        <div class="extra-block joke-block">
            <h3>😄 Το αστείο της εβδομάδας</h3>
            <p class="joke-text">{joke}</p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="el">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Τα νέα της μαμάς — {greek_dt}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif:ital,wght@0,400;0,700;1,400&family=Noto+Sans:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

        :root {{
            --blue:    #0d47a1;
            --blue-light: #1565c0;
            --sky:     #e3f2fd;
            --gold:    #f9a825;
            --white:   #ffffff;
            --text:    #1a1a2e;
            --muted:   #546e7a;
            --border:  #cfd8dc;
            --card-bg: #ffffff;
            --page-bg: #f0f4f8;
        }}

        body {{
            font-family: 'Noto Sans', sans-serif;
            background: var(--page-bg);
            color: var(--text);
            min-height: 100vh;
        }}

        /* ── Header ── */
        header {{
            background: linear-gradient(135deg, var(--blue) 0%, #1a237e 100%);
            color: var(--white);
            padding: 0;
            position: relative;
            overflow: hidden;
        }}
        header::before {{
            content: '';
            position: absolute;
            inset: 0;
            background: repeating-linear-gradient(
                90deg,
                transparent 0px,
                transparent 38px,
                rgba(255,255,255,0.04) 38px,
                rgba(255,255,255,0.04) 40px
            );
        }}
        .header-inner {{
            position: relative;
            max-width: 900px;
            margin: 0 auto;
            padding: 3rem 1.5rem 2.5rem;
            text-align: center;
        }}
        .meander {{
            width: 100%;
            height: 8px;
            background: repeating-linear-gradient(
                90deg,
                var(--gold) 0px, var(--gold) 8px,
                transparent 8px, transparent 12px,
                var(--gold) 12px, var(--gold) 16px,
                transparent 16px, transparent 20px
            );
            margin-bottom: 1.5rem;
            opacity: 0.9;
        }}
        .site-label {{
            font-size: 0.75rem;
            letter-spacing: 0.25em;
            text-transform: uppercase;
            color: var(--gold);
            margin-bottom: 0.75rem;
        }}
        h1 {{
            font-family: 'Noto Serif', serif;
            font-size: clamp(1.8rem, 4vw, 3rem);
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: 0.5rem;
        }}
        .header-date {{
            color: rgba(255,255,255,0.7);
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
        }}
        .intro {{
            font-family: 'Noto Serif', serif;
            font-style: italic;
            font-size: 1.05rem;
            line-height: 1.7;
            color: rgba(255,255,255,0.9);
            max-width: 640px;
            margin: 0 auto;
        }}
        .meander-bottom {{
            width: 100%;
            height: 8px;
            background: repeating-linear-gradient(
                90deg,
                var(--gold) 0px, var(--gold) 8px,
                transparent 8px, transparent 12px,
                var(--gold) 12px, var(--gold) 16px,
                transparent 16px, transparent 20px
            );
            margin-top: 2rem;
            opacity: 0.9;
        }}

        /* ── Audio bar ── */
        .audio-bar {{
            background: var(--blue);
            color: var(--white);
            padding: 1.25rem 1.5rem 1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 3px 12px rgba(0,0,0,0.35);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.75rem;
        }}
        .audio-bar--pending {{
            background: #37474f;
            padding: 1rem 1.5rem;
            justify-content: center;
        }}
        .big-play-btn {{
            background: #FFD600;
            color: #000;
            border: none;
            border-radius: 12px;
            width: 100%;
            max-width: 560px;
            padding: 1.1rem 1rem;
            font-size: 1.5rem;
            font-weight: 900;
            letter-spacing: 0.05em;
            cursor: pointer;
            box-shadow: 0 4px 14px rgba(0,0,0,0.35);
            transition: transform 0.12s, background 0.12s;
        }}
        .big-play-btn:active {{ transform: scale(0.97); background: #FFC400; }}
        .progress-wrap {{
            width: 100%;
            max-width: 560px;
            height: 8px;
            background: rgba(255,255,255,0.2);
            border-radius: 4px;
            cursor: pointer;
        }}
        .progress-bar {{
            height: 100%;
            width: 0%;
            background: #FFD600;
            border-radius: 4px;
            transition: width 0.5s linear;
        }}
        .audio-duration-label {{
            font-size: 0.78rem;
            opacity: 0.7;
        }}
        .audio-pending {{
            font-size: 1rem;
            opacity: 0.85;
            font-style: italic;
        }}

        /* ── Main layout ── */
        main {{
            max-width: 900px;
            margin: 0 auto;
            padding: 2.5rem 1.5rem 4rem;
        }}

        /* ── Section heading ── */
        .section-block {{
            background: var(--white);
            border-radius: 16px;
            padding: 2rem 1.5rem 1.5rem;
            margin-bottom: 2.5rem;
            box-shadow: 0 2px 12px rgba(13,71,161,0.08);
            border: 2px solid var(--border);
        }}
        .section-heading {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 4px solid var(--blue);
        }}
        .section-flag {{ font-size: 2rem; }}
        .section-heading h2 {{
            font-family: 'Noto Serif', serif;
            font-size: 1.6rem;
            color: var(--blue);
            font-weight: 700;
        }}
        .section-count {{
            margin-left: auto;
            font-size: 0.8rem;
            color: var(--muted);
            background: var(--sky);
            padding: 0.25rem 0.7rem;
            border-radius: 999px;
            font-weight: 600;
        }}

        /* ── Card grid ── */
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 1.25rem;
            margin-bottom: 3rem;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            transition: box-shadow 0.2s, transform 0.2s;
        }}
        .card:hover {{
            box-shadow: 0 8px 24px rgba(13,71,161,0.12);
            transform: translateY(-2px);
        }}
        .card-header {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}
        .badge {{
            color: #fff;
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.04em;
            padding: 0.2rem 0.55rem;
            border-radius: 999px;
            text-transform: uppercase;
        }}
        .source {{
            font-size: 0.75rem;
            color: var(--muted);
            margin-left: auto;
        }}
        .card-title {{
            font-family: 'Noto Serif', serif;
            font-size: 1rem;
            font-weight: 700;
            line-height: 1.4;
            color: var(--text);
        }}
        .card-summary {{
            font-size: 0.88rem;
            line-height: 1.6;
            color: #374151;
            flex: 1;
        }}
        .read-more {{
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--blue);
            text-decoration: none;
            align-self: flex-start;
        }}
        .read-more:hover {{ text-decoration: underline; }}

        /* ── Top extras (nameday + joke, shown between player and header) ── */
        .top-extras {{
            max-width: 900px;
            margin: 1.25rem auto 0;
            padding: 0 1.5rem;
            display: flex;
            gap: 1.25rem;
            flex-wrap: wrap;
        }}
        .top-extras .extra-block {{
            flex: 1;
            min-width: 260px;
            margin-bottom: 0;
        }}

        /* ── Nameday & Joke blocks ── */
        .extra-block {{
            border-radius: 16px;
            padding: 1.5rem 1.75rem;
            margin-bottom: 2.5rem;
        }}
        .extra-block h3 {{
            font-family: 'Noto Serif', serif;
            font-size: 1.25rem;
            margin-bottom: 1rem;
        }}
        .nameday-block {{
            background: #e8f4fd;
            border: 2px solid #90caf9;
        }}
        .nameday-block h3 {{ color: #1565c0; }}
        .nameday-list {{
            list-style: none;
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem 1.5rem;
            padding: 0;
        }}
        .nameday-list li {{ font-size: 1rem; }}
        .nd-date {{ font-size: 0.82rem; color: var(--muted); }}
        .joke-block {{
            background: #fffde7;
            border: 2px solid #ffe082;
        }}
        .joke-block h3 {{ color: #f57f17; }}
        .joke-text {{
            font-size: 1.05rem;
            line-height: 1.7;
            font-style: italic;
            color: #37474f;
        }}

        /* ── Footer ── */
        footer {{
            background: var(--blue);
            color: rgba(255,255,255,0.7);
            text-align: center;
            padding: 1.5rem;
            font-size: 0.8rem;
        }}
        footer a {{ color: var(--gold); text-decoration: none; }}

        @media (max-width: 480px) {{
            .card-grid {{ grid-template-columns: 1fr; }}
            h1 {{ font-size: 1.6rem; }}
        }}
    </style>
</head>
<body>
    {audio_player}

    <div class="top-extras">
        {nameday_html}
        {joke_html}
    </div>

    <header>
        <div class="meander"></div>
        <div class="header-inner">
            <p class="site-label">Εβδομαδιαία Έκδοση · Podcast</p>
            <h1>Τα νέα της μαμάς 🇬🇷</h1>
            <p class="header-date">{greek_dt}</p>
            <p class="intro">{intro}</p>
        </div>
        <div class="meander-bottom"></div>
    </header>

    <main>
        <div class="section-block">
            <div class="section-heading">
                <span class="section-flag">🇬🇷</span>
                <h2>Νέα από την Ελλάδα</h2>
                <span class="section-count">{len(greek_news)} ειδήσεις</span>
            </div>
            <div class="card-grid">
                {greek_cards}
            </div>
        </div>

        <div class="section-block">
            <div class="section-heading">
                <span class="section-flag">🌍</span>
                <h2>Θετικά Νέα από τον Κόσμο</h2>
                <span class="section-count">{len(world_news)} ειδήσεις</span>
            </div>
            <div class="card-grid">
                {world_cards}
            </div>
        </div>

    </main>

    <footer>
        <p>Δημιουργήθηκε αυτόματα με AI · Πηγές: ΑΠΕ-ΜΠΕ, Kathimerini, Positive.news, Good News Network κ.ά.</p>
        <p style="margin-top:0.4rem">
            <a href="index.html">Αρχική</a> ·
            Τελευταία ενημέρωση: {greek_dt}
        </p>
    </footer>
</body>
</html>"""


class WebpageGenerator:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        with open(self.base_dir / "config.yaml") as f:
            self.config = yaml.safe_load(f)
        self.data_dir = self.base_dir / "data"
        self.output_dir = self.base_dir / "output"
        self.output_dir.mkdir(exist_ok=True)

    def get_latest_curated(self):
        files = sorted(self.data_dir.glob("curated_*.json"), reverse=True)
        if not files:
            raise FileNotFoundError(
                "No curated files found. Run curate_content.py first."
            )
        return files[0]

    def generate(self):
        curated_path = self.get_latest_curated()
        date_str = curated_path.stem.split("_")[1]
        with open(curated_path, encoding="utf-8") as f:
            curated = json.load(f)

        audio_path = self.base_dir / "audio" / f"narration_{date_str}.mp3"
        has_audio = audio_path.exists()

        html = build_html(curated, date_str, has_audio)

        index_path = self.output_dir / "index.html"
        archive_path = self.output_dir / f"digest-{date_str}.html"
        for path in (index_path, archive_path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)

        if has_audio:
            import shutil

            shutil.copy(audio_path, self.output_dir / f"narration_{date_str}.mp3")

        print(f"Webpage saved to {index_path}")
        return index_path


if __name__ == "__main__":
    gen = WebpageGenerator()
    gen.generate()

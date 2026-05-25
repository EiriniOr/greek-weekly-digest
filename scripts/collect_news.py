#!/usr/bin/env python3
import feedparser
import requests
import json
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time


class NewsCollector:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        with open(self.base_dir / "config.yaml") as f:
            self.config = yaml.safe_load(f)
        self.data_dir = self.base_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    def fetch_feed(self, feed_config):
        url = feed_config["url"]
        name = feed_config["name"]
        headers = {
            "User-Agent": "greek-weekly-digest/1.0 (educational; contact renaorn@gmail.com)"
        }
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            items = []
            for entry in feed.entries:
                published = self._parse_date(entry)
                if published and published < self.week_ago:
                    continue
                items.append(
                    {
                        "title": entry.get("title", "").strip(),
                        "url": entry.get("link", ""),
                        "summary": self._clean_summary(entry),
                        "published": published.isoformat() if published else None,
                        "source": name,
                    }
                )
            print(f"  {name}: {len(items)} items")
            return items
        except Exception as e:
            print(f"  {name}: failed ({e})")
            return []

    def _parse_date(self, entry):
        for field in ("published_parsed", "updated_parsed"):
            t = entry.get(field)
            if t:
                try:
                    return datetime(*t[:6], tzinfo=timezone.utc)
                except Exception:
                    pass
        return datetime.now(timezone.utc)  # default to now if no date

    def _clean_summary(self, entry):
        raw = entry.get("summary", entry.get("description", ""))
        # strip HTML tags simply
        import re

        clean = re.sub(r"<[^>]+>", "", raw)
        return clean.strip()[:400]

    def collect(self):
        all_items = {"greek_news": [], "world_positive_news": []}

        print("Collecting Greek news...")
        cfg = self.config["sources"]["greek_news"]
        for feed in cfg["feeds"]:
            items = self.fetch_feed(feed)
            all_items["greek_news"].extend(items[: cfg["max_items_per_feed"]])
            time.sleep(0.5)

        print("Collecting world positive news...")
        cfg = self.config["sources"]["world_positive_news"]
        for feed in cfg["feeds"]:
            items = self.fetch_feed(feed)
            all_items["world_positive_news"].extend(items[: cfg["max_items_per_feed"]])
            time.sleep(0.5)

        date_str = datetime.now().strftime("%Y%m%d")
        out_path = self.data_dir / f"raw_news_{date_str}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)

        total = len(all_items["greek_news"]) + len(all_items["world_positive_news"])
        print(f"Saved {total} items to {out_path}")
        return out_path


if __name__ == "__main__":
    collector = NewsCollector()
    collector.collect()

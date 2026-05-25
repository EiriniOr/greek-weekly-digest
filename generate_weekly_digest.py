#!/usr/bin/env python3
"""Main orchestrator — runs the full Greek weekly positive news pipeline."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from collect_news import NewsCollector
from curate_content import ContentCurator
from generate_audio import AudioGenerator
from generate_webpage import WebpageGenerator
from deploy_github import GitHubDeployer


def run(deploy=True):
    start = time.time()
    steps = [
        ("Συλλογή ειδήσεων", NewsCollector, "collect"),
        ("Επιμέλεια με AI", ContentCurator, "curate"),
        ("Δημιουργία ήχου", AudioGenerator, "generate"),
        ("Δημιουργία ιστοσελίδας", WebpageGenerator, "generate"),
    ]

    for label, Cls, method in steps:
        print(f"\n{'=' * 50}")
        print(f"  {label}...")
        print(f"{'=' * 50}")
        try:
            obj = Cls()
            getattr(obj, method)()
        except Exception as e:
            print(f"ERROR in {label}: {e}")
            raise

    if deploy:
        print(f"\n{'=' * 50}")
        print("  Ανάπτυξη στο GitHub Pages...")
        print(f"{'=' * 50}")
        try:
            GitHubDeployer().deploy()
        except Exception as e:
            print(f"Deploy skipped (will still work locally): {e}")

    elapsed = time.time() - start
    print(f"\n✅ Ολοκληρώθηκε σε {elapsed:.0f} δευτερόλεπτα")
    print("   Το MP3 βρίσκεται στον φάκελο audio/")
    print("   Η ιστοσελίδα βρίσκεται στον φάκελο output/index.html")


if __name__ == "__main__":
    # Pass --no-deploy to skip GitHub Pages push (e.g. first manual run)
    deploy = "--no-deploy" not in sys.argv
    run(deploy=deploy)

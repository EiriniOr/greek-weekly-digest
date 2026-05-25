#!/usr/bin/env python3
import subprocess
import yaml
import os
from datetime import datetime
from pathlib import Path


class GitHubDeployer:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        with open(self.base_dir / "config.yaml") as f:
            self.config = yaml.safe_load(f)
        self.output_dir = self.base_dir / "output"

    def _run(self, *args, cwd=None):
        result = subprocess.run(
            args, cwd=cwd or self.output_dir, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"git error: {result.stderr.strip()}")
        return result.stdout.strip()

    def deploy(self):
        cfg = self.config["github"]
        repo = cfg["repo"]
        branch = cfg["branch"]
        date_str = datetime.now().strftime("%Y-%m-%d")
        remote_url = f"https://github.com/{repo}.git"

        print(f"Deploying to {repo} ({branch})...")

        try:
            self._run("git", "init")
            self._run("git", "checkout", "-B", branch)
            self._run("git", "config", "user.email", "renaorn@gmail.com")
            self._run("git", "config", "user.name", "Greek Weekly Digest Bot")
            self._run("git", "add", ".")
            self._run("git", "commit", "-m", f"Weekly digest update — {date_str}")

            # Use token from env if available
            token = os.environ.get("GITHUB_TOKEN")
            if token:
                auth_url = f"https://{token}@github.com/{repo}.git"
                self._run("git", "remote", "add", "origin", auth_url)
            else:
                self._run("git", "remote", "add", "origin", remote_url)

            self._run("git", "push", "-f", "origin", branch)
            print(
                f"Deployed: https://{repo.split('/')[0].lower()}.github.io/{repo.split('/')[1]}/"
            )
        except RuntimeError as e:
            print(f"Deploy failed: {e}")
            raise


if __name__ == "__main__":
    deployer = GitHubDeployer()
    deployer.deploy()

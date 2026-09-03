#!/usr/bin/env python3
"""Build changelog/releases.json from the per-version releases on FreeToken-Web.

Runs inside the Pages deploy (gh authenticates with GITHUB_TOKEN) and locally for
preview (gh auth login). Only the immutable v* releases carry a version's notes; the
rolling `beta` / `dev` tags describe whatever was built last and are skipped.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = os.environ.get("REPO", "FlashML-org/FreeToken-Web")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "changelog" / "releases.json"


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


# The page shows the version as its own heading, so the customary top heading is dropped.
WHATS_CHANGED = re.compile(r"^\s*<h[1-3][^>]*>\s*What'?s Changed\s*</h[1-3]>\s*", re.I)


def list_releases():
    page = 1
    while True:
        # The html media type returns each body already rendered (body_html), sanitized the
        # same way GitHub renders it on the release page.
        batch = json.loads(gh("api", "-H", "Accept: application/vnd.github.html+json",
                              f"repos/{REPO}/releases?per_page=100&page={page}"))
        yield from batch
        if len(batch) < 100:
            return
        page += 1


def main():
    releases = list_releases()
    out = []
    for r in releases:
        if r["draft"] or not r["tag_name"].startswith("v"):
            continue
        out.append({
            "tag": r["tag_name"],
            "date": r["published_at"],
            "prerelease": r["prerelease"],
            "url": r["html_url"],
            "html": WHATS_CHANGED.sub("", (r.get("body_html") or "").strip()),
        })
    out.sort(key=lambda r: r["date"], reverse=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "releases": out,
    }, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(out)} releases)", file=sys.stderr)


if __name__ == "__main__":
    main()

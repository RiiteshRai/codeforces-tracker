"""
cf_utils.py
-----------
Small shared helpers used by both add.py and logic.py:
- parse_cf_url(url)   -> pull (contest_id, index, is_gym) out of a link
- fetch_meta(...)     -> auto-fetch a problem's name + rating from Codeforces

Kept in one place so both scripts stay in sync and short.
"""

import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE_FILE = ROOT / "cf_cache.json"
CF_API_URL = "https://codeforces.com/api/problemset.problems"
CACHE_MAX_AGE_SECONDS = 6 * 60 * 60  # refresh the cached problem list every 6 hours

_CONTEST_PATTERNS = [
    re.compile(r"/contest/(\d+)/problem/([A-Za-z0-9]+)"),
    re.compile(r"/problemset/problem/(\d+)/([A-Za-z0-9]+)"),
]
_GYM_PATTERN = re.compile(r"/gym/(\d+)/problem/([A-Za-z0-9]+)")


def parse_cf_url(url):
    """Returns (contest_id, index, is_gym) or None if it's not a CF problem link."""
    url = (url or "").strip()
    if "codeforces.com" not in url:
        return None
    for pattern in _CONTEST_PATTERNS:
        m = pattern.search(url)
        if m:
            return m.group(1), m.group(2).upper(), False
    m = _GYM_PATTERN.search(url)
    if m:
        return "gym" + m.group(1), m.group(2).upper(), True
    return None


def _load_cache():
    if not CACHE_FILE.exists():
        return None
    try:
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if time.time() - cache.get("fetched_at", 0) > CACHE_MAX_AGE_SECONDS:
            return None
        return cache.get("problems")
    except (json.JSONDecodeError, OSError):
        return None


def _fetch_cf_problem_list():
    """Downloads the full CF problem list once, caches it locally for speed."""
    cached = _load_cache()
    if cached is not None:
        return cached

    print("   (fetching problem list from Codeforces API…)")
    try:
        with urllib.request.urlopen(CF_API_URL, timeout=10) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        print(f"   couldn't reach Codeforces API ({e}).")
        return {}

    if raw.get("status") != "OK":
        print("   Codeforces API returned an error.")
        return {}

    lookup = {}
    for p in raw["result"]["problems"]:
        lookup[f"{p['contestId']}-{p['index']}"] = {
            "name": p.get("name"),
            "rating": p.get("rating"),
        }
    CACHE_FILE.write_text(json.dumps({"fetched_at": time.time(), "problems": lookup}), encoding="utf-8")
    return lookup


def fetch_meta(contest_id, index, is_gym):
    """Returns {"name":..., "rating":...} for a problem, or None if not found."""
    if is_gym:
        return None  # gym problems aren't in the public problemset API
    return _fetch_cf_problem_list().get(f"{contest_id}-{index}")


# ---------- sections (easy / medium / hard / contests) ----------
SECTIONS_DIR = ROOT / "sections"
SECTION_NAMES = ["easy", "medium", "hard", "contests"]


def pick_section(arg=None):
    """Returns (name, path) for a section page, or (None, None) if invalid."""
    raw = (arg or input("Section (easy / medium / hard / contests): ")).strip().lower()
    if raw.endswith(".html"):
        raw = raw[:-5]
    if raw == "contest":
        raw = "contests"
    if raw not in SECTION_NAMES:
        print(f"Error: section must be one of: {', '.join(SECTION_NAMES)}.")
        return None, None
    path = SECTIONS_DIR / f"{raw}.html"
    if not path.exists():
        print(f"Error: {path} does not exist.")
        return None, None
    return raw, path

import re
import sys
from html import escape, unescape
from pathlib import Path

from cf_utils import parse_cf_url, fetch_meta

ROOT = Path(__file__).resolve().parent
WEEKS = ROOT / "weeks"


def existing_ids(html):
    """Set of (contest_id, index) already present in this week's file,
    so we catch duplicates even if the link was pasted in a different form
    (e.g. /contest/.../problem/.. vs /problemset/problem/...)."""
    ids = set()
    for m in re.finditer(r'<a href="([^"]+)"', html):
        parsed = parse_cf_url(unescape(m.group(1)))
        if parsed:
            ids.add((parsed[0], parsed[1]))
    return ids


def main():
    week = sys.argv[1] if len(sys.argv) > 1 else input("Enter week (example: week1): ").strip()
    if not week.endswith(".html"):
        week += ".html"

    file = WEEKS / week
    if not file.exists():
        print(f"Error: {week} does not exist.")
        return

    html = file.read_text(encoding="utf-8")
    print(f"\nAdding problems to {week}")
    print('Paste a Codeforces problem link. Type "done" when finished.\n')

    already = existing_ids(html)
    added = 0

    while True:
        url = input("Problem URL: ").strip()
        if url.lower() == "done":
            break
        if not url:
            print("URL cannot be empty.\n")
            continue

        parsed = parse_cf_url(url)
        if not parsed:
            print("That doesn't look like a Codeforces problem link.\n")
            continue

        contest_id, index, is_gym = parsed
        if (contest_id, index) in already:
            print("This problem is already in this week. Skipped.\n")
            continue

        meta = fetch_meta(contest_id, index, is_gym)
        if meta and meta.get("name"):
            name = meta["name"]
            rating = meta.get("rating")
            print(f"   found: {name}" + (f"  (rating {rating})" if rating else ""))
        else:
            # only asked when auto-detect fails (gym problem, or API unreachable)
            print("   couldn't auto-detect the name — type it in:")
            name = input("   Problem name: ").strip()
            if not name:
                print("Problem name cannot be empty. Skipped.\n")
                continue
            rating_in = input("   Rating (optional, press Enter to skip): ").strip()
            rating = rating_in or None

        tag = f"{contest_id}{index}"
        rating_html = f' <span class="rating">{escape(str(rating))}</span>' if rating else ""

        block = (
            '<div class="question" data-status="not-solved">\n'
            '<input type="checkbox">\n'
            f'<a href="{escape(url, quote=True)}" target="_blank">{escape(name)}</a>'
            f'{rating_html} <span class="tag">{escape(tag)}</span>\n'
            '<p>Write your logic here...</p>\n'
            '<span class="status">NOT SOLVED</span>\n'
            '</div>\n'
        )

        marker = "\n</div>\n<script>"
        pos = html.rfind(marker)
        if pos == -1:
            print("Could not find the weekly page structure.")
            return

        html = html[:pos] + "\n" + block + html[pos:]
        file.write_text(html, encoding="utf-8")
        already.add((contest_id, index))
        added += 1
        print(f"✓ Added: {name}\n")

    print(f"Done! Added {added} new problem(s) to {week}.")


if __name__ == "__main__":
    main()

import re
import sys
from html import escape, unescape

from cf_utils import parse_cf_url, fetch_meta, pick_section, SECTIONS_DIR


def existing_ids(html):
    """Set of (contest_id, index) already present in a page, so duplicates are
    caught even if the link was pasted in a different form."""
    ids = set()
    for m in re.finditer(r'<a href="([^"]+)"', html):
        parsed = parse_cf_url(unescape(m.group(1)))
        if parsed:
            ids.add((parsed[0], parsed[1]))
    return ids


def find_duplicate(contest_id, index):
    """Checks ALL sections, so a problem can't sit in both Easy and Hard."""
    for f in sorted(SECTIONS_DIR.glob("*.html")):
        if (contest_id, index) in existing_ids(f.read_text(encoding="utf-8")):
            return f.stem
    return None


def insert_block(html, block):
    marker = "\n</div>\n<script>"
    pos = html.rfind(marker)
    if pos == -1:
        return None
    return html[:pos] + "\n" + block + html[pos:]


def add_problems(section, file):
    print(f"\nAdding problems to {section}")
    print('Paste a Codeforces problem link. Type "done" when finished.\n')
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
        dup = find_duplicate(contest_id, index)
        if dup:
            print(f"This problem is already in '{dup}'. Skipped.\n")
            continue

        meta = fetch_meta(contest_id, index, is_gym)
        if meta and meta.get("name"):
            name = meta["name"]
            rating = meta.get("rating")
            print(f"   found: {name}" + (f"  (rating {rating})" if rating else ""))
        else:
            print("   couldn't auto-detect the name — type it in:")
            name = input("   Problem name: ").strip()
            if not name:
                print("Problem name cannot be empty. Skipped.\n")
                continue
            rating = input("   Rating (optional, press Enter to skip): ").strip() or None

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

        html = file.read_text(encoding="utf-8")
        new_html = insert_block(html, block)
        if new_html is None:
            print("Could not find the page structure.")
            return
        file.write_text(new_html, encoding="utf-8")
        added += 1
        print(f"✓ Added: {name}\n")

    print(f"Done! Added {added} new problem(s) to {section}.")


def add_contests(file):
    print("\nAdding contests")
    print('Type a contest number (example: 2030). Type "done" when finished.')
    print("Add the question + logic later with: python logic.py contests\n")
    added = 0

    while True:
        num = input("Contest number: ").strip()
        if num.lower() == "done":
            break
        if not num.isdigit():
            print("Contest number must be digits only.\n")
            continue

        html = file.read_text(encoding="utf-8")
        if f'data-contest="{num}"' in html:
            again = input(f"Contest {num} already has an entry. Add another? (y/n): ").strip().lower()
            if again != "y":
                print("Skipped.\n")
                continue

        block = (
            f'<div class="question" data-status="not-solved" data-contest="{num}">\n'
            '<input type="checkbox">\n'
            f'<a href="https://codeforces.com/contest/{num}" target="_blank">Question not added yet</a>'
            f' <span class="contest-badge">Contest {num}</span>\n'
            '<p>Write your logic here...</p>\n'
            '<span class="status">NOT SOLVED</span>\n'
            '</div>\n'
        )

        new_html = insert_block(html, block)
        if new_html is None:
            print("Could not find the page structure.")
            return
        file.write_text(new_html, encoding="utf-8")
        added += 1
        print(f"✓ Added: Contest {num}\n")

    print(f"Done! Added {added} contest(s).")


def main():
    section, file = pick_section(sys.argv[1] if len(sys.argv) > 1 else None)
    if not file:
        return
    if section == "contests":
        add_contests(file)
    else:
        add_problems(section, file)


if __name__ == "__main__":
    main()

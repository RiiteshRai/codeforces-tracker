import sys
import re
from pathlib import Path
from html import unescape, escape

from cf_utils import parse_cf_url

ROOT = Path(__file__).resolve().parent
WEEKS = ROOT / "weeks"


def set_status_attr(block, status):
    """Set data-status="solved"/"review" on the block's outer div, whether
    or not it already had the attribute (older entries won't)."""
    if 'data-status="' in block:
        return re.sub(r'data-status="[^"]*"', f'data-status="{status}"', block, count=1)
    return re.sub(r'(<div class="question")', rf'\1 data-status="{status}"', block, count=1)


def main():
    week = sys.argv[1] if len(sys.argv) > 1 else input("Enter week (example: week1): ").strip()
    if not week.endswith(".html"):
        week += ".html"

    file = WEEKS / week
    if not file.exists():
        print(f"Error: {week} does not exist.")
        return

    html = file.read_text(encoding="utf-8")
    blocks = re.findall(r'<div class="question".*?</div>', html, re.S)

    questions = []
    for block in blocks:
        m = re.search(r'<a href="([^"]+)" target="_blank">(.*?)</a>', block, re.S)
        if m:
            url = unescape(m.group(1))
            parsed = parse_cf_url(url)
            tag = f"{parsed[0]}{parsed[1]}" if parsed else ""
            questions.append({
                "url": url,
                "name": unescape(re.sub(r"\s+", " ", m.group(2)).strip()),
                "tag": tag,
                "block": block
            })

    if not questions:
        print("No problems found.")
        return

    print("\n=== QUESTIONS ===\n")
    for i, q in enumerate(questions, 1):
        print(f"{i}. {q['name']}" + (f"  [{q['tag']}]" if q['tag'] else ""))

    search = input("\nChoose number, name, URL, or tag (e.g. 1985F): ").strip()
    selected = None

    if search.isdigit() and 1 <= int(search) <= len(questions):
        selected = questions[int(search) - 1]
    else:
        needle = search.lower()
        matches = [
            q for q in questions
            if needle in q["name"].lower()
            or needle in q["url"].lower()
            or needle == q["tag"].lower()
        ]
        if len(matches) == 1:
            selected = matches[0]
        elif len(matches) > 1:
            print("\nMultiple matches:")
            for i, q in enumerate(matches, 1):
                print(f"{i}. {q['name']}")
            n = input("Choose number: ").strip()
            if n.isdigit() and 1 <= int(n) <= len(matches):
                selected = matches[int(n) - 1]

    if not selected:
        print("Problem not found.")
        return

    original = selected["block"]
    print(f"\nSelected: {selected['name']}")
    print("\nWrite your logic. Type END on a new line when finished:\n")

    lines = []
    while True:
        line = input()
        if line == "END":
            break
        lines.append(line)

    logic = "\n".join(lines).strip()
    if not logic:
        print("No logic entered. Nothing changed.")
        return

    new_block = re.sub(
        r"<p>.*?</p>",
        "<p>\n            " + escape(logic).replace("\n", "\n            ") + "\n        </p>",
        selected["block"], count=1, flags=re.S
    )

    if not re.search(r'<span class="rating">.*?</span>', new_block, re.S):
        rating = input("\nRating (optional, press Enter to skip): ").strip()
        if rating:
            new_block = new_block.replace("</a>", f'</a> <span class="rating">{escape(rating)}</span>', 1)

    solved = input("\nDid you solve it yourself? (y/n): ").strip().lower()

    if solved == "y":
        new_block = new_block.replace('<input type="checkbox">', '<input type="checkbox" checked>', 1)
        new_block = re.sub(r'<span class="status">.*?</span>', '<span class="status">SOLVED</span>', new_block, count=1, flags=re.S)
        new_block = set_status_attr(new_block, "solved")
    else:
        new_block = re.sub(r'<span class="status">.*?</span>', '<span class="status">REVIEW</span>', new_block, count=1, flags=re.S)
        new_block = set_status_attr(new_block, "review")

    html = html.replace(original, new_block, 1)
    file.write_text(html, encoding="utf-8")

    print("\n✓ Logic saved!")
    print("✓ Problem status updated!")


if __name__ == "__main__":
    main()

import sys
import re
from html import unescape, escape

from cf_utils import parse_cf_url, fetch_meta, pick_section

PLACEHOLDER = "Write your logic here..."


def set_status_attr(block, status):
    """Set data-status="solved"/"help"/"review" on the block's outer div, whether
    or not it already had the attribute (older entries won't)."""
    if 'data-status="' in block:
        return re.sub(r'data-status="[^"]*"', f'data-status="{status}"', block, count=1)
    return re.sub(r'(<div class="question")', rf'\1 data-status="{status}"', block, count=1)


def label(q):
    prefix = f"[Contest {q['contest']}] " if q["contest"] else ""
    return prefix + q["name"] + (f"  [{q['tag']}]" if q["tag"] else "")


def ask_problem():
    """Contest section: set/replace the problem inside a contest entry.
    Returns (url, name, rating, tag) or None to keep the current one."""
    url = input("\nProblem URL (press Enter to keep current): ").strip()
    if not url:
        return None
    parsed = parse_cf_url(url)
    if not parsed:
        print("That doesn't look like a Codeforces problem link. Keeping current.")
        return None

    contest_id, index, is_gym = parsed
    meta = fetch_meta(contest_id, index, is_gym)
    if meta and meta.get("name"):
        name, rating = meta["name"], meta.get("rating")
        print(f"   found: {name}" + (f"  (rating {rating})" if rating else ""))
    else:
        print("   couldn't auto-detect the name — type it in:")
        name = input("   Problem name: ").strip()
        if not name:
            print("Name cannot be empty. Keeping current.")
            return None
        rating = input("   Rating (optional, press Enter to skip): ").strip() or None
    return url, name, rating, f"{contest_id}{index}"


def apply_problem(block, url, name, rating, tag):
    """Swap the link/name, rating and tag inside a block (contest badge is kept)."""
    link = f'<a href="{escape(url, quote=True)}" target="_blank">{escape(name)}</a>'
    block = re.sub(r'<a href="[^"]*" target="_blank">.*?</a>', lambda m: link, block, count=1, flags=re.S)
    block = re.sub(r'\s*<span class="rating">.*?</span>', "", block, count=1, flags=re.S)
    block = re.sub(r'\s*<span class="tag">.*?</span>', "", block, count=1, flags=re.S)
    extra = (f' <span class="rating">{escape(str(rating))}</span>' if rating else "")
    extra += f' <span class="tag">{escape(tag)}</span>'
    return block.replace("</a>", "</a>" + extra, 1)


def main():
    section, file = pick_section(sys.argv[1] if len(sys.argv) > 1 else None)
    if not file:
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
            c = re.search(r'data-contest="(\d+)"', block)
            questions.append({
                "url": url,
                "name": unescape(re.sub(r"\s+", " ", m.group(2)).strip()),
                "tag": tag,
                "contest": c.group(1) if c else "",
                "block": block
            })

    if not questions:
        print("No problems found.")
        return

    print(f"\n=== {section.upper()} ===\n")
    for i, q in enumerate(questions, 1):
        print(f"{i}. {label(q)}")

    search = input("\nChoose number, name, URL, tag (e.g. 1985F)" +
                   (" or contest number" if section == "contests" else "") + ": ").strip()
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
            or (q["contest"] and needle == q["contest"])
        ]
        if len(matches) == 1:
            selected = matches[0]
        elif len(matches) > 1:
            print("\nMultiple matches:")
            for i, q in enumerate(matches, 1):
                print(f"{i}. {label(q)}")
            n = input("Choose number: ").strip()
            if n.isdigit() and 1 <= int(n) <= len(matches):
                selected = matches[int(n) - 1]

    if not selected:
        print("Problem not found.")
        return

    original = selected["block"]
    base = original
    print(f"\nSelected: {label(selected)}")

    # contests: first set which question you solved from that contest
    if section == "contests":
        problem = ask_problem()
        if problem:
            base = apply_problem(original, *problem)

    print('\nWrite your logic. Type END on a new line when finished.')
    print('(Or type CLEAR alone and press END to wipe existing logic.)\n')

    lines = []
    while True:
        line = input()
        if line == "END":
            break
        lines.append(line)

    old_p_match = re.search(r"<p>(.*?)</p>", base, re.S)
    old_text = unescape(old_p_match.group(1)).strip() if old_p_match else ""

    if lines == ["CLEAR"]:
        combined = PLACEHOLDER
        print("\n✓ Logic cleared.")
    else:
        logic = "\n".join(lines).strip()
        if not logic:
            if base == original:
                print("No logic entered. Nothing changed.")
                return
            combined = old_text or PLACEHOLDER  # contest: question set, logic later
        elif old_text and old_text != PLACEHOLDER:
            combined = old_text + "\n\n---\n\n" + logic
        else:
            combined = logic

    replacement = "<p>\n            " + escape(combined).replace("\n", "\n            ") + "\n        </p>"
    new_block = re.sub(r"<p>.*?</p>", lambda m: replacement, base, count=1, flags=re.S)

    if not re.search(r'<span class="rating">.*?</span>', new_block, re.S):
        rating = input("\nRating (optional, press Enter to skip): ").strip()
        if rating:
            new_block = new_block.replace("</a>", f'</a> <span class="rating">{escape(rating)}</span>', 1)

    print("\nHow did it go?")
    print("  1. Solved it myself")
    print("  2. Solved with help (hint / editorial / AI / friend)")
    print("  3. Not solved yet")
    choice = input("Choose 1/2/3: ").strip()

    # normalize checkbox first so re-editing a question doesn't duplicate "checked"
    new_block = re.sub(r'<input type="checkbox"[^>]*>', '<input type="checkbox">', new_block, count=1)

    if choice == "1":
        new_block = new_block.replace('<input type="checkbox">', '<input type="checkbox" checked>', 1)
        new_block = re.sub(r'<span class="status">.*?</span>', '<span class="status">SOLVED</span>', new_block, count=1, flags=re.S)
        new_block = set_status_attr(new_block, "solved")
    elif choice == "2":
        new_block = new_block.replace('<input type="checkbox">', '<input type="checkbox" checked>', 1)
        new_block = re.sub(r'<span class="status">.*?</span>', '<span class="status">SOLVED WITH HELP</span>', new_block, count=1, flags=re.S)
        new_block = set_status_attr(new_block, "help")
    else:
        new_block = re.sub(r'<span class="status">.*?</span>', '<span class="status">REVIEW</span>', new_block, count=1, flags=re.S)
        new_block = set_status_attr(new_block, "review")

    html = html.replace(original, new_block, 1)
    file.write_text(html, encoding="utf-8")

    print("\n✓ Logic saved!")
    print("✓ Problem status updated!")


if __name__ == "__main__":
    main()

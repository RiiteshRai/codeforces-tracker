"""
upgrade.py  -  run ONCE inside your tracker folder:   python upgrade.py
Turns the weekly tracker into Easy / Medium / Hard / Contests sections.
Then push with:   python sync.py
Old files (weeks/, newweek.py, week-template.html) are NOT touched - delete them if you like.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

FILES = {
"add.py": r'''import re
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
''',
"logic.py": r'''import sys
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
''',
"index.html": r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Codeforces Practice</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<div class="container">
<h1>CODEFORCES PRACTICE</h1>
<p class="subtitle">Problem tracker</p>

<a class="week easy" href="sections/easy.html">
    <span>Easy</span>
    <small>Warm-up problems</small>
</a>
<a class="week medium" href="sections/medium.html">
    <span>Medium</span>
    <small>Core practice</small>
</a>
<a class="week hard" href="sections/hard.html">
    <span>Hard</span>
    <small>Stretch problems</small>
</a>
<a class="week contests" href="sections/contests.html">
    <span>Contests</span>
    <small>Contest upsolving</small>
</a>
</div>
</body>
</html>
''',
"README.txt": r'''CODEFORCES TRACKER  (Easy / Medium / Hard / Contests)

Sections: easy, medium, hard, contests

ADD PROBLEMS (easy / medium / hard):
    python add.py easy
Paste a problem URL - name and rating are fetched automatically.
Type done when finished. A problem can't be added twice across ANY section.

ADD A CONTEST:
    python add.py contests
Type just the contest number (e.g. 2030). Type done when finished.

WRITE LOGIC / UPDATE STATUS:
    python logic.py easy
    python logic.py contests
Choose by number, name, URL, tag (e.g. 1985F) - or contest number.
Contests: you are first asked for the problem URL (name/rating auto-fetched),
then the logic. Press Enter to skip either. Write logic, then type END.
Finally choose: 1 solved / 2 solved with help / 3 not solved (review).

OTHER:
- sync.py pushes everything to GitHub.
- cf_cache.json is auto-created and safe to delete.
- style.css controls the design.
''',
}

UTILS_ADD = r'''

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
'''

CSS_ADD = r'''

/* ---- sections ---- */
.week.easy { border-left: 6px solid #22c55e }
.week.medium { border-left: 6px solid #f59e0b }
.week.hard { border-left: 6px solid #ef4444 }
.week.contests { border-left: 6px solid #6366f1 }

.contest-badge {
    display: inline-block;
    margin-left: 6px;
    padding: 3px 8px;
    border-radius: 20px;
    background: #fef3c7;
    color: #b45309;
    font-size: 11px;
    font-weight: 700
}

@media(max-width:600px) {
    .contest-badge {
        display: block;
        width: max-content;
        margin: 8px 0 0 28px
    }
}
'''

SECTION_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%(t)s - Codeforces</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
<div class="container">
<a class="back" href="../index.html">← Back</a>
<div class="week-header">
<h1>%(t)s</h1>
<div class="stats"><span id="solved">0</span> / <span id="total">0</span> solved
<div class="progress"><div class="progress-bar" id="progress-bar"></div></div>
</div>
</div>
<!-- Problems are added automatically by add.py -->
</div>
<script>
const q=document.querySelectorAll(".question");
const s=document.querySelectorAll(".question input:checked").length;
document.getElementById("total").textContent=q.length;
document.getElementById("solved").textContent=s;
document.getElementById("progress-bar").style.width=(q.length?s/q.length*100:0)+"%%";
q.forEach(x=>{const b=x.querySelector("input");if(b.checked)x.classList.add("solved");b.addEventListener("change",()=>x.classList.toggle("solved",b.checked));});
</script>
</body>
</html>
'''


def main():
    if not (ROOT / "cf_utils.py").exists() or not (ROOT / "style.css").exists():
        print("Run this inside your tracker folder (cf_utils.py / style.css not found).")
        return

    for name, text in FILES.items():
        (ROOT / name).write_text(text, encoding="utf-8")
        print(f"✓ wrote {name}")

    utils = ROOT / "cf_utils.py"
    t = utils.read_text(encoding="utf-8")
    if "def pick_section" not in t:
        utils.write_text(t.rstrip() + "\n" + UTILS_ADD, encoding="utf-8")
    print("✓ updated cf_utils.py")

    css = ROOT / "style.css"
    t = css.read_text(encoding="utf-8")
    if ".contest-badge" not in t:
        css.write_text(t.rstrip() + "\n" + CSS_ADD, encoding="utf-8")
    print("✓ updated style.css")

    (ROOT / "sections").mkdir(exist_ok=True)
    for n, title in [("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard"), ("contests", "Contests")]:
        p = ROOT / "sections" / f"{n}.html"
        if p.exists():
            print(f"- sections/{n}.html already exists, kept")
        else:
            p.write_text(SECTION_TEMPLATE % {"t": title}, encoding="utf-8")
            print(f"✓ created sections/{n}.html")

    print("\nDone! Now run:  python sync.py")


if __name__ == "__main__":
    main()
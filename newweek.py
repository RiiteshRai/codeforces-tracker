from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parent
WEEKS = ROOT / "weeks"
INDEX = ROOT / "index.html"
TEMPLATE = ROOT / "week-template.html"

def main():
    WEEKS.mkdir(exist_ok=True)

    number = input("Week number: ").strip()
    start = input("Start date (example: 29/08/26): ").strip()
    end = input("End date (example: 05/09/26): ").strip()

    if not number or not start or not end:
        print("All fields are required.")
        return

    filename = f"week{number}.html"
    destination = WEEKS / filename

    if destination.exists():
        print(f"{filename} already exists.")
        return

    content = TEMPLATE.read_text(encoding="utf-8")
    content = content.replace("WEEK - Codeforces", f"Week {number} - Codeforces")
    content = content.replace("DATE - DATE", f"{start} - {end}")
    destination.write_text(content, encoding="utf-8")

    index = INDEX.read_text(encoding="utf-8")
    link = f'<a class="week" href="weeks/{filename}">\n    <span>{escape(start)} - {escape(end)}</span>\n    <small>Week {escape(number)}</small>\n</a>\n'

    marker = '<a class="week" href="weeks/week1.html">'
    pos = index.find(marker)

    if pos != -1:
        index = index[:pos] + link + "\n" + index[pos:]
    else:
        pos = index.rfind("</div>")
        index = index[:pos] + link + index[pos:]

    INDEX.write_text(index, encoding="utf-8")

    print(f"\n✓ Created weeks/{filename}")
    print("✓ Added the week to index.html")
    print(f"\nNow run: python add.py week{number}")

if __name__ == "__main__":
    main()

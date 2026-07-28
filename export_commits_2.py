import subprocess
from datetime import datetime
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


OUTPUT_FILE = "commits_report_noyabr.docx"

def get_git_commits():
    result = subprocess.run(
        [
            "git",
            "log",
            "--since=2025-11-01",
            "--until=2025-11-31",
            "--pretty=format:%H|%h|%an|%ad|%s",
            "--date=short"
        ],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.splitlines()


def enrich_message(msg):
    msg_l = msg.lower()

    if "seed" in msg_l:
        return "Urug‘ kirim/chiqim bo‘yicha hisobot logikasi takomillashtirildi"
    if "optimize" in msg_l:
        return "Algoritmlar optimizatsiya qilindi"
    if "speed" in msg_l:
        return "Hisobot ishlash tezligi yaxshilandi"
    if "fix" in msg_l:
        return "Xatoliklar tuzatildi"
    if "filter" in msg_l:
        return "Filtrlash va statistik bloklar qo‘shildi"

    return msg


def create_report():
    doc = Document()

    # ===== TITLE =====
    title = doc.add_heading(
        "2026-yil Stat-Urmon Reposi — Commitlar LOG Hisoboti",
        level=1
    )
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph(
        "Ushbu hisobotda Stat-Urmon repository bo‘yicha amalga oshirilgan commitlar, "
        "ularning mazmuni va funksional o‘zgarishlari jamlangan."
    )

    doc.add_paragraph("")

    # ===== TABLE =====
    table = doc.add_table(rows=1, cols=5)
    table.style = "Table Grid"

    headers = ["Sana", "Commit message", "Muallif", "Izoh (boyitilgan)", "Commit hash"]

    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        run = p.add_run(h)
        run.bold = True

    for line in get_git_commits():
        full_hash, short_hash, author, date, message = line.split("|", 4)

        pretty_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d %b %Y")

        row = table.add_row().cells
        row[0].text = pretty_date
        row[1].text = message
        row[2].text = author
        row[3].text = enrich_message(message)
        row[4].text = short_hash

    doc.save(OUTPUT_FILE)
    print(f"✅ Word hisobot yaratildi: {OUTPUT_FILE}")


if __name__ == "__main__":
    create_report()

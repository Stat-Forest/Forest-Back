from git import Repo
import csv

# 💡 Bu yerda frontend repong joylashgan to‘liq path
repo_path = "/home/oybek/urmon-rental-working"
repo = Repo(repo_path)

# 🔍 Barcha commitlarni olamiz
commits = list(repo.iter_commits('main'))  # Yoki branch 'master' bo‘lsa shu nomni yoz

# 📤 Faylga yozamiz
with open('frontend_commits.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Hash', 'Author', 'Date', 'Message'])

    for commit in commits:
        writer.writerow([
            commit.hexsha[:7],
            commit.author.name,
            commit.committed_datetime.strftime("%Y-%m-%d"),
            commit.message.strip()
        ])

print(f"✅ Exported {len(commits)} frontend commits to frontend_commits.csv")

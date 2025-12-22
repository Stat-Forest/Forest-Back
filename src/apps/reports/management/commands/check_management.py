from django.core.management.base import BaseCommand
from apps.reports.models import Statement, StatementColumn


class Command(BaseCommand):
    help = "Sotish uchun yaroqli ko‘chatlar statementidagi soni va summa ustunlarini is_user_input=True qilib yangilaydi"

    def handle(self, *args, **kwargs):
        try:
            statement = Statement.objects.get(name__icontains="Sotish uchun yaroqli ko‘chatlar")
        except Statement.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Statement 'Sotish uchun yaroqli ko‘chatlar' topilmadi."))
            return

        columns = StatementColumn.objects.filter(
            statement=statement,
            is_user_input=False,
        ).filter(
            title__icontains="soni"
        ) | StatementColumn.objects.filter(
            statement=statement,
            is_user_input=False,
            title__icontains="summa"
        )

        updated_count = 0
        for column in columns:
            column.is_user_input = True
            column.save(update_fields=["is_user_input"])
            updated_count += 1
            self.stdout.write(self.style.SUCCESS(f"✅ Updated: {column.title}"))

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Jami yangilangan ustunlar soni: {updated_count}"))

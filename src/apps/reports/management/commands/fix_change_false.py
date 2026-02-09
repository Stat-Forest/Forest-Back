from django.core.management.base import BaseCommand
from django.db import transaction

from apps.reports.models import Statement, StatementColumn


class Command(BaseCommand):
    help = "Ko‘chat-va-Nihol-ilova ostidagi barcha columnlarni is_user_input=True qiladi"

    def handle(self, *args, **options):

        self.stdout.write("🔍 Ko‘chat va Nihol statement qidirilmoqda...")

        try:
            statement = Statement.objects.get(name_uz="Ko‘chat va Nihol")
        except Statement.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Ko‘chat va Nihol statement topilmadi"))
            return

        ilova_parent = StatementColumn.objects.filter(
            statement=statement,
            title_uz__icontains="Ko‘chat-va-Nihol-ilova"
        ).first()

        if not ilova_parent:
            self.stdout.write(self.style.ERROR("❌ Ko‘chat-va-Nihol-ilova parent topilmadi"))
            return

        self.stdout.write(f"📌 Ilova parent topildi: {ilova_parent.title_uz}")
        self.stdout.write(f"📐 Ordering prefix: {ilova_parent.ordering}")

        # ⭐ MUHIM JOYI — butun subtree
        ilova_columns = StatementColumn.objects.filter(
            statement=statement,
            ordering__startswith=ilova_parent.ordering
        )

        false_columns = ilova_columns.filter(is_user_input=True)

        count = false_columns.count()

        if count == 0:
            self.stdout.write(self.style.WARNING("⚠️ False bo‘lgan column topilmadi"))
            return

        self.stdout.write(f"🔥 {count} ta column True qilinmoqda...")

        with transaction.atomic():
            updated = false_columns.update(is_user_input=False)

        self.stdout.write(
            self.style.SUCCESS(f"✅ {updated} ta column muvaffaqiyatli True qilindi")
        )

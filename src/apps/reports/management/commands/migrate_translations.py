from django.core.management.base import BaseCommand
from apps.reports.models import Statement, StatementColumn

class Command(BaseCommand):
    help = "Mavjud 'name' va 'title' ma'lumotlarini tarjima maydonlariga ko'chiradi"

    def handle(self, *args, **kwargs):
        statements = Statement.objects.all()
        for s in statements:
            if s.name and not s.name_uz:
                s.name_uz = s.name
                s.save(update_fields=["name_uz"])

        columns = StatementColumn.objects.all()
        for c in columns:
            if c.title and not c.title_uz:
                c.title_uz = c.title
                c.save(update_fields=["title_uz"])

        self.stdout.write(self.style.SUCCESS("✅ Tarjima maydonlari muvaffaqiyatli yangilandi."))

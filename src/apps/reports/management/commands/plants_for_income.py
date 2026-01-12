from django.core.management.base import BaseCommand
from django.db import transaction

from apps.reports.models import Plant, Statement


class Command(BaseCommand):
    help = "Create income plants for Daromad statement"

    PLANTS = [
        ("Ko‘chat va nihol sotish", "Продажа саженцев и рассады"),
        ("Yaylov tushumi", "Доход от пастбищ"),
        ("Yog‘och o‘tin sotish", "Продажа дров"),
        ("Sanoat va iste'mol mollari ishlab chiqarish", "Производство промышленных и потребительских товаров"),
        ("Aholiga pullik xizmat", "Платные услуги населению"),
        ("Qishloq xo‘jaligi mahsulotlari yetishtirish", "Производство сельскохозяйственной продукции"),
        ("Chorvachilik", "Животноводство"),
        ("Parrandachilik", "Птицеводство"),
        ("Quyonchilik", "Кролиководство"),
        ("Baliqchilik", "Рыбоводство"),
        ("Asalarichilik", "Пчеловодство"),
        ("Dorivor o‘simliklar yetishtirish", "Выращивание лекарственных растений"),
        ("Yer ijarasidan", "Доход от аренды земли"),
        ("Ko‘kalamzorlashtirish", "Озеленение"),
        ("Ihota daraxtzorlari barpo etish", "Создание защитных лесных полос"),
        ("Arizalarni ko‘rib chiqish va ruxsatnomalar berish", "Рассмотрение заявлений и выдача разрешений"),
        ("Yetkazilgan zararni qoplash", "Взыскание средств за причинённый ущерб"),
        ("Boshqa tushumlar", "Прочие доходы"),
    ]

    @transaction.atomic
    def handle(self, *args, **options):
        statement = Statement.objects.filter(name="Daromad 1").first()

        if not statement:
            self.stderr.write(self.style.ERROR("Statement 'Daromad 1' topilmadi"))
            return

        plants = []
        for name_uz, name_ru in self.PLANTS:
            plants.append(
                Plant(
                    name=name_uz,
                    statement=statement
                )
            )

        Plant.objects.bulk_create(plants, ignore_conflicts=True)

        self.stdout.write(
            self.style.SUCCESS(f"{len(plants)} ta Plant muvaffaqiyatli yaratildi")
        )

from django.core.management.base import BaseCommand
from django.db import transaction
from modeltranslation.utils import build_localized_fieldname

from apps.reports.models import Plant, Statement


PARENT_PLANT = {
    "uz": "Daromad manbalari",
    "ru": "Источники доходов",
}

CHILD_PLANTS = [
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
    ("Yetkazilgan zararni qoplash", "Взыскание средств за причинённый ущерb"),
    ("Boshqa tushumlar", "Прочие доходы"),
]


class Command(BaseCommand):
    help = "Create parent + child plants for 'Daromad' statement"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("🚀 Creating Daromad plant structure...")

        try:
            statement = Statement.objects.get(name="Daromad")
        except Statement.DoesNotExist:
            self.stderr.write("❌ Statement 'Daromad' topilmadi")
            return

        # 1️⃣ Parent plant
        parent, _ = Plant.objects.get_or_create(
            name=PARENT_PLANT["uz"],
            parent=None,
            defaults={"statement": statement}
        )

        parent.statement = statement
        setattr(parent, build_localized_fieldname("name", "uz"), PARENT_PLANT["uz"])
        setattr(parent, build_localized_fieldname("name", "ru"), PARENT_PLANT["ru"])
        parent.save()

        created_children = 0

        # 2️⃣ Child plants
        for name_uz, name_ru in CHILD_PLANTS:
            child, created = Plant.objects.get_or_create(
                name=name_uz,
                parent=parent,
                defaults={"statement": statement}
            )

            child.statement = statement
            setattr(child, build_localized_fieldname("name", "uz"), name_uz)
            setattr(child, build_localized_fieldname("name", "ru"), name_ru)
            child.save()

            if created:
                created_children += 1
                self.stdout.write(f"  ➕ Created child: {name_uz}")

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Daromad plants ready | Parent: 1 | Children: {created_children}"
            )
        )

from django.core.management.base import BaseCommand
from modeltranslation.utils import build_localized_fieldname

from apps.reports.models import Plant, Statement

CATEGORY_STRUCTURE = {
    "Iganbarglilar": [
        ("Qrim qarag‘ayi", "Крымская сосна"),
        ("Zarafshon archasi", "Зеравшанская арча"),
        ("Eldor qarag‘ayi", "Эльдарская сосна"),
        ("Virgin archasi", "Вирджинская можжевельник"),
        ("Kompakt tuya", "Компактный туя"),
        ("Sharq tuya", "Восточный туя"),
        ("Kiparis", "Кипарис"),
        ("Tog‘ archasi", "Горный можжевельник"),
    ],
    "Yaproqbarglilar": [
        ("Katalpa", "Катальпа"),
        ("Qayrag‘och", "Вяз"),
        ("Eman (chereshchaty)", "Дуб черешчатый"),
        ("Eman (Piramida)", "Дуб пирамидальный"),
        ("Maklyura", "Маклюра"),
        ("Gledichiya", "Гледичия"),
        ("Kanada bagryannigi", "Канадская багрянник"),
        ("Shumtol (yasen)", "Ясень"),
        ("Chinor", "Платан"),
        ("Oq akatsiya", "Белая акация"),
        ("Sovun daraxti", "Мыльное дерево"),
        ("Qog‘oz daraxti", "Бумажное дерево"),
        ("Lola daraxti", "Тюльпановое дерево"),
        ("Magnoliya", "Магнолия"),
        ("Akatsiya", "Акация"),
        ("Kashtan", "Каштан"),
        ("Lipa", "Липа"),
        ("Yapon safora", "Японская софора"),
        ("Sliva pissardi", "Слива Писсарди"),
        ("Zarang (klyon)", "Клён"),
        ("Ipak akatsiya", "Шёлковая акация"),
        ("Oqqayin", "Тополь белый"),
        ("Ginkgo biloba", "Гинкго билоба"),
        ("Kanada bundugi", "Канадский бундук"),
        ("Aylant", "Айлант"),
        ("Xilo katalpa", "Гибридная катальпа"),
        ("Oq qayin", "Берёза белая"),
        ("Terak", "Тополь"),
        ("Tol", "Ива"),
        ("Majnuntol", "Плакучая ива"),
        ("Pavlovniya", "Павловния"),
        ("Savattol", "Корзиночная ива"),
    ],
    "Tez o'suvchilar": [
        ("Terak", "Тополь"),
        ("Tol", "Ива"),
        ("Majnuntol", "Плакучая ива"),
        ("Pavlovniya", "Павловния"),
    ],
    "Mevalilar": [
        ("O‘rik", "Абрикос"),
        ("Olma", "Яблоко"),
        ("Shaftoli", "Персик"),
        ("Tut", "Шелковица"),
        ("Gilos", "Черешня"),
        ("Olcha (oddiy)", "Алыча"),
        ("Bexi", "Айва"),
        ("Nok", "Груша"),
        ("Xurmo", "Хурма"),
        ("Magalepka olcha", "Магалебская вишня"),
        ("Jiyda", "Джида"),
        ("Chilonjiyda", "Зизифус"),
        ("Qizil do‘lona", "Боярышник красный"),
        ("Uzum", "Виноград"),
        ("Anor", "Гранат"),
        ("Anjir", "Инжир"),
        ("Chappa tut", "Белая шелковица"),
        ("Non jiyda", "Лох съедобный"),
        ("Palma", "Пальма"),
        ("Limon", "Лимон"),
    ],
    "Yong`oq Mevalilar": [
        ("Shirin bodom", "Сладкий миндаль"),
        ("Bodom", "Миндаль"),
        ("Funduk", "Фундук"),
        ("Pekan (amerik. Yong‘oq)", "Пекан"),
        ("Xandon pista", "Фисташка настоящая"),
        ("Yong‘oq", "Грецкий орех"),
        ("Achchiq bodom", "Горький миндаль"),
    ],
    "Cho'l o'simliklari": [
        ("Saxsavul", "Саксаул"),
        ("Cherkez", "Черкез"),
        ("Yulg‘un", "Тамарикс"),
        ("Qoraburoq", "Солянка"),
        ("Qandim", "Кандым")
    ],
    "Butalar": [
        ("Na‘matak", "Шиповник"),
        ("Suriya gibiskusi", "Гибискус сирийский"),
        ("Sireni", "Сирень"),
        ("Magoniya", "Магнолия падуболистная"),
        ("Yapon bexisi", "Айва японская"),
        ("Amorfa", "Аморфа"),
        ("Pirokanta", "Пироканта"),
        ("Oddiy jasmin", "Жасмин обыкновенный"),
        ("Ispan droki", "Испанский дрок"),
        ("Tog‘ muruch", "Горный перец"),
        ("Uchqat (jimolost)", "Жимолость"),
        ("Zirk", "Барбарис"),
        ("Ligustrum", "Бирючина"),
        ("Beresklet", "Бересклет"),
        ("Forsiziya", "Форзиция"),
        ("Hind sireni", "Индийская сирень"),
        ("Atirgul", "Роза"),
        ("Cizalpinia", "Цезальпиния"),
        ("Chakanda", "Облепиха"),
        ("Sumax", "Сумах"),
        ("Yukka", "Юкка"),
        ("Smorodina", "Смородина"),
        ("Arxideya", "Орхидея"),
        ("Ryabina", "Рябина"),
        ("Lavanda", "Лаванда"),
    ]
}


class Command(BaseCommand):
    help = "Ko'chatxona va Niholxona Jami uchun o'simlik turlari va nomlarini yaratish"

    def handle(self, *args, **options):
        self.stdout.write("🚀 Ko'chatxona o'simliklari yaratilmoqda...")

        try:
            statement = Statement.objects.get(name_uz="Ko'chatxona va Niholxona Jami")
        except Statement.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                "❌ 'Ko'chatxona va Niholxona Jami' nomli Statement topilmadi!"
            ))
            return

        total_created = 0

        for category_uz, plants_list in CATEGORY_STRUCTURE.items():
            # 1. Kategoriya (parent) ni topish yoki yaratish
            parent_qs = Plant.objects.filter(
                name=category_uz,
                parent__isnull=True,
                statement=statement
            )

            if parent_qs.exists():
                parent = parent_qs.first()
                if parent_qs.count() > 1:
                    self.stdout.write(self.style.WARNING(
                        f"⚠️ Dublikat kategoriya: {category_uz} ({parent_qs.count()} ta) — birinchisi ishlatildi"
                    ))
            else:
                parent = Plant.objects.create(
                    name=category_uz,
                    statement=statement,
                    parent=None
                )
                total_created += 1
                self.stdout.write(f"  Parent yaratildi: {category_uz}")

            # Har doim nomlarni yangilash (xavfsizlik uchun)
            parent.name_uz = category_uz
            parent.name_ru = category_uz  # agar ruscha alohida bo'lsa - o'zgartiring
            parent.statement = statement
            parent.save(update_fields=['name_uz', 'name_ru', 'statement'])

            # 2. Bolalar (konkret o'simliklar)
            for name_uz, name_ru in plants_list:
                child_qs = Plant.objects.filter(
                    name=name_uz,
                    parent=parent,
                    statement=statement
                )

                if child_qs.exists():
                    child = child_qs.first()
                    if child_qs.count() > 1:
                        self.stdout.write(self.style.WARNING(
                            f"  ⚠️ Dublikat o'simlik: {name_uz} — birinchisi ishlatildi"
                        ))
                else:
                    child = Plant.objects.create(
                        name=name_uz,
                        parent=parent,
                        statement=statement
                    )
                    total_created += 1
                    self.stdout.write(f"    ➕ Yaratildi: {name_uz}")

                # Nomlarni yangilash
                child.name_uz = name_uz
                child.name_ru = name_ru
                child.statement = statement
                child.save(update_fields=['name_uz', 'name_ru', 'statement'])

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Hammasi tayyor! Jami yangi yaratilgan o'simliklar: {total_created} ta"
        ))

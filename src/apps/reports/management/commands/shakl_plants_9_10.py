from django.core.management.base import BaseCommand

from apps.reports.models import Statement, Plant

from modeltranslation.utils import auto_populate


CATEGORY_STRUCTURE = {
    "Iganbarglilar": [
        ("Qrim qarag‘ayi", "Қрим қарағайи"),
        ("Zarafshon archasi", "Зарафшон арчаси"),
        ("Eldor qarag‘ayi", "Элдор қарағайи"),
        ("Virgin archasi", "Виргин арчаси"),
        ("Kompakt tuya", "Компакт туя"),
        ("Sharq tuya", "Шарқ туя"),
        ("Kiparis", "Кипарис")
    ],
    "Yaproqbarglilar": [
        ("Katalpa", "Катальпа"),
        ("Qayrag‘och", "Қайрағоч"),
        ("Eman (chereshchaty)", "Эман (черешчатый)"),
        ("Eman (Piramida)", "Эман (Пирамида)"),
        ("Maklyura", "Маклюра"),
        ("Gledichiya", "Гледичия"),
        ("Kanada bagryannigi", "Канада багрянниги"),
        ("Shumtol (yasen)", "Шумтол (ясень)"),
        ("Chinor", "Чинор"),
        ("Oq akatsiya", "Оқ акация"),
        ("Sovun daraxti", "Совун дарахти"),
        ("Qog‘oz daraxti", "Қоғоз дарахти"),
        ("Lola daraxti", "Лола дарахти"),
        ("Magnoliya", "Магнолия"),
        ("Akatsiya", "Акатция"),
        ("Kashtan", "Каштан"),
        ("Lipa", "Липа"),
        ("Yapon safora", "Япон сафора"),
        ("Sliva pissardi", "Слива писсарди"),
        ("Zarang (klyon)", "Заранг (клён)"),
        ("Ipak akatsiya", "Ипак акация"),
        ("Oqqayin", "Оққайин"),
        ("Ginkgo biloba", "Гинкго билоба"),
        ("Kanada bundugi", "Канада  бундуги"),
        ("Aylant", "Айлант")
    ],
    "Mevalilar": [
        ("O‘rik", "Ўрик"),
        ("Olma", "Олма"),
        ("Shaftoli", "Шафтоли"),
        ("Tut", "Тут"),
        ("Gilos", "Гилос"),
        ("Olcha (oddiy)", "Олча (оддий)"),
        ("Bexi", "Бехи"),
        ("Nok", "Нок"),
        ("Xurmo", "Хурма"),
        ("Magalepka olcha", "Магалепка олча"),
        ("Jiyda", "Жийда"),
        ("Chilonjiyda", "Чилонжийда"),
        ("Qizil do‘lona", "Қизил дўлана")
    ],
    "Yong`oq Mevalilar": [
        ("Shirin bodom", "Ширин бодом"),
        ("Bodom", "Бодом"),
        ("Funduk", "Фундук"),
        ("Pekan (amerik. Yong‘oq)", "Пекан (америк. Ёнғоқ)"),
        ("Xandon pista", "Хандон писта"),
        ("Yong‘oq", "Ёнгок")
    ],
    "Cho'l o'simliklari": [
        ("Saxsavul", "Саксавул"),
        ("Cherkez", "Черкез"),
        ("Yulg‘un", "Юлғун"),
        ("Qoraburoq", "Қорабуроқ"),
        ("Qandim", "Қандим")
    ],
    "Butalar": [
        ("Na‘matak", "Наъматак"),
        ("Suriya gibiskusi", "Сурия гибискуси"),
        ("Sireni", "Сирень"),
        ("Magoniya", "Магония"),
        ("Yapon bexisi", "Япон бехиси"),
        ("Amorfa", "Аморфа"),
        ("Pirokanta", "Пироканта"),
        ("Oddiy jasmin", "Оддий жасмин"),
        ("Ispan droki", "Испан дроки"),
        ("Tog‘ muruch", "Тоғ муруч"),
        ("Uchqat (jimolost)", "Учқат (жимолость)"),
        ("Zirk", "зирк")
    ]
}

class Command(BaseCommand):
    help = "Reset and create categorized plants for Shakl 9-O‘X and Shakl 10-O‘X"

    def handle(self, *args, **kwargs):
        for name_uz in ["Shakl 9-O‘X", "Shakl 10-O‘X"]:
            statement = Statement.objects.filter(name_uz__icontains=name_uz).first()
            if not statement:
                self.stderr.write(self.style.ERROR(f"❌ Statement not found: {name_uz}"))
                continue

            # ❌ Avval childlarni o‘chiramiz, keyin parentlarni
            child_count, _ = Plant.objects.filter(statement=statement, parent__isnull=False).delete()
            parent_count, _ = Plant.objects.filter(statement=statement, parent__isnull=True).delete()
            total_deleted = child_count + parent_count
            self.stdout.write(self.style.WARNING(f"🧹 {name_uz}: {total_deleted} ta eski plantlar o‘chirildi."))

            created_total = 0
            with auto_populate('ru'):
                for category_uz, plants in CATEGORY_STRUCTURE.items():
                    category_ru = plants[0][1] if plants else category_uz

                    parent = Plant.objects.create(
                        name_uz=category_uz,
                        name_ru=category_ru,
                        parent=None,
                        statement=statement
                    )

                    for name_uz, name_ru in plants:
                        Plant.objects.create(
                            name_uz=name_uz,
                            name_ru=name_ru,
                            parent=parent,
                            statement=statement
                        )
                        created_total += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {name_uz}: {created_total} ta yangi plant yaratildi."
                )
            )
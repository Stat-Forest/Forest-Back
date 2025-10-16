from django.core.management.base import BaseCommand
from modeltranslation.utils import build_localized_fieldname

from apps.reports.models import Plant, Statement

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
    help = "Create plants for `Urug' harakati` statement"

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Creating plants for Urug' harakati...")

        try:
            statement = Statement.objects.get(name_uz="Urug' xarakati Reja")
        except Statement.DoesNotExist:
            self.stderr.write("❌ Statement 'Urug' harakati' not found.")
            return

        total_created = 0

        for parent_name, children in CATEGORY_STRUCTURE.items():
            # Parent
            parent, _ = Plant.objects.get_or_create(
                name=parent_name,
                parent=None,
                defaults={"statement": statement}
            )
            parent.statement = statement
            setattr(parent, build_localized_fieldname("name", "uz"), parent_name)
            setattr(parent, build_localized_fieldname("name", "ru"), parent_name)
            parent.save()

            # Children
            for name_uz, name_ru in children:
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
                    total_created += 1
                    self.stdout.write(f"  ➕ Created: {name_uz}")

        self.stdout.write(self.style.SUCCESS(f"✅ Done. Total new plants created: {total_created}"))
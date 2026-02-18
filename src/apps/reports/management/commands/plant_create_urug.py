from django.db import transaction
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
        ("Kiparis", "Кипарис"),
        ("Tyanshan qora qarag‘ayi", "Тяншан қора қарағайи"),
        ("Tog' archa", "Тоғ арча"),
    ],

    "Yaproqbarglilar": [
        ("Bagrannik", "Багрянник"),
        ("Eman (chereshchaty)", "Эман (черешчатый)"),
        ("Eman (piramida)", "Эман (пирамидальный)"),
        ("Qayrag‘och", "Қайрағоч"),
        ("Sada qayrag‘och", "Сада қайрағоч"),
        ("Shumtol", "Шумтол"),
        ("Aylant", "Айлант"),
        ("Savattol", "Саваттол"),
        ("Gledichiya", "Гледичия"),
        ("Chinor", "Чинор"),
        ("Yapon safora", "Япон сафора"),
        ("Kashtan", "Каштан"),
        ("Katalpa", "Катальпа"),
        ("Xilo katalpa", "Хило каталпа"),
        ("Oq qayin", "Оқ қайин"),
        ("Zarang", "Заранг"),
        ("Ipak akatsiya", "Ипак акация"),
        ("Akatsiya", "Акация"),
        ("Maklyura", "Маклюра"),
        ("Lipa", "Липа"),
        ("Qog‘oz daraxti", "Қоғоз дарахти"),
        ("Sovun daraxti", "Совун дарахти"),
        ("Magnoliya", "Магнолия"),
        ("Lola daraxti", "Лола дарахти"),
        ("Ginkgo biloba", "Гинкго билоба"),
        ("Kanada bundugi", "Канада бундуги"),
    ],

    "Tez o‘suvchilar": [
        ("Terak", "Терак"),
        ("Tol", "Тол"),
        ("Majnuntol", "Мажнунтол"),
        ("Pavlovniya", "Павловния"),
    ],

    "Mevalilar": [
        ("O‘rik", "Ўрик"),
        ("Shaftoli", "Шафтоли"),
        ("Olcha", "Олча"),
        ("Olxuri", "Олхури"),
        ("Gilos", "Гилос"),
        ("Magalepka gilos", "Магалепка гилос"),
        ("Xurmo", "Хурмо"),
        ("Olma", "Олма"),
        ("Bexi", "Бехи"),
        ("Nok", "Нок"),
        ("Uzum", "Узум"),
        ("Anor", "Анор"),
        ("Anjir", "Анжир"),
        ("Qizil do‘lona", "Қизил дўлана"),
        ("Tut", "Тут"),
        ("Chappa tut", "Чаппа тут"),
        ("Jiyda", "Жийда"),
        ("Non jiyda", "Нон жийда"),
        ("Chilonjiyda", "Чилонжийда"),
        ("Palma", "Палма"),
        ("Limon", "Лимон"),
    ],

    "Yong‘oq mevalilar": [
        ("Yong‘oq", "Ёнгок"),
        ("Achchiq bodom", "Аччиқ бодом"),
        ("Shirin bodom", "Ширин бодом"),
        ("Pekan", "Пекан"),
        ("Pista", "Писта"),
        ("Funduk", "Фундук"),
    ],

    "Cho‘l o‘simliklari": [
        ("Saxsavul", "Саксавул"),
        ("Cherkez", "Черкез"),
        ("Yulg‘un", "Юлғун"),
        ("Qoraburoq", "Қорабуроқ"),
        ("Qandim", "Қандим"),
    ],

    "Buta va gullar": [
        ("Na‘matak", "Наъматак"),
        ("Amorfa", "Аморфа"),
        ("Ligustrum", "Лигуструм"),
        ("Beresklet", "Бересклет"),
        ("Yapon bexi", "Япон бехи"),
        ("Magoniya", "Магония"),
        ("Forzitsiya", "Форзиция"),
        ("Samshit", "Самшит"),
        ("Sireni", "Сирень"),
        ("Hind sireni", "Ҳинд сирени"),
        ("Atirgul", "Атиргул"),
        ("Suriya gibiskusi", "Сурия гибискуси"),
        ("Tsizalpiniya", "Цизалпиния"),
        ("Chakanda", "Чаканда"),
        ("Ispan drok", "Испан дрок"),
        ("Sumax", "Сумах"),
        ("Yukka", "Юкка"),
        ("Smorodina", "Смородина"),
        ("Arxideya", "Архидея"),
        ("Ryabina", "Рябина"),
        ("Pirakanta", "Пираканта"),
        ("Lavanda", "Лаванда"),
        ("Zirk", "Зирк"),
        ("Boshqalar", "Бошқалар"),
    ]
}


class Command(BaseCommand):
    help = "Create/update plants for `Urug' xarakati Reja` statement (safe, idempotent, logged)"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Syncing plants for Urug' xarakati Reja...")

        try:
            statement = Statement.objects.get(name_uz="Urug' xarakati Reja")
        except Statement.DoesNotExist:
            self.stderr.write(
                self.style.ERROR("❌ Statement 'Urug' xarakati Reja' not found.")
            )
            return

        created_count = 0
        updated_count = 0

        for parent_name, children in CATEGORY_STRUCTURE.items():

            # =====================
            # PARENT SAFE FETCH
            # =====================
            parent_qs = Plant.objects.filter(
                name=parent_name,
                parent__isnull=True,
                statement=statement
            )

            if parent_qs.exists():
                parent = parent_qs.first()
                if parent_qs.count() > 1:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️ Duplicate parent: {parent_name} ({parent_qs.count()})"
                        )
                    )
            else:
                parent = Plant.objects.create(
                    name=parent_name,
                    parent=None,
                    statement=statement
                )
                created_count += 1
                self.stdout.write(f"➕ Parent created: {parent_name}")

            # Parent update detect
            parent_changed = False
            if getattr(parent, build_localized_fieldname("name", "uz")) != parent_name:
                setattr(parent, build_localized_fieldname("name", "uz"), parent_name)
                parent_changed = True

            if getattr(parent, build_localized_fieldname("name", "ru")) != parent_name:
                setattr(parent, build_localized_fieldname("name", "ru"), parent_name)
                parent_changed = True

            if parent.statement_id != statement.id:
                parent.statement = statement
                parent_changed = True

            if parent_changed:
                parent.save()
                updated_count += 1
                self.stdout.write(f"🔁 Parent updated: {parent_name}")

            # =====================
            # CHILD SAFE FETCH
            # =====================
            for name_uz, name_ru in children:

                child_qs = Plant.objects.filter(
                    name=name_uz,
                    parent=parent,
                    statement=statement
                )

                if child_qs.exists():
                    child = child_qs.first()
                    if child_qs.count() > 1:
                        self.stdout.write(
                            self.style.WARNING(
                                f"⚠️ Duplicate child: {name_uz} ({child_qs.count()})"
                            )
                        )
                    created = False
                else:
                    child = Plant.objects.create(
                        name=name_uz,
                        parent=parent,
                        statement=statement
                    )
                    created = True
                    created_count += 1
                    self.stdout.write(f"➕ Created: {name_uz}")

                # Detect updates
                changed = False

                if getattr(child, build_localized_fieldname("name", "uz")) != name_uz:
                    setattr(child, build_localized_fieldname("name", "uz"), name_uz)
                    changed = True

                if getattr(child, build_localized_fieldname("name", "ru")) != name_ru:
                    setattr(child, build_localized_fieldname("name", "ru"), name_ru)
                    changed = True

                if child.statement_id != statement.id:
                    child.statement = statement
                    changed = True

                if changed:
                    child.save()
                    if not created:
                        updated_count += 1
                        self.stdout.write(f"🔁 Updated: {name_uz}")

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Done. Created: {created_count}, Updated: {updated_count}"
            )
        )
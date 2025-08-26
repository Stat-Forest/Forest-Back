from django.core.management import BaseCommand

from apps.reports.constants.plant_title_translations import plant_translations
from apps.reports.models import Statement, StatementColumn
from apps.utils.services import PeriodChoices


def create_subcolumns(statement, parent, ordering, custom_titles=None):
    if custom_titles is None:
        custom_titles = [("soni", "количество"), ("summa", "сумма")]

    for idx, (title_uz, title_ru) in enumerate(custom_titles, start=1):
        StatementColumn.objects.create(
            statement=statement,
            parent=parent,
            title_uz=title_uz,
            title_ru=title_ru,
            ordering=f"{ordering}.{idx}"
        )


def create_column_group(statement, parent, columns, section_title_uz=None, user_input_flags=None):
    for idx, (title_uz, ordering) in enumerate(columns):
        title_ru = plant_translations.get(title_uz, title_uz)
        is_user_input = user_input_flags[idx] if user_input_flags else True

        node = StatementColumn.objects.create(
            statement=statement,
            parent=parent,
            title_uz=title_uz,
            title_ru=title_ru,
            ordering=ordering,
            is_user_input=is_user_input
        )

        is_jami_uz = title_uz.strip().lower() == "jami"
        is_jami_ru = title_ru.strip().lower() in ["итого", "jami"]

        if (
            (is_jami_uz or is_jami_ru)
            and section_title_uz in ["Tez o‘suvchilar", "Yong‘oqmevalilar", "Mevalilar"]
        ):
            create_subcolumns(
                statement,
                node,
                ordering,
                custom_titles=[
                    ("ko‘chat soni", "кол-во саженцев"),
                    ("ko‘chat narxi", "цена саженцев"),
                ]
            )
        else:
            create_subcolumns(statement, node, ordering)

class Command(BaseCommand):
    def handle(self, *args, **options):
        parent_statement = Statement.objects.get(
            name_uz="O'rmon barpo qilish",
            name_ru="Создание леса",
            period=PeriodChoices.YILLIK
        )

        statement = Statement.objects.create(
            parent=parent_statement,
            name_uz="Sotish uchun yaroqli ko‘chatlar",
            name_ru="Ростки и саженцы, пригодные для продажи",
        )

        app_column = StatementColumn.objects.create(
            statement=statement,
            parent=None,
            title_uz="6-ilova",
            title_ru="Приложение 6",
            ordering="1"
        )

        title_column = StatementColumn.objects.create(
            statement=statement,
            parent=app_column,
            title_uz="O‘rmon xo‘jaliklari tomonidan joriy yilda mavjud sotishga yaroqli mevali manzarali ko‘chatlar va butalar to‘g‘risida ma‘lumot",
            title_ru="Информация о наличии плодовых и декоративных ростков и кустарников, пригодных для продажи, в лесничествах в текущем году",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=statement,
            parent=title_column,
            title_uz="Tashkilot nomi",
            title_ru="Название организации",
            ordering="1.1.1",
            is_organization=True
        )

        jami = StatementColumn.objects.create(
            statement=statement,
            parent=title_column,
            title_uz="Jami",
            title_ru="Итого",
            ordering="1.1.2",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=jami,
            title_uz="soni (ming dona)",
            title_ru="количество (тыс. шт)",
            ordering="1.1.2.1",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=jami,
            title_uz="summa (ming so‘m)",
            title_ru="сумма (тыс. сум)",
            ordering="1.1.2.2",
            is_user_input=False
        )

        sections = [
            ("Ignabarglilar", "1.1.3", [
                ("Jami", "1.1.3.1"), ("Tyanşhan qora qarag‘ay", "1.1.3.2"),
                ("Moyiv qarag‘ay", "1.1.3.3"), ("Zarafşon archa", "1.1.3.4"),
                ("Vergin archa", "1.1.3.5"), ("Şarq tuya", "1.1.3.6"),
                ("Kompyakt tuya", "1.1.3.7"), ("Krim qarag‘ay", "1.1.3.8"),
                ("Eldor qarag‘ay", "1.1.3.9"), ("Arizon sarvi", "1.1.3.10"),
                ("Botkok sarvi", "1.1.3.11"), ("Pixta", "1.1.3.12"),
            ]),
            ("Tez o‘suvchilar", "1.1.4", [
                ("Jami", "1.1.4.1"), ("Terak", "1.1.4.2"), ("Qayrog‘och (vaz)", "1.1.4.3"),
                ("Sada qayrog‘och", "1.1.4.4"), ("Şumtol (yasen)", "1.1.4.5"),
                ("Aylant", "1.1.4.6"), ("Gledichiya", "1.1.4.7"), ("Uluğ", "1.1.4.8"),
                ("Majnutol", "1.1.4.9"), ("Yapon safarasi", "1.1.4.10"),
                ("Pavloniya", "1.1.4.11"), ("Savat tol", "1.1.4.12"),
            ]),
            ("Yong‘oqmevalilar", "1.1.5", [
                ("Jami", "1.1.5.1"), ("yong‘oq", "1.1.5.2"), ("yong‘oq", "1.1.5.3"),
                ("achchiq bodom", "1.1.5.4"), ("Şirin bodom", "1.1.5.5"),
                ("xondan pista", "1.1.5.6"), ("pekan", "1.1.5.7"), ("funduk", "1.1.5.8"),
            ]),
            ("Mevalilar", "1.1.6", [
                ("Jami", "1.1.6.1"), ("o‘rik (abrikos)", "1.1.6.2"), ("şaftoli", "1.1.6.3"),
                ("olcha (vishnevyy)", "1.1.6.4"), ("olxuri", "1.1.6.5"), ("pissarda olxurisi", "1.1.6.6"),
                ("gilos (gayin)", "1.1.6.7"), ("magalevka gilos", "1.1.6.8"), ("xurmo", "1.1.6.9"),
                ("Olma", "1.1.6.10"), ("behi", "1.1.6.11"), ("Tok", "1.1.6.12"),
                ("nok (murut)", "1.1.6.13"), ("Dulana", "1.1.6.14"),
                ("jiyda (lox)", "1.1.6.15"), ("anor", "1.1.6.16"),
                ("chilonjiyda (unabi)", "1.1.6.17"), ("non jiyda", "1.1.6.18"),
            ]),
            ("Cho‘l o‘simliklari", "1.1.7", [
                ("Jami", "1.1.7.1"), ("saksovul", "1.1.7.2"),
            ]),
            ("Yaprog‘barqlilar", "1.1.8", [
                ("Jami", "1.1.8.1"), ("bag‘ryannik", "1.1.8.2"), ("eman chereshch (Dub)", "1.1.8.3"),
                ("eman piramida", "1.1.8.4"), ("kashtan", "1.1.8.5"), ("katalpa", "1.1.8.6"),
                ("xelokatalpa", "1.1.8.7"), ("qatronğı (uchqat)", "1.1.8.8"),
                ("oq qayin (beryozka)", "1.1.8.9"), ("zarang (klen)", "1.1.8.10"),
                ("ipak akasiya", "1.1.8.11"), ("akasiya", "1.1.8.12"), ("maklyura", "1.1.8.13"),
                ("lipa (juka)", "1.1.8.14"), ("lola daraxti", "1.1.8.15"),
                ("qog‘oz daraxt", "1.1.8.16"), ("sovun daraxti", "1.1.8.17"),
                ("tug‘onda", "1.1.8.18"), ("magnoliya", "1.1.8.19"),
            ]),
            ("Buta va gullar", "1.1.9", [
                ("Jami", "1.1.9.1"), ("na‘matak", "1.1.9.2"), ("amorfa", "1.1.9.3"),
                ("biryuchina (ligustrum)", "1.1.9.4"), ("gibiskus", "1.1.9.5"),
                ("beresket", "1.1.9.6"), ("Zirk", "1.1.9.7"), ("yapon behi", "1.1.9.8"),
                ("suriya atirguli", "1.1.9.9"), ("magniya", "1.1.9.10"), ("sireng", "1.1.9.11"),
                ("hind sireni", "1.1.9.12"), ("atirgul", "1.1.9.13"), ("forziçiya", "1.1.9.14"),
                ("ispan drogi", "1.1.9.15"), ("çakanda (oblepixa)", "1.1.9.16"),
                ("çizalpiniya", "1.1.9.17"), ("ryabina (lapina)", "1.1.9.18"),
                ("pirakanta", "1.1.9.19"), ("lavanda", "1.1.9.20"),
                ("Samşod", "1.1.9.21"), ("smorodina", "1.1.9.22"),
            ]),
        ]

        for section_title_uz, section_ordering, column_items in sections:
            section_title_ru = {
                "Ignabarglilar": "Хвойные",
                "Tez o‘suvchilar": "Быстрорастущие",
                "Yong‘oqmevalilar": "Ореховые",
                "Mevalilar": "Плодовые",
                "Cho‘l o‘simliklari": "Пустынные растения",
                "Yaprog‘barqlilar": "Лиственные",
                "Buta va gullar": "Кустарники и цветы"
            }.get(section_title_uz, section_title_uz)

            section = StatementColumn.objects.create(
                statement=statement,
                parent=title_column,
                title_uz=section_title_uz,
                title_ru=section_title_ru,
                ordering=section_ordering
            )

            # Jami bloklarining user_input ni aniqlash
            def is_jami_row(title_uz):
                return title_uz.strip().lower() == "jami"

            # Har bir elementga `is_user_input=False` ni Jami uchun va uning keyingi 2 ustuni uchun belgilash
            input_flags = []
            skip = 0
            for title_uz, _ in column_items:
                if skip > 0:
                    input_flags.append(False)
                    skip -= 1
                elif is_jami_row(title_uz):
                    input_flags.append(False)
                    skip = 2
                else:
                    input_flags.append(True)

            create_column_group(
                statement,
                section,
                column_items,
                section_title_uz=section_title_uz,
                user_input_flags=input_flags
            )
            create_column_group(statement, section, column_items, section_title_uz=section_title_uz)

        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'Ростки и саженцы, пригодные для продажи' statement."))
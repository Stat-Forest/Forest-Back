from django.core.management import BaseCommand
from apps.reports.models import Statement, StatementColumn
from apps.utils.services import PeriodChoices


def create_subcolumns(statement, parent, ordering):
    StatementColumn.objects.create(
        statement=statement,
        parent=parent,
        title_uz="soni",
        title_ru="количество",
        ordering=f"{ordering}.1"
    )
    StatementColumn.objects.create(
        statement=statement,
        parent=parent,
        title_uz="summa",
        title_ru="сумма",
        ordering=f"{ordering}.2"
    )


def create_column_group(statement, parent, columns):
    for title_uz, ordering in columns:
        title_ru = {
            "Jami": "Итого",
            "Tyanşhan qora qarag‘ay": "Тяньшанский черный карагач",
            "Moyiv qarag‘ay": "Синий карагач",
            "Zarafşon archa": "Зеравшанская арча",
            "Vergin archa": "Верджинская арча",
            "Şarq tuya": "Восточная туя",
            "Kompyakt tuya": "Компактная туя",
            "Krim qarag‘ay": "Крымский карагач",
            "Eldor qarag‘ay": "Елдорский карагач",
            "Arizon sarvi": "Аризонский кипарис",
            "Botkok sarvi": "Боткокский кипарис",
            "Pixta": "Ель",
            "Terak": "Тополь",
            "Qayrog‘och (vaz)": "Вяз (кайрагач)",
            "Sada qayrog‘och": "Садовый вяз",
            "Şumtol (yasen)": "Ясень (шумтол)",
            "Aylant": "Айлант",
            "Gledichiya": "Гледичия",
            "Uluğ": "Тополь черный",
            "Majnutol": "Маджунус",
            "Yapon safarasi": "Японский кипарис",
            "Pavloniya": "Павлония",
            "Savat tol": "Ива",
            "yong‘oq": "Орех",
            "achchiq bodom": "Горький миндаль",
            "Şirin bodom": "Сладкий миндаль",
            "xondan pista": "Хондонский фисташка",
            "pekan": "Пекан",
            "funduk": "Лесной орех",
            "o‘rik (abrikos)": "Абрикос (урюк)",
            "şaftoli": "Персик",
            "olcha (vishnevyy)": "Вишня (олча)",
            "olxuri": "Слива",
            "pissarda olxurisi": "Писсарда слива",
            "gilos (gayin)": "Черешня (гайн)",
            "magalevka gilos": "Магалебская черешня",
            "xurmo": "Хурма",
            "Olma": "Яблоня",
            "behi": "Айва",
            "Tok": "Виноград",
            "nok (murut)": "Груша (мурут)",
            "Dulana": "Тут белый",
            "jiyda (lox)": "Ясень (лох)",
            "anor": "Гранат",
            "chilonjiyda (unabi)": "Инжир (унаби)",
            "non jiyda": "Хлебное дерево",
            "saksovul": "Саксаул",
            "bag‘ryannik": "Багрянник",
            "eman chereshch (Dub)": "Манчжурский дуб",
            "eman piramida": "Пирамидальный дуб",
            "kashtan": "Каштан",
            "katalpa": "Катальпа",
            "xelokatalpa": "Гибридная катальпа",
            "qatronğı (uchqat)": "Тис (учкват)",
            "oq qayin (beryozka)": "Белая береза",
            "zarang (klen)": "Клен (заранг)",
            "ipak akasiya": "Шелковая акация",
            "akasiya": "Акация",
            "maklyura": "Маклюра",
            "lipa (juka)": "Липа (жужа)",
            "lola daraxti": "Тюльпанное дерево",
            "qog‘oz daraxt": "Бумажное дерево",
            "sovun daraxti": "Софора",
            "tug‘onda": "Туганда",
            "magnoliya": "Магнолия",
            "na‘matak": "Нематака",
            "amorfa": "Аморфа",
            "biryuchina (ligustrum)": "Бирючина (лигуструм)",
            "gibiskus": "Гибискус",
            "beresket": "Бересклет",
            "Zirk": "Зирк",
            "yapon behi": "Японская айва",
            "suriya atirguli": "Сирийская роза",
            "magniya": "Магнолия",
            "sireng": "Сирень",
            "hind sireni": "Индийская сирень",
            "atirgul": "Роза",
            "forziçiya": "Форзиция",
            "ispan drogi": "Испанский дрок",
            "çakanda (oblepixa)": "Облепиха (чакада)",
            "çizalpiniya": "Цизальпиния",
            "ryabina (lapina)": "Рябина (лапина)",
            "pirakanta": "Пирант",
            "lavanda": "Лаванда",
            "Samşod": "Самшит",
            "smorodina": "Смородина"
        }.get(title_uz, title_uz)
        node = StatementColumn.objects.create(
            statement=statement,
            parent=parent,
            title_uz=title_uz,
            title_ru=title_ru,
            ordering=ordering
        )
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
            ordering="1.1.2"
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=jami,
            title_uz="soni (ming dona)",
            title_ru="количество (тыс. шт)",
            ordering="1.1.2.1"
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=jami,
            title_uz="summa (ming so‘m)",
            title_ru="сумма (тыс. сум)",
            ordering="1.1.2.2"
        )

        sections = [
            ("Ignabarqlilar", "1.1.3", [
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
                "Ignabarqlilar": "Хвойные",
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
            create_column_group(statement, section, column_items)

        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'Ростки и саженцы, пригодные для продажи' statement."))
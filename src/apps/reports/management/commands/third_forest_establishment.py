from django.core.management import BaseCommand
from apps.reports.models import Statement, StatementColumn


def create_subcolumns(statement, parent, ordering):
    StatementColumn.objects.create(
        statement=statement, parent=parent, title="сони", ordering=f"{ordering}.1"
    )
    StatementColumn.objects.create(
        statement=statement, parent=parent, title="сумма", ordering=f"{ordering}.2"
    )


def create_column_group(statement, parent, columns):
    for title, ordering in columns:
        node = StatementColumn.objects.create(
            statement=statement, parent=parent, title=title, ordering=ordering
        )
        create_subcolumns(statement, node, ordering)


class Command(BaseCommand):
    def handle(self, *args, **options):
        parent_statement = Statement.objects.get(name="O`rmon barpo qilish")

        statement = Statement.objects.create(
            parent=parent_statement,
            name="Sotish uchun yaroqli ko`chatlar"
        )

        app_column = StatementColumn.objects.create(
            statement=statement,
            parent=None,
            title="6-ilova",
            ordering="1"
        )

        title_column = StatementColumn.objects.create(
            statement=statement,
            parent=app_column,
            title=(
                "Ўрмон хўжаликлари томонидан жорий йилда мавжуд сотишга яроқли "
                "мевали манзарали кўчатлар ва буталар тўғрисида маълумот"
            ),
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=statement,
            parent=title_column,
            title="Ташкилот номи",
            ordering="1.1.1",
            is_organization=True
        )

        jami = StatementColumn.objects.create(
            statement=statement, parent=title_column, title="Жами", ordering="1.1.2"
        )
        StatementColumn.objects.create(
            statement=statement, parent=jami, title="сони (минг дона)", ordering="1.1.2.1"
        )
        StatementColumn.objects.create(
            statement=statement, parent=jami, title="сумма (минг сўм)", ordering="1.1.2.2"
        )

        sections = [
            ("Игнабарглилар", "1.1.3", [
                ("Жами", "1.1.3.1"), ("Тяншан қора қарағай", "1.1.3.2"),
                ("Мовий қарағай", "1.1.3.3"), ("Зарафшон арча", "1.1.3.4"),
                ("Вергин арча", "1.1.3.5"), ("Шарқ туя", "1.1.3.6"),
                ("Компакт туя", "1.1.3.7"), ("Крим қарағай", "1.1.3.8"),
                ("Элдор қарағай", "1.1.3.9"), ("Аризон сарви", "1.1.3.10"),
                ("Боткок сарви", "1.1.3.11"), ("Пихта", "1.1.3.12"),
            ]),
            ("Тез ўсувчилар", "1.1.4", [
                ("Жами", "1.1.4.1"), ("Терак", "1.1.4.2"), ("Қайроғоч (вяз)", "1.1.4.3"),
                ("Сада қайроғоч", "1.1.4.4"), ("Шумтол (ясень)", "1.1.4.5"),
                ("Айлант", "1.1.4.6"), ("Гледичия", "1.1.4.7"), ("Улуғ", "1.1.4.8"),
                ("Мажнунтол", "1.1.4.9"), ("Япон сафораси", "1.1.4.10"),
                ("Павлония", "1.1.4.11"), ("Саваттол", "1.1.4.12"),
            ]),
            ("Ёнғоқмевалилар", "1.1.5", [
                ("Жами", "1.1.5.1"), ("ёнгок", "1.1.5.2"), ("ёнгок", "1.1.5.3"),
                ("аччиқ бодом", "1.1.5.4"), ("Ширин бодом", "1.1.5.5"),
                ("хондон писта", "1.1.5.6"), ("пекан", "1.1.5.7"), ("фундук", "1.1.5.8"),
            ]),
            ("Мевалилар", "1.1.6", [
                ("Жами", "1.1.6.1"), ("ўрик (абрикос)", "1.1.6.2"), ("шафтоли", "1.1.6.3"),
                ("олча (вишневый)", "1.1.6.4"), ("олхури", "1.1.6.5"), ("писсарда олхуриси", "1.1.6.6"),
                ("гилос (гаин)", "1.1.6.7"), ("магалепка гилос", "1.1.6.8"), ("хурмо", "1.1.6.9"),
                ("Олма", "1.1.6.10"), ("бехи", "1.1.6.11"), ("Ток", "1.1.6.12"),
                ("нок (мурут)", "1.1.6.13"), ("Дўлана", "1.1.6.14"),
                ("жийда (лох)", "1.1.6.15"), ("анор", "1.1.6.16"),
                ("чилонжийда (унаби)", "1.1.6.17"), ("нон жийда", "1.1.6.18"),
            ]),
            ("Чўл ўсимликлари", "1.1.7", [
                ("Жами", "1.1.7.1"), ("саксовул", "1.1.7.2"),
            ]),
            ("Япроқбарглилар", "1.1.8", [
                ("Жами", "1.1.8.1"), ("богриянник", "1.1.8.2"), ("эман черешч (Дуб)", "1.1.8.3"),
                ("эман пирамида.", "1.1.8.4"), ("каштан", "1.1.8.5"), ("катальпа", "1.1.8.6"),
                ("хелокатальпа", "1.1.8.7"), ("қатронғи (учқат)", "1.1.8.8"),
                ("оқ қайин (берёза)", "1.1.8.9"), ("заранг (клен)", "1.1.8.10"),
                ("ипак акация", "1.1.8.11"), ("акация", "1.1.8.12"), ("маклюра", "1.1.8.13"),
                ("липа (жўка)", "1.1.8.14"), ("лола дарахти", "1.1.8.15"),
                ("қогоз дарахт", "1.1.8.16"), ("совун дарахти", "1.1.8.17"),
                ("туғонда", "1.1.8.18"), ("магнолия", "1.1.8.19"),
            ]),
            ("Бута ва гуллар", "1.1.9", [
                ("Жами", "1.1.9.1"), ("наъматак", "1.1.9.2"), ("аморфа", "1.1.9.3"),
                ("бирючина (лигуструм).", "1.1.9.4"), ("гибискус", "1.1.9.5"),
                ("бересклет", "1.1.9.6"), ("Зирк", "1.1.9.7"), ("япон бехи", "1.1.9.8"),
                ("сурия атиргули", "1.1.9.9"), ("магония", "1.1.9.10"), ("сирень", "1.1.9.11"),
                ("ҳинд сирени", "1.1.9.12"), ("атиргул", "1.1.9.13"), ("форзиция", "1.1.9.14"),
                ("испан дроги", "1.1.9.15"), ("чаканда (облепиха)", "1.1.9.16"),
                ("цизалпения", "1.1.9.17"), ("рябина (лапина)", "1.1.9.18"),
                ("пираканта", "1.1.9.19"), ("лованда", "1.1.9.20"),
                ("Самшод", "1.1.9.21"), ("смородина", "1.1.9.22"),
            ]),
        ]

        for section_title, section_ordering, column_items in sections:
            section = StatementColumn.objects.create(
                statement=statement, parent=title_column, title=section_title, ordering=section_ordering
            )
            create_column_group(statement, section, column_items)

        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Sotish uchun yaroqli ko`chatlar' statement."))

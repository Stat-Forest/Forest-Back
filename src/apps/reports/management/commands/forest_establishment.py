from django.core.management import BaseCommand
from django.utils import timezone

from apps.reports.models import Statement, StatementColumn
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    help = "Создание заявления об учреждении леса"

    def handle(self, *args, **options):

        current_year = timezone.now().strftime("%Y")

        first_statement = Statement.objects.create(
            parent=None,
            name_uz="O'rmon barpo qilish",
            name_ru="Создание леса",
            period=PeriodChoices.YILLIK
        )
        first_of_second_statement = Statement.objects.create(
            parent=first_statement,
            name_uz="Yopiq ildiz yirik hajmli",
            name_ru="Закрытый корень крупногабаритный",
            period=PeriodChoices.YILLIK
        )

        app_column = StatementColumn.objects.create(
            statement=first_of_second_statement,
            parent=None,
            title_uz="1-ilova",
            title_ru="Приложение 1",
            ordering="1"
        )

        title_column = StatementColumn.objects.create(
            statement=first_of_second_statement,
            parent=app_column,
            title_uz=(
                f"O'rmon xo'jaligi agentligi tizimidagi o'rmon xo'jaliklari tomonidan "
                f"{current_year} yildan yirik hajmli yopiq ko'chatlarni yetishtirish to'g'risida "
                "tezkor ma'lumot."
            ),
            title_ru=(
                f"Срочная информация о выращивании крупногабаритных закрытых саженцев "
                f"лесничествами в системе Агентства лесного хозяйства с {current_year} года."
            ),
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=first_of_second_statement,
            parent=title_column,
            title_uz="Tashkilot nomi",
            title_ru="Названия регионов",
            ordering="1.1.1",
            is_organization=True
        )

        rows = [
            ("Yirik hajmli yopiq ildizli ko'chatlar yetishtirish miqdori",
             "Количество выращивания крупногабаритных саженцев с закрытым корнем", False, "YILLIK"),

            # Yaproqbarglilar
            ("bagrannik", "багрянник", True, "YILLIK"),
            ("eman chereshch (dub)", "эман черешч (дуб)", True, "YILLIK"),
            ("eman piramid (dub)", "эман пирамид (дуб)", True, "YILLIK"),
            ("qayrogoch (vyaz)", "қайрогоч (вяз)", True, "YILLIK"),
            ("sada qayrog‘och (gujum)", "сада қайроғоч (гужум)", True, "YILLIK"),
            ("shumtol (yasen)", "шумтол (ясень)", True, "YILLIK"),
            ("aylant", "айлант", True, "YILLIK"),
            ("savatol", "саваттол", True, "YILLIK"),
            ("gledichiya", "гледичия", True, "YILLIK"),
            ("chinor", "чинор", True, "YILLIK"),
            ("yapon saforasi", "япон сафораси", True, "YILLIK"),
            ("kashtan", "каштан", True, "YILLIK"),
            ("katalpa", "катальпа", True, "YILLIK"),
            ("xilo katalpa", "хило каталпа", True, "YILLIK"),
            ("oq qayin (beryoza)", "оқ қайин (берёза)", True, "YILLIK"),
            ("zarang (klen)", "заранг (клен)", True, "YILLIK"),
            ("ipak akatsiya", "ипак акация", True, "YILLIK"),
            ("akatsiya", "акация", True, "YILLIK"),
            ("maklyura", "маклюра", True, "YILLIK"),
            ("lipa", "липа", True, "YILLIK"),
            ("qog‘oz daraxt", "қогоз дарахт", True, "YILLIK"),
            ("sovun daraxti", "совун дарахти", True, "YILLIK"),
            ("magnoliya", "магнолия", True, "YILLIK"),
            ("lola daraxti", "лола дарахти", True, "YILLIK"),

            # Tez o‘suvchilar
            ("pavlovniya", "павловния", True, "YILLIK"),

            # Yong‘oqmevalilar
            ("yong‘oq", "ёнгок", True, "YILLIK"),
            ("achchiq bodom", "аччиқ бодом", True, "YILLIK"),
            ("shirin bodom", "ширин бодом", True, "YILLIK"),
            ("pekan", "пекан", True, "YILLIK"),
            ("pista", "писта", True, "YILLIK"),
            ("funduk", "фундук", True, "YILLIK"),

            # Mevalilar
            ("o‘rik (abrikos)", "ўрик (абрикос)", True, "YILLIK"),
            ("shaftoli", "шафтоли", True, "YILLIK"),
            ("olchcha (vishnya)", "олча (вишневый)", True, "YILLIK"),
            ("olxuri, qorali GAYLOLU", "олхури, қорали ГАЙЛОЛУ", True, "YILLIK"),
            ("pissarda olxurisi", "писсарда олхуриси", True, "YILLIK"),
            ("gilos (vishnya)", "гилос  (вышня)", True, "YILLIK"),
            ("magalepka gilos", "магалепка гилос", True, "YILLIK"),
            ("xurmo", "хурмо", True, "YILLIK"),
            ("olma", "олма", True, "YILLIK"),
            ("bexi", "бехи", True, "YILLIK"),
            ("nok (murut)", "нок (мурут)", True, "YILLIK"),
            ("uzum (tok)", "узум (ток)", True, "YILLIK"),
            ("anor", "анор", True, "YILLIK"),
            ("anjir", "анжир", True, "YILLIK"),
            ("qizil do‘lona", "қизил дўлана", True, "YILLIK"),
            ("tut", "тут", True, "YILLIK"),
            ("chappa tut", "чаппа тут", True, "YILLIK"),
            ("jiyda (lox)", "жийда (лох)", True, "YILLIK"),
            ("non jiyda", "нон жийда", True, "YILLIK"),
            ("chilonjiyda (unabi)", "чилонжийда (унаби)", True, "YILLIK"),
            ("palma", "Палма", True, "YILLIK"),
            ("limon", "лимон", True, "YILLIK"),

            # Ignabarglilar
            ("tyanshan qora qarag‘ayi", "тяншан қора қарағайи", True, "YILLIK"),
            ("zarafshon archasi", "Зарафшон арчаси", True, "YILLIK"),
            ("virgin archa", "виргин арча", True, "YILLIK"),
            ("sharq tuya", "шарқ туя", True, "YILLIK"),
            ("kompakt tuya", "компакт туя", True, "YILLIK"),
            ("qrim qarag‘ayi", "қрим қарағайи", True, "YILLIK"),
            ("eldor qarag‘ayi", "эльдор қарағайи", True, "YILLIK"),
            ("sarvi (kiparis)", "сарви (кипарис)", True, "YILLIK"),
            ("tog‘ archa", "тоғ арча", True, "YILLIK"),

            # Buta va gullar
            ("na‘matak (shipovnik)", "наъматак (шиповник)", True, "YILLIK"),
            ("amorfa", "аморфа", True, "YILLIK"),
            ("ligustrum (biryuchina)", "лигуструм (бирючина)", True, "YILLIK"),
            ("beresklet", "бересклет", True, "YILLIK"),
            ("yapon bexi", "япон бехи", True, "YILLIK"),
            ("magoniya", "магония", True, "YILLIK"),
            ("forzitsiya", "форзиция", True, "YILLIK"),
            ("samshit", "самшит", True, "YILLIK"),
            ("sireni", "сирень", True, "YILLIK"),
            ("hind sireni", "ҳинд сирени", True, "YILLIK"),
            ("atirgul", "атиргул", True, "YILLIK"),
            ("suriya atirguli (gibiskus)", "сурия атиргули (гибискус)", True, "YILLIK"),
            ("tsizalpiniya", "цизалпиния", True, "YILLIK"),
            ("chakanda (oblepixa)", "чаканда (облепиха)", True, "YILLIK"),
            ("ispan drek", "испан дрок", True, "YILLIK"),
            ("sumax", "сумах", True, "YILLIK"),
            ("yukka", "юкка", True, "YILLIK"),
            ("smorodina", "смородина", True, "YILLIK"),
            ("arxideya", "архидея", True, "YILLIK"),
            ("ryabina", "рябина", True, "YILLIK"),
            ("pirakanta", "пираканта", True, "YILLIK"),
            ("lovanda", "лованда", True, "YILLIK"),
            ("zirk", "зирк", True, "YILLIK"),
            ("boshqalar", "бошқалар", True, "YILLIK"),
        ]

        for index, (title_uz, title_ru, has_children, plan_status) in enumerate(rows, start=2):
            parent_ordering = f"1.1.{index}"
            parent = StatementColumn.objects.create(
                statement=first_of_second_statement,
                parent=title_column,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=parent_ordering,
                is_user_input=has_children
            )

            if title_uz == "Yirik hajmli yopiq ildizli ko'chatlar yetishtirish miqdori":
                for i, sub in enumerate(["Reja", "Amalda", "%"], start=1):
                    sub_ordering = f"{parent_ordering}.{i}"

                    status_plan = (
                        StatementColumn.PlanStatus.YILLIK
                        if plan_status == "YILLIK" and sub == "Reja"
                        else None
                    )

                    StatementColumn.objects.create(
                        statement=first_of_second_statement,
                        parent=parent,
                        title_uz=sub,
                        title_ru={"Reja": "План", "Amalda": "Факт", "%": "%"}[sub],
                        ordering=sub_ordering,
                        status_plan=status_plan,
                        is_user_input=(sub in ["Reja", "%"])
                    )

        # ================================================================ Закрытый корень крупногабаритный

        # =========================== 2-Ilova =============================
        second_statement_of_forest = Statement.objects.create(
            parent=first_statement,
            name_uz="O'rmon barpo qilish bo'limi",
            name_ru="Отдел создания леса",
            period=PeriodChoices.YILLIK
        )

        second_app_column = StatementColumn.objects.create(
            statement=second_statement_of_forest,
            parent=None,
            title_uz="2-ilova",
            title_ru="Приложение 2",
            ordering="1"
        )

        second_ilova_title = StatementColumn.objects.create(
            statement=second_statement_of_forest,
            parent=second_app_column,
            title_uz="O'rmon xo'jaliklari tomonidan joriy yilda o'rmon barpo etilishi to'g'risida ma'lumot",
            title_ru="Информация о создании лесов лесничествами в текущем году",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=second_statement_of_forest,
            parent=second_ilova_title,
            title_uz="Tashkilot nomi",
            title_ru="Названия лесничеств",
            ordering="1.1.1",
            is_organization=True
        )

        rows = [
            ("Jami o'rmonlar barpo etish va qayta tiklash", "Полное лесовосстановление и восстановление", True),
            ("O‘rmonlar (yashil qoplamalar) barpo etish va qayta tiklash (ga)",
             "Создание и восстановление лесов (зеленых покровов) (га)", True),
            ("Himoya o‘rmonzorlarini barpo etish (ga)", "Создание защитных лесов (га)", True),
            ("Orolbo‘yi mintaqasida yashil qoplama barpo etish (ga)", "Создание зеленого покрова в Приаралье (га)",
             True),
            ("Orolning qurigan tubida yashil qoplamalar barpo etish (ga)",
             "Создание зеленого покрова на сухом дне острова (га)", True),

            ("Jami yong‘oq-mevalilar", "Всего орехов и фруктов", False),
            ("Shu jumladan (yong‘oq-mevalilar)", "Включая (ореховые)", True),

            ("Jami tez o'suvchilar", "Итого быстрорастущие", True),
            ("Shu jumladan (tez o‘suvchilar)", "Включая (быстрорастущие)", True),

            ("Tabiiy tiklanishga ko'maklashish va boshqa daraxt turlaridan ekish",
             "Помощь в естественном восстановлении и посадка других видов деревьев", True),
        ]

        ordering_base = "1.1"

        for i, (title_uz, title_ru, has_subcolumns) in enumerate(rows, start=2):
            parent_col = StatementColumn.objects.create(
                statement=second_statement_of_forest,
                parent=second_ilova_title,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=f"{ordering_base}.{i}",
                is_user_input=False if title_uz == "Jami yong‘oq-mevalilar" else has_subcolumns
            )

            # 1️⃣ Jami o‘rmonlar → Reja, Amalda, %
            if title_uz == "Jami o'rmonlar barpo etish va qayta tiklash":
                for j, sub in enumerate(["Reja", "Amalda", "%"], start=1):
                    status_plan = StatementColumn.PlanStatus.YILLIK_TOTAL if sub == "Reja" else None
                    StatementColumn.objects.create(
                        statement=second_statement_of_forest,
                        parent=parent_col,
                        title_uz=sub,
                        title_ru={"Reja": "План", "Amalda": "Факт", "%": "Процент"}[sub],
                        ordering=f"{ordering_base}.{i}.{j}",
                        status_plan=status_plan,
                        is_user_input=(sub == "Reja")
                    )

            # 2️⃣ Oddiy bo‘limlar (ga) → Reja, Amalda
            elif title_uz in [
                "O‘rmonlar (yashil qoplamalar) barpo etish va qayta tiklash (ga)",
                "Himoya o‘rmonzorlarini barpo etish (ga)",
                "Orolbo‘yi mintaqasida yashil qoplama barpo etish (ga)",
                "Orolning qurigan tubida yashil qoplamalar barpo etish (ga)",
            ]:
                for j, sub in enumerate(["Reja", "Amalda"], start=1):
                    status_plan = StatementColumn.PlanStatus.YILLIK if sub == "Reja" else None
                    StatementColumn.objects.create(
                        statement=second_statement_of_forest,
                        parent=parent_col,
                        title_uz=sub,
                        title_ru={"Reja": "План", "Amalda": "Факт"}[sub],
                        ordering=f"{ordering_base}.{i}.{j}",
                        status_plan=status_plan,
                        is_user_input=True
                    )

            # 3️⃣ Shu jumladan (yong‘oq-mevalilar)
            elif title_uz.startswith("Shu jumladan (yong‘oq-mevalilar)"):
                children = ["Yong'oq", "Pista", "Bodom"]
                children_ru = ["Орех", "Писташка", "Миндаль"]
                for j, (child_uz, child_ru) in enumerate(zip(children, children_ru), start=1):
                    StatementColumn.objects.create(
                        statement=second_statement_of_forest,
                        parent=parent_col,
                        title_uz=child_uz,
                        title_ru=child_ru,
                        ordering=f"{ordering_base}.{i}.{j}",
                        is_user_input=True
                    )

            # 4️⃣ Jami tez o‘suvchilar → Reja, Amalda, %
            elif title_uz == "Jami tez o'suvchilar":
                for j, sub in enumerate(["Reja", "Amalda", "%"], start=1):
                    status_plan = StatementColumn.PlanStatus.YILLIK if sub == "Reja" else None
                    StatementColumn.objects.create(
                        statement=second_statement_of_forest,
                        parent=parent_col,
                        title_uz=sub,
                        title_ru={"Reja": "План", "Amalda": "Факт", "%": "Процент"}[sub],
                        ordering=f"{ordering_base}.{i}.{j}",
                        status_plan=status_plan,
                        is_user_input=(sub == "Reja")
                    )

            # 5️⃣ Shu jumladan (tez o‘suvchilar)
            elif title_uz.startswith("Shu jumladan (tez o‘suvchilar)"):
                children = ["Terak", "Pavloniya", "Qayrag'och", "Shumtol", "Chinar", "Akatsiya", "Boshqa turlar"]
                children_ru = ["Тополь", "Павлония", "Кайрагач", "Шумтол", "Чинар", "Акация", "Другие виды"]
                for j, (child_uz, child_ru) in enumerate(zip(children, children_ru), start=1):
                    StatementColumn.objects.create(
                        statement=second_statement_of_forest,
                        parent=parent_col,
                        title_uz=child_uz,
                        title_ru=child_ru,
                        ordering=f"{ordering_base}.{i}.{j}",
                        is_user_input=True
                    )

            # 6️⃣ Tabiiy tiklanishga ko‘maklashish → Reja, Amalda
            elif title_uz == "Tabiiy tiklanishga ko'maklashish va boshqa daraxt turlaridan ekish":
                for j, sub in enumerate(["Reja", "Amalda"], start=1):
                    status_plan = StatementColumn.PlanStatus.YILLIK if sub == "Reja" else None
                    StatementColumn.objects.create(
                        statement=second_statement_of_forest,
                        parent=parent_col,
                        title_uz=sub,
                        title_ru={"Reja": "План", "Amalda": "Факт"}[sub],
                        ordering=f"{ordering_base}.{i}.{j}",
                        status_plan=status_plan,
                        is_user_input=True
                    )

        # ==========================  Urug` xarakati Jami    =============================
        urug_statement = Statement.objects.create(
            parent=first_statement,
            name_uz="Urug' xarakati Reja",
            name_ru="План движения семян",
            period=PeriodChoices.KUNLIK
        )

        app_column_1 = StatementColumn.objects.create(
            statement=urug_statement,
            title_uz="1-ilova",
            title_ru="Приложение 1",
            ordering="1"
        )

        title_column_1 = StatementColumn.objects.create(
            statement=urug_statement,
            parent=app_column_1,
            title_uz=f"O‘rmon xo‘jaligi agentligi tizimidagi o‘rmon xo‘jaliklari tomonidan {current_year}-yilda"
                     " tayyorlanadigan urug‘larni turlari bo‘yicha prognoz ko‘rsatgichlari (kilogramm)",
            title_ru=f"Прогнозные показатели по видам семян, заготавливаемых лесными хозяйствами в системе"
                     f" Агентства по лесному хозяйству в {current_year} году (в килограммах)",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=urug_statement,
            parent=title_column_1,
            title_uz="Tashkilot nomi",
            title_ru="Название организации",
            ordering="1.1.1",
            is_organization=True
        )

        parent = StatementColumn.objects.create(
            statement=urug_statement,
            parent=title_column_1,
            title_uz="Urug' jamg'arish miqdori",
            title_ru="Объем сбора семян",
            ordering="1.1.2"
        )
        for i, title_uz in enumerate(["Reja", "Amalda", "Foiz"], start=1):
            title_ru = {"Reja": "План", "Amalda": "Факт", "Foiz": "Процент"}[title_uz]

            StatementColumn.objects.create(
                statement=urug_statement,
                parent=parent,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=f"1.1.2.{i}",
                status_plan=StatementColumn.PlanStatus.YILLIK if title_uz == "Reja" else None,
                is_user_input=title_uz in ("Reja", "Amalda")
            )


        # =========================== 3-Ilova =============================
        third_statement = Statement.objects.create(
            parent=first_statement,
            name_uz="Urug' harakati",
            name_ru="Движение семян",
            period=PeriodChoices.YILLIK
        )

        third_app_column = StatementColumn.objects.create(
            statement=third_statement,
            title_uz="3-ilova",
            title_ru="Приложение 3",
            ordering="1"
        )

        third_ilova_title = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_app_column,
            title_uz=f"O'rmon xo'jaligida {current_year} yilda tayyorlangan o'rmon daraxt va buta urug'larining harakati to'g'risida",
            title_ru=f"О движении семян лесных деревьев и кустарников, подготовленных в лесном хозяйстве в {current_year} году",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title_uz="Tashkilot nomi",
            title_ru="Название организации",
            ordering="1.1.1",
            is_organization=True
        )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title_uz="Yil boshiga qolgan qoldiq (kg)",
            title_ru="Остаток на начало года (кг)",
            ordering="1.1.3"
        )

        hisobot = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title_uz="Hisobot davrida tayyorlandi va sotib olindi",
            title_ru="Подготовлено и приобретено в отчетный период",
            ordering="1.1.4"
        )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=hisobot,
            title_uz="Jami (kg)",
            title_ru="Итого (кг)",
            ordering="1.1.4.1",
            is_user_input=False
        )

        child1 = StatementColumn.objects.create(
            statement=third_statement,
            parent=hisobot,
            title_uz="Xo'jalik tomonidan tayyorlandi",
            title_ru="Подготовлено хозяйством",
            ordering="1.1.4.1.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=child1,
            title_uz="Jami (kg)",
            title_ru="Итого (кг)",
            ordering="1.1.4.1.1.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=child1,
            title_uz="Sh.J urug'lik uchastkadan",
            title_ru="Из семенных участков Ш.Ж",
            ordering="1.1.4.1.1.2"
        )

        child2 = StatementColumn.objects.create(
            statement=third_statement,
            parent=hisobot,
            title_uz="Boshqa tashkilotdan sotib olindi",
            title_ru="Приобретено у других организаций",
            ordering="1.1.4.1.2"
        )
        for i, title in enumerate(["Miqdori (kg)", "Sarflangan summa"], start=1):
            StatementColumn.objects.create(
                statement=third_statement,
                parent=child2,
                title_uz=title,
                title_ru={"Miqdori (kg)": "Количество (кг)", "Sarflangan summa": "Сумма затрат"}[title],
                ordering=f"1.1.4.1.2.{i}"
            )

        sarflandi = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title_uz="Hisobot davrida sarflandi",
            title_ru="Израсходовано в отчетный период",
            ordering="1.1.5"
        )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=sarflandi,
            title_uz="Jami (kg)",
            title_ru="Итого (кг)",
            ordering="1.1.5.1",
            is_user_input=False
        )

        subtitles = [
            ("Ko'chatzorlar barpo etish uchun", ["Miqdori (kg)", "Ish hajmi (ga)"], "Для создания питомников",
             ["Количество (кг)", "Объем работ (на)"]),
            ("O'rmonzorlar barpo etish uchun", ["Miqdori (kg)", "Ish hajmi (ga)"], "Для создания лесных насаждений",
             ["Количество (кг)", "Объем работ (на)"]),
            ("O'rmonlarni yo'qotilganini tiklash uchun", ["Miqdori (kg)", "Ish hajmi (ga)"],
             "Для восполнения потерь лесов", ["Количество (кг)", "Объем работ (на)"]),
            ("Boshqa tashkilotlarga berildi", ["kg"], "Передано другим организациям", ["кг"]),
            ("Hisobdan chiqarildi", ["kg"], "Списано", ["кг"])
        ]

        for i, (title_uz, children_uz, title_ru, children_ru) in enumerate(subtitles, start=1):
            parent = StatementColumn.objects.create(
                statement=third_statement,
                parent=sarflandi,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=f"1.1.5.1.{i}"
            )
            for j, (child_uz, child_ru) in enumerate(zip(children_uz, children_ru), start=1):
                StatementColumn.objects.create(
                    statement=third_statement,
                    parent=parent,
                    title_uz=child_uz,
                    title_ru=child_ru,
                    ordering=f"1.1.5.1.{i}.{j}"
                )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=third_ilova_title,
            title_uz="Hisobot oxiriga qolgan qoldiq (kg)",
            title_ru="Остаток на конец отчетного периода (кг)",
            ordering="1.1.6",
            is_user_input=False
        )

        # ============================ YAKUNIY ============================
        self.stdout.write(
            self.style.SUCCESS("✅ 'Yopiq ildiz yirik hajmli' Statement va Columns muvaffaqiyatli yaratildi."))
        self.stdout.write(
            self.style.SUCCESS("✅ 'O'rmon barpo qilish bo'limi' Statement va Columns muvaffaqiyatli yaratildi."))
        self.stdout.write(self.style.SUCCESS("✅ 'Urug' harakati' Statement va Columns muvaffaqiyatli yaratildi."))

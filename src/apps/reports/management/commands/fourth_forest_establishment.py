from django.utils import timezone
from django.core.management import BaseCommand

from apps.utils.services import PeriodChoices
from apps.reports.models import Statement, StatementColumn


class Command(BaseCommand):
    def handle(self, *args, **options):
        current_year = timezone.now().strftime("%Y")

        parent_statement = Statement.objects.get(
            name_uz="O'rmon barpo qilish",
            name_ru="Создание леса",
        )

        statement = Statement.objects.create(
            parent=parent_statement,
            name_uz="Ko'chatxona va Niholxona Jami",
            name_ru="Детский сад и ясли, всего",
            period=PeriodChoices.OYLIK
        )

        second_statement = Statement.objects.create(
            parent=parent_statement,
            name_uz="Tut Ko'chat va Tut Nihol",
            name_ru="Саженец и саженец тутового дерева",
            period=PeriodChoices.OYLIK
        )

        brusanetta_statement = Statement.objects.create(
            parent=parent_statement,
            name_uz="Bryusanetta",
            name_ru="Брюсетта",
            period=PeriodChoices.OYLIK
        )

        high_region_statement = Statement.objects.create(
            parent=parent_statement,
            name_uz="Og'ir mahalla",
            name_ru="трудный район",
            period=PeriodChoices.OYLIK
        )

        healthy_statement = Statement.objects.create(
            parent=parent_statement,
            name_uz="Sog'liqni saqlash",
            name_ru="Здравоохранение",
            period=PeriodChoices.OYLIK
        )

        education_statement = Statement.objects.create(
            parent=parent_statement,
            name_uz="Talim muassasalariga yetkazib berilgan ko'chatlar",
            name_ru="Рассада доставлена ​​в учебные заведения",
            period=PeriodChoices.OYLIK
        )

        green_place_statement = Statement.objects.create(
            parent=parent_statement,
            name_uz="Yashil makonga Ko'chat yetkazib berish",
            name_ru="Доставка саженцев на зеленую зону",
            period=PeriodChoices.OYLIK
        )

# ========================== Ko'chatxona va Niholxona Jami ===============================

        app_column = StatementColumn.objects.create(
            statement=statement,
            title_uz="1-ilova",
            title_ru="Приложение 1",
            ordering="1"
        )

        title_column_1 = StatementColumn.objects.create(
            statement=statement,
            parent=app_column,
            title_uz=f"{current_year}-yilda  o‘rmon xo‘jaliklari tomonidan niholxona va ko‘chatxonalar tashkil etish, shuningdek yillik nihol va ko‘chat yetishtirish tezkor ma’lumoti",
            title_ru=f"Оперативная информация о создании лесными хозяйствами питомников и питомников, а также выращивании годовых саженцев и рассады в {current_year} году",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=statement,
            parent=title_column_1,
            title_uz="Tashkilot nomi",
            title_ru="Названия регионов",
            ordering="1.1.1",
            is_organization=True
        )

        jami = StatementColumn.objects.create(
            statement=statement,
            parent=title_column_1,
            title_uz="Jami niholxona va ko‘chatxonalar tashkil etish (ga)",
            title_ru="Всего создание питомников и теплиц (га)",
            ordering="1.1.2"
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=jami,
            title_uz="Reja",
            title_ru="План",
            ordering="1.1.2.1",
            status_plan=StatementColumn.PlanStatus.YILLIK,
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=jami,
            title_uz="Amalda",
            title_ru="Факт",
            ordering="1.1.2.2",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=jami,
            title_uz="Foiz",
            title_ru="Процент",
            ordering="1.1.2.3",
            is_user_input=False
        )

        subgroup = StatementColumn.objects.create(
            statement=statement,
            parent=jami,
            title_uz="shundan",
            title_ru="в том числе",
            ordering="1.1.3"
        )

        niholxona = StatementColumn.objects.create(
            statement=statement,
            parent=subgroup,
            title_uz="Niholxona",
            title_ru="Питомник",
            ordering="1.1.3.1"
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=niholxona,
            title_uz="Reja",
            title_ru="План",
            ordering="1.1.3.1.1",
            status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL,
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=niholxona,
            title_uz="Amalda",
            title_ru="Факт",
            ordering="1.1.3.1.2",
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=niholxona,
            title_uz="Foiz",
            title_ru="Процент",
            ordering="1.1.3.1.3",
        )

        kochatxona_2 = StatementColumn.objects.create(
            statement=statement,
            parent=subgroup,
            title_uz="Ko'chatxona",
            title_ru="Питомница",
            ordering="1.1.3.2"
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=kochatxona_2,
            title_uz="Reja",
            title_ru="План",
            ordering="1.1.3.2.1",
            status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL,
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=kochatxona_2,
            title_uz="Amalda",
            title_ru="Факт",
            ordering="1.1.3.2.2",
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=kochatxona_2,
            title_uz="Foiz",
            title_ru="Процент",
            ordering="1.1.3.2.3",
        )



# ===================================== Tut Ko`chat va Tut Nihol ===========================================

        new_app_column = StatementColumn.objects.create(
            statement=second_statement,
            title_uz="1-ilova",
            title_ru="Приложение 1",
            ordering="1"
        )

        title_column_2 = StatementColumn.objects.create(
            statement=second_statement,
            parent=new_app_column,
            title_uz="Tut yetishtirish",
            title_ru="Выращивание тутовника",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=second_statement,
            parent=title_column_2,
            title_uz="Tashkilot nomi",
            title_ru="Названия регионов",
            ordering="1.1.1",
            is_organization=True
        )

        jami_column = StatementColumn.objects.create(
            statement=second_statement,
            parent=title_column_2,
            title_uz="Jami niholxona va ko'chatxonalar tashkil etish (1020 dona)",
            title_ru="Всего создание питомников и саженцев (1020 шт.)",
            ordering="1.1.2"
        )
        StatementColumn.objects.create(
            statement=second_statement,
            parent=jami_column,
            title_uz="Reja",
            title_ru="План",
            ordering="1.1.2.1",
            status_plan=StatementColumn.PlanStatus.YILLIK,
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=second_statement,
            parent=jami_column,
            title_uz="Amalda",
            title_ru="Факт",
            ordering="1.1.2.2",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=second_statement,
            parent=jami_column,
            title_uz="Foiz",
            title_ru="Процент",
            ordering="1.1.2.3",
            is_user_input=False
        )

        shundan = StatementColumn.objects.create(
            statement=second_statement,
            parent=jami_column,
            title_uz="shundan",
            title_ru="в том числе",
            ordering="1.1.2.4"
        )
        StatementColumn.objects.create(
            statement=second_statement,
            parent=shundan,
            title_uz="Tut Nihol",
            title_ru="Шелковица Саженец",
            ordering="1.1.2.4.1"
        )
        StatementColumn.objects.create(
            statement=second_statement,
            parent=shundan,
            title_uz="Tut Ko'chat",
            title_ru="Саженец шелковицы",
            ordering="1.1.2.4.2"
        )

# ===========================  Bryusanetta ==============================

        new_app_column_2 = StatementColumn.objects.create(
            statement=brusanetta_statement,
            title_uz="1-ilova",
            title_ru="Приложение 1",
            ordering="1"
        )

        title_column_3 = StatementColumn.objects.create(
            statement=brusanetta_statement,
            parent=new_app_column_2,
            title_uz="Bryusanetta daraxtini plantatsiyalarini barpo etish bo'yicha tezkor ma`lumot",
            title_ru="Краткое руководство по созданию плантаций брюссельской капусты",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=brusanetta_statement,
            parent=title_column_3,
            title_uz="Tashkilot nomi",
            title_ru="Названия регионов",
            ordering="1.1.1",
            is_organization=True
        )

        StatementColumn.objects.create(
            statement=brusanetta_statement,
            parent=title_column_3,
            title_uz="Ekilgan xudud (Tuman, shahar, MFY) nomi",
            title_ru="Наименование территории насаждения (район, город, МО)",
            ordering="1.1.2"
        )

        plan_column = StatementColumn.objects.create(
            statement=brusanetta_statement,
            parent=title_column_3,
            title_uz="Reja",
            title_ru="План",
            ordering="1.1.3",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=brusanetta_statement,
            parent=plan_column,
            title_uz="Maydoni (gektar)",
            title_ru="Площадь (га)",
            ordering="1.1.3.1",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=brusanetta_statement,
            parent=plan_column,
            title_uz="Ekiladigan ko'chatlar soni (maydon)",
            title_ru="Количество высаживаемых саженцев (площадь)",
            ordering="1.1.3.2",
            is_user_input=False
        )

        practise_column = StatementColumn.objects.create(
            statement=brusanetta_statement,
            parent=title_column_3,
            title_uz="Amalda",
            title_ru="Факт",
            ordering="1.1.4"
        )
        StatementColumn.objects.create(
            statement=brusanetta_statement,
            parent=practise_column,
            title_uz="Maydoni (gektar)",
            title_ru="Площадь (га)",
            ordering="1.1.4.1",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=brusanetta_statement,
            parent=practise_column,
            title_uz="Ekiladigan ko'chatlar soni (maydon)",
            title_ru="Количество высаживаемых саженцев (площадь)",
            ordering="1.1.4.2",
            is_user_input=False
        )

# ====================================== Og'ir Mahalla ===============================

        new_app_column_3 = StatementColumn.objects.create(
            statement=high_region_statement,
            title_uz="1-ilova",
            title_ru="Приложение 1",
            ordering="1"
        )

        title_column_4 = StatementColumn.objects.create(
            statement=high_region_statement,
            parent=new_app_column_3,
            title_uz=f"O‘zbekiston Respublikasi Prezidentining {current_year}-yil 17-yanvardagi PQ-12 sonli qarorining 2025-yilda aholi bandligini ta’minlash va kambag‘alchilikni qisqartirish chora tadbirlari to‘g‘risida”gi qarorida berilgan topshiriqlari ijrosi bajarilishi to‘g‘risida ma’lumot",
            title_ru=f"Об исполнении поручений, данных в постановлении Президента Республики Узбекистан от 17 января {current_year} года No ПП-12 О мерах по обеспечению занятости населения и сокращению бедности в {current_year} году информация",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=high_region_statement,
            parent=title_column_4,
            title_uz="Tashkilot nomi",
            title_ru="Названия регионов",
            ordering="1.1.1",
            is_organization=True
        )
        StatementColumn.objects.create(
            statement=high_region_statement,
            parent=title_column_4,
            title_uz="Tuman shahar nomi",
            title_ru="Название города района",
            ordering="1.1.2"
        )
        StatementColumn.objects.create(
            statement=high_region_statement,
            parent=title_column_4,
            title_uz="Og'ir mahalla soni",
            title_ru="Тяжелый подсчет соседей",
            ordering="1.1.3"
        )
        StatementColumn.objects.create(
            statement=high_region_statement,
            parent=title_column_4,
            title_uz="Og'ir toifadagi mahallalar soni",
            title_ru="Количество районов с интенсивной застройкой",
            ordering="1.1.4"
        )
        StatementColumn.objects.create(
            statement=high_region_statement,
            parent=title_column_4,
            title_uz="O'rmon xo'jaliklari nomi",
            title_ru="Название лесничества",
            ordering="1.1.5"
        )
        StatementColumn.objects.create(
            statement=high_region_statement,
            parent=title_column_4,
            title_uz="Yetkazib beriladigan ko'chatlar soni (dona)",
            title_ru="Количество поставляемых саженцев (шт.)",
            ordering="1.1.6"
        )
        StatementColumn.objects.create(
            statement=high_region_statement,
            parent=title_column_4,
            title_uz="Amalda yetkazib berildi",
            title_ru="Практически доставлено",
            ordering="1.1.7"
        )
        StatementColumn.objects.create(
            statement=high_region_statement,
            parent=title_column_4,
            title_uz="%",
            title_ru="%",
            ordering="1.1.8",
            is_user_input=False
        )

# =============================== Sog`liqni saqlash =============================
        new_app_column_4 = StatementColumn.objects.create(
            statement=healthy_statement,
            title_uz="1-ilova",
            title_ru="Приложение 1",
            ordering="1"
        )

        title_column_5 = StatementColumn.objects.create(
            statement=healthy_statement,
            parent=new_app_column_4,
            title_uz=f"O'rmon xo'jaliklari tomonidan {current_year} yilda Sog'liqni saqlash muassasalariga ko'chatlarni yetkazib berish taqsimoti.",
            title_ru=f"Распределение поставок саженцев лесным хозяйством в учреждения здравоохранения в {current_year} году.",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=title_column_5,
            title_uz="Tashkilot nomi",
            title_ru="Названия регионов",
            ordering="1.1.1",
            is_organization=True
        )
        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=title_column_5,
            title_uz="Xududlar nomi",
            title_ru="Название территорий",
            ordering="1.1.2"
        )

        arrived_column = StatementColumn.objects.create(
            statement=healthy_statement,
            parent=title_column_5,
            title_uz="Yetkazib beriladigan daraxt ba butalar ko'chatlari miqdori, (dona)",
            title_ru="Количество поставляемых саженцев деревьев и кустарников, шт.",
            ordering="1.1.3"
        )
        plan_health_column = StatementColumn.objects.create(
            statement=healthy_statement,
            parent=arrived_column,
            title_uz="Reja",
            title_ru="План",
            ordering="1.1.3.1",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=plan_health_column,
            title_uz="Jami",
            title_ru="Общий",
            ordering="1.1.3.1.1",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=plan_health_column,
            title_uz="Manzaralilar",
            title_ru="Живописные",
            ordering="1.1.3.1.2",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=plan_health_column,
            title_uz="Mevalilar",
            title_ru="Фрукты",
            ordering="1.1.3.1.3",
            is_user_input=False
        )

        practise_health_column = StatementColumn.objects.create(
            statement=healthy_statement,
            parent=arrived_column,
            title_uz="Amalda",
            title_ru="Факт",
            ordering="1.1.3.2"
        )
        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=practise_health_column,
            title_uz="Jami",
            title_ru="Общий",
            ordering="1.1.3.2.1",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=practise_health_column,
            title_uz="Manzaralilar",
            title_ru="Живописные",
            ordering="1.1.3.2.2"
        )
        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=practise_health_column,
            title_uz="Mevalilar",
            title_ru="Фрукты",
            ordering="1.1.3.2.3"
        )

        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=arrived_column,
            title_uz="%",
            title_ru="%",
            ordering="1.1.3.3",
            is_user_input=False
        )

# ================================== Talim muassasalari ===============================

        new_app_column_5 = StatementColumn.objects.create(
            statement=education_statement,
            title_uz="1-ilova",
            title_ru="Приложение 4",
            ordering="1"
        )

        title_column_6 = StatementColumn.objects.create(
            statement=education_statement,
            parent=new_app_column_5,
            title_uz=f"O'rmon xo'jaliklari tomonidan {current_year} yilda Maktab va mkatabgacha talim muassasalariga ko'chatlarni yetkazib berish taqsimoti",
            title_ru=f"Распределение саженцев, поставленных лесхозами в школы и дошкольные образовательные учреждения в {current_year} году",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=education_statement,
            parent=title_column_6,
            title_uz="Tashkilot nomi",
            title_ru="Названия регионов",
            ordering="1.1.1",
            is_organization=True
        )

        StatementColumn.objects.create(
            statement=education_statement,
            parent=title_column_6,
            title_uz="Xududlar nomi",
            title_ru="Название территорий",
            ordering="1.1.2"
        )

        arrived_column_2 = StatementColumn.objects.create(
            statement=healthy_statement,
            parent=title_column_5,
            title_uz="Yetkazib beriladigan daraxt ba butalar ko'chatlari miqdori, dona",
            title_ru="Количество поставляемых саженцев деревьев и кустарников, шт.",
            ordering="1.1.3",
            is_user_input=False
        )
        plan_health_column_2 = StatementColumn.objects.create(
            statement=healthy_statement,
            parent=arrived_column_2,
            title_uz="Reja",
            title_ru="План",
            ordering="1.1.3.1",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=plan_health_column_2,
            title_uz="Jami",
            title_ru="Общий",
            ordering="1.1.3.1.1",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=plan_health_column_2,
            title_uz="Manzaralilar",
            title_ru="Живописные",
            ordering="1.1.3.1.2",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=plan_health_column_2,
            title_uz="Mevalilar",
            title_ru="Фрукты",
            ordering="1.1.3.1.3",
            is_user_input=False
        )

        practise_health_column_3 = StatementColumn.objects.create(
            statement=healthy_statement,
            parent=arrived_column_2,
            title_uz="Amalda",
            title_ru="Факт",
            ordering="1.1.3.2",
        )
        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=practise_health_column_3,
            title_uz="Jami",
            title_ru="Общий",
            ordering="1.1.3.2.1",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=practise_health_column_3,
            title_uz="Manzaralilar",
            title_ru="Живописные",
            ordering="1.1.3.2.2"
        )
        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=practise_health_column_3,
            title_uz="Mevalilar",
            title_ru="Фрукты",
            ordering="1.1.3.2.3"
        )

        StatementColumn.objects.create(
            statement=healthy_statement,
            parent=arrived_column_2,
            title_uz="%",
            title_ru="%",
            ordering="1.1.3.3",
            is_user_input=False
        )
# ==============================  Yashil makonga Ko`chat yetkazib berish ====================================
        new_app_column_6 = StatementColumn.objects.create(
            statement=green_place_statement,
            title_uz="1-ilova",
            title_ru="Приложение 4",
            ordering="1"
        )

        title_column_7 = StatementColumn.objects.create(
            statement=green_place_statement,
            parent=new_app_column_6,
            title_uz=f"{current_year} yil bahor va kuz mavsumida 'Yashil makon' umummilliy loyihasi doirasida xo'jaliklari tomonidan yetkazib beriladigan ko'chatlar taqsimoti",
            title_ru=f"Распределение саженцев, поставленных фермерскими хозяйствами в рамках национального проекта «Зеленое пространство» весной и осенью {current_year} года",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=green_place_statement,
            parent=title_column_7,
            title_uz="Tashkilot nomi",
            title_ru="Названия регионов",
            ordering="1.1.1",
            is_organization=True
        )

        jami_yetkazib_berish = StatementColumn.objects.create(
            statement=green_place_statement,
            parent=title_column_7,
            title_uz="Jami yetkazib berilgan ko'chatlar soni",
            title_ru="Общее количество поставленных саженцев",
            ordering="1.1.2",
            is_user_input=False
        )

        StatementColumn.objects.create(
            statement=green_place_statement,
            parent=jami_yetkazib_berish,
            title_uz="Reja",
            title_ru="План",
            ordering="1.1.2.1",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=green_place_statement,
            parent=jami_yetkazib_berish,
            title_uz="Amalda",
            title_ru="Факт",
            ordering="1.1.2.2",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=green_place_statement,
            parent=jami_yetkazib_berish,
            title_uz="%",
            title_ru="%",
            ordering="1.1.2.3",
            is_user_input=False
        )

        bahor_mavsumida = StatementColumn.objects.create(
            statement=green_place_statement,
            parent=title_column_7,
            title_uz="Bahor mavsumida yetkazilib beriladigan ko'chatlar miqdori",
            title_ru="Количество поставленной рассады весной",
            ordering="1.1.3"
        )
        StatementColumn.objects.create(
            statement=green_place_statement,
            parent=bahor_mavsumida,
            title_uz="Reja",
            title_ru="План",
            ordering="1.1.3.1",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=green_place_statement,
            parent=bahor_mavsumida,
            title_uz="Amalda",
            title_ru="Факт",
            ordering="1.1.3.2"
        )
        StatementColumn.objects.create(
            statement=green_place_statement,
            parent=bahor_mavsumida,
            title_uz="%",
            title_ru="%",
            ordering="1.1.3.3",
            is_user_input=False
        )

        kuz_mavsumida = StatementColumn.objects.create(
            statement=green_place_statement,
            parent=title_column_7,
            title_uz="Kuz mavsumida yetkazilib beriladigan ko'chatlar miqdori",
            title_ru="Количество поставленной рассады весной",
            ordering="1.1.4"
        )
        StatementColumn.objects.create(
            statement=green_place_statement,
            parent=kuz_mavsumida,
            title_uz="Reja",
            title_ru="План",
            ordering="1.1.4.1",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=green_place_statement,
            parent=kuz_mavsumida,
            title_uz="Amalda",
            title_ru="Факт",
            ordering="1.1.4.2"
        )
        StatementColumn.objects.create(
            statement=green_place_statement,
            parent=kuz_mavsumida,
            title_uz="%",
            title_ru="%",
            ordering="1.1.4.3",
            is_user_input=False
        )

        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'Детский сад и ясли' statement."))
        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'TUT' statement."))
        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'Brusanetta' statement."))
        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'Og'ir mahalla' statement."))
        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'Talim muassasalari' statement."))
        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'Yetkazib berish' statement."))
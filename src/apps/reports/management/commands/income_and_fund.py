import re
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.reports.models import Statement, StatementColumn
from apps.reports.models.statement_column import StatementColumn as SC
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    help = 'Create Jamg‘arma va Daromad statementlari bilan to‘liq column tuzilmasi'

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            moliya_statement = Statement.objects.create(
                name="Moliya-iqtisod va buxgalteriya",
                name_uz="Moliya-iqtisod va buxgalteriya",
                name_ru="Финансово-экономический и бухгалтерский отдел"
            )

            # --- JAMG'ARMA STATEMENT ---
            jamg_statement = Statement.objects.create(
                name="Jamg'arma",
                name_uz="Jamg'arma",
                name_ru="Фонд",
                parent=moliya_statement,
                period=PeriodChoices.HAFTALIK
            )

            parent_info = StatementColumn.objects.create(
                statement=jamg_statement,
                title="Jamg'arma",
                title_uz="Jamg'arma",
                title_ru="Фонд",
                ordering="1"
            )

            info_child = StatementColumn.objects.create(
                statement=jamg_statement,
                parent=parent_info,
                title="O‘rmonlarni rivojlantirish jamg‘armasiga o‘tkazgan tushumi to‘g‘risida HISOBOT",
                title_uz="O‘rmonlarni rivojlantirish jamg‘armasiga o‘tkazgan tushumi to‘g‘risida HISOBOT",
                title_ru="ОТЧЁТ о средствах, перечисленных в фонд развития лесов",
                ordering="1.1"
            )

            StatementColumn.objects.create(
                statement=jamg_statement,
                parent=info_child,
                title="Tashkilot nomi",
                title_uz="Tashkilot nomi",
                title_ru="Название организации",
                ordering="1.1.1",
                is_organization=True
            )

            StatementColumn.objects.create(
                statement=jamg_statement,
                parent=info_child,
                title="Hisob raqamda yil boshiga qoldiq",
                title_uz="Hisob raqamda yil boshiga qoldiq",
                title_ru="Остаток на счете на начало года",
                ordering="1.1.2"
            )

            income_types = [
                (
                    "Ruxsatnoma olish uchun arizalarni ko‘rib chiqqanlik va ruxsatnomalar berganlik uchun tushgan mablag‘ (100%)",
                    "Рассмотрение заявок и выдача разрешений (100%)",
                    "1.1.3"
                ),
                (
                    "Hayvonot va o‘simlik dunyosiga yetkazilgan zararni qoplash bo‘yicha undirilgan mablag‘ (100%)",
                    "Возмещение ущерба животному и растительному миру (100%)",
                    "1.1.4"
                ),
                (
                    "Ruxsat etilgan hududlarda chorva boqish, pichan o‘rish, asalarilar uyasi va qutilarini joylashtirish, daraxt kesmagan holda o‘tin yig‘ish va boshqa maqsadlardan tushgan mablag‘ (50%)",
                    "Доходы от пастбищ, сена, ульев, дров и др. (50%)",
                    "1.1.5"
                ),
                (
                    "O‘rmon fondi yerlaridagi bog‘lar va madaniy o‘rmonzorlani fuqarolarga ijaraga berishdan tushgan mablag‘ (100%)",
                    "Аренда садов и лесонасаждений (100%)",
                    "1.1.6"
                ),
                (
                    "O‘rmon xo‘jaligida yog‘och kesishdan tushgan mablag‘ (50%)",
                    "Вырубка древесины в лесном хозяйстве (50%)",
                    "1.1.7"
                ),
                (
                    "Boshqa daromadlar (10%)",
                    "Прочие доходы (10%)",
                    "1.1.8"
                ),
            ]

            for income_title_uz, income_title_ru, income_order in income_types:
                match = re.search(r'\((\d+%)\)', income_title_uz)
                percent = match.group(1) if match else "0%"

                income_node = StatementColumn.objects.create(
                    statement=jamg_statement,
                    parent=info_child,
                    title=income_title_uz,
                    title_uz=income_title_uz,
                    title_ru=income_title_ru,
                    ordering=income_order
                )

                StatementColumn.objects.create(
                    statement=jamg_statement,
                    parent=income_node,
                    title="Jami tushum",
                    title_uz="Jami tushum",
                    title_ru="Общий доход",
                    ordering=f"{income_order}.1",
                    is_user_input=False
                )

                jamg_node = StatementColumn.objects.create(
                    statement=jamg_statement,
                    parent=income_node,
                    title="shundan jamg’armaga",
                    title_uz="shundan jamg’armaga",
                    title_ru="в том числе в фонд",
                    ordering=f"{income_order}.2"
                )

                for j_idx, (title_uz, title_ru) in enumerate([
                    (f"To‘lanishi kerak ({percent})", f"Подлежит оплате ({percent})"),
                    ("To‘landi", "Оплачено"),
                    ("Qoldiq", "Остаток")
                ], start=1):
                    extra_kwargs = {}
                    if title_uz == "Qoldiq":
                        extra_kwargs["is_user_input"] = False

                    StatementColumn.objects.create(
                        statement=jamg_statement,
                        parent=jamg_node,
                        title=title_uz,
                        title_uz=title_uz,
                        title_ru=title_ru,
                        ordering=f"{income_order}.2.{j_idx}",
                        **extra_kwargs
                    )

            jami_tushum = StatementColumn.objects.create(
                statement=jamg_statement,
                parent=info_child,
                title="Jami tushum",
                title_uz="Jami tushum",
                title_ru="Общий доход",
                ordering="1.1.9"

            )

            StatementColumn.objects.create(
                statement=jamg_statement,
                parent=jami_tushum,
                title="Jamg’arma ga jami tushum",
                title_uz="Jamg’arma ga jami tushum",
                title_ru="Общий доход в фонд",
                ordering="1.1.9.1",
                is_user_input=False
            )

            jamg_shundan = StatementColumn.objects.create(
                statement=jamg_statement,
                parent=jami_tushum,
                title="shundan jamg’armaga",
                title_uz="shundan jamg’armaga",
                title_ru="в том числе в фонд",
                ordering="1.1.9.2"
            )

            for j_idx, (title_uz, title_ru) in enumerate([
                ("Jamg’arma ga tushishi kerak bo‘lgan tushum", "Доход, подлежащий зачислению в фонд"),
                ("To‘landi", "Оплачено"),
                ("Qoldiq", "Остаток")
            ], start=1):
                StatementColumn.objects.create(
                    statement=jamg_statement,
                    parent=jamg_shundan,
                    title=title_uz,
                    title_uz=title_uz,
                    title_ru=title_ru,
                    ordering=f"1.1.9.2.{j_idx}",
                    is_user_input = False
                )

            self.stdout.write(self.style.SUCCESS("Jamg‘arma statement yaratildi."))

            daromad_statement = Statement.objects.create(
                name="Daromad",
                name_uz="Daromad",
                name_ru="Доход",
                parent=moliya_statement,
                period=PeriodChoices.OYLIK,
            )

            # Daromad turlari
            daromad_turlari = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=None,
                title="Daromad turlari bo‘yicha",
                title_uz="Daromad turlari bo‘yicha",
                title_ru="По видам доходов",
                ordering="1"
            )

            info = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=daromad_turlari,
                title="2025 yil davomida topilgan daromadlar haqida MA'LUMOT",
                title_uz="2025 yil davomida topilgan daromadlar haqida MA'LUMOT",
                title_ru="ИНФОРМАЦИЯ о доходах, полученных в 2025 году",
                ordering="1.1"
            )

            titles = [
                ("Tashkilot nomi", "Название организации"),
                ("Ko‘chat va nihol sotish", "Продажа саженцев и рассады"),
                ("Yog‘och o‘tin sotish", "Продажа дров"),
                ("Sanoat, xalq iste’mol mollari", "Промышленные и потребительские товары"),
                ("Aholiga pullik xizmat", "Платные услуги населению"),
                ("Yaylov tushumi", "Доход от пастбищ"),
                ("Qishloq xo‘jaligi mahsulotlari", "Сельскохозяйственная продукция"),
                ("Chorvachilik", "Животноводство"),
                ("Parrandachilik", "Птицеводство"),
                ("Quyonchilik", "Кролиководство"),
                ("Baliqchilik", "Рыбоводство"),
                ("Asalarichilik", "Пчеловодство"),
                ("Dorivor o‘simliklar", "Лекарственные растения"),
                ("Ko‘kalamzorlashtirish", "Озеленение"),
                ("Boshqa tushumlar", "Прочие доходы"),
                ("Ixota", "Охота"),
                ("Urug‘ sotishdan", "Продажа семян"),
                ("Ijara to‘lovlari", "Арендные платежи"),
                ("Jami", "Итого")
            ]

            for idx, (title_uz, title_ru) in enumerate(titles, start=1):
                StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=info,
                    title=title_uz,
                    title_uz=title_uz,
                    title_ru=title_ru,
                    ordering=f"1.1.{idx}",
                    is_organization=(idx == 1),
                    is_user_input=(idx != len(titles))
                )

            # Tushumlar bo‘yicha
            tushumlar = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=None,
                title="Tushumlar bo‘yicha",
                title_uz="Tushumlar bo‘yicha",
                title_ru="По поступлениям",
                ordering="2"
            )


            tushum_info = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushumlar,
                title="2025 yil holatiga daromad tushumi to‘g‘risida ma’lumot",
                title_uz="2025 yil holatiga daromad tushumi to‘g‘risida ma’lumot",
                title_ru="ИНФОРМАЦИЯ о доходах по состоянию на 2025 год",
                ordering="2.1"
            )

            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushum_info,
                title='Tashkilot nomi',
                title_uz='Tashkilot nomi',
                title_ru='Название организации',
                ordering="2.1.1",
                is_organization=True
            )

            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushum_info,
                title='Yillik reja',
                title_uz='Yillik reja',
                title_ru='Годовой план',
                ordering="2.1.2",
                status_plan=SC.PlanStatus.YILLIK
            )

            chorak_nomi_uz = {
                SC.PlanStatus.CHORAK_1: "1-chorak",
                SC.PlanStatus.CHORAK_2: "2-chorak",
                SC.PlanStatus.CHORAK_3: "3-chorak",
                SC.PlanStatus.CHORAK_4: "4-chorak",
            }

            chorak_nomi_ru = {
                SC.PlanStatus.CHORAK_1: "1-й квартал",
                SC.PlanStatus.CHORAK_2: "2-й квартал",
                SC.PlanStatus.CHORAK_3: "3-й квартал",
                SC.PlanStatus.CHORAK_4: "4-й квартал",
            }

            oy_nomi_uz = {
                SC.PlanStatus.YANVAR: "Yanvar",
                SC.PlanStatus.FEVRAL: "Fevral",
                SC.PlanStatus.MART: "Mart",
                SC.PlanStatus.APREL: "Aprel",
                SC.PlanStatus.MAY: "May",
                SC.PlanStatus.IYUN: "Iyun",
                SC.PlanStatus.IYUL: "Iyul",
                SC.PlanStatus.AVGUST: "Avgust",
                SC.PlanStatus.SENTABR: "Sentabr",
                SC.PlanStatus.OKTABR: "Oktabr",
                SC.PlanStatus.NOYABR: "Noyabr",
                SC.PlanStatus.DEKABR: "Dekabr",
            }

            oy_nomi_ru = {
                SC.PlanStatus.YANVAR: "Январь",
                SC.PlanStatus.FEVRAL: "Февраль",
                SC.PlanStatus.MART: "Март",
                SC.PlanStatus.APREL: "Апрель",
                SC.PlanStatus.MAY: "Май",
                SC.PlanStatus.IYUN: "Июнь",
                SC.PlanStatus.IYUL: "Июль",
                SC.PlanStatus.AVGUST: "Август",
                SC.PlanStatus.SENTABR: "Сентябрь",
                SC.PlanStatus.OKTABR: "Октябрь",
                SC.PlanStatus.NOYABR: "Ноябрь",
                SC.PlanStatus.DEKABR: "Декабрь",
            }

            choraklar = {
                SC.PlanStatus.CHORAK_1: [SC.PlanStatus.YANVAR, SC.PlanStatus.FEVRAL, SC.PlanStatus.MART],
                SC.PlanStatus.CHORAK_2: [SC.PlanStatus.APREL, SC.PlanStatus.MAY, SC.PlanStatus.IYUN],
                SC.PlanStatus.CHORAK_3: [SC.PlanStatus.IYUL, SC.PlanStatus.AVGUST, SC.PlanStatus.SENTABR],
                SC.PlanStatus.CHORAK_4: [SC.PlanStatus.OKTABR, SC.PlanStatus.NOYABR, SC.PlanStatus.DEKABR],
            }

            for c_idx, (chorak_status, oylar) in enumerate(choraklar.items(), start=1):
                chorak_order = f"2.1.{2 + c_idx * 2 - 1}"

                # Chorak reja
                chorak_reja = StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=tushum_info,
                    title=f"{chorak_nomi_uz[chorak_status]} reja",
                    title_uz=f"{chorak_nomi_uz[chorak_status]} reja",
                    title_ru=f"{chorak_nomi_ru[chorak_status]} план",
                    ordering=chorak_order
                )

                StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=chorak_reja,
                    title="Reja",
                    title_uz="Reja",
                    title_ru="План",
                    ordering=f"{chorak_order}.1",
                    status_plan=chorak_status
                )

                StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=chorak_reja,
                    title="Amalda",
                    title_uz="Amalda",
                    title_ru="Факт",
                    ordering=f"{chorak_order}.2",
                    is_user_input=False
                )

                # Chorak oylar bo'limi
                chorak_oy_node = StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=tushum_info,
                    title=chorak_nomi_uz[chorak_status],
                    title_uz=chorak_nomi_uz[chorak_status],
                    title_ru=chorak_nomi_ru[chorak_status],
                    ordering=f"2.1.{2 + c_idx * 2}"
                )

                for o_idx, oy_status in enumerate(oylar, start=1):
                    oy_order = f"2.1.{2 + c_idx * 2}.{o_idx}"

                    oy_node = StatementColumn.objects.create(
                        statement=daromad_statement,
                        parent=chorak_oy_node,
                        title=oy_nomi_uz[oy_status],
                        title_uz=oy_nomi_uz[oy_status],
                        title_ru=oy_nomi_ru[oy_status],
                        ordering=oy_order
                    )

                    for p_idx, (title_uz, title_ru) in enumerate([
                        ("Reja", "План"),
                        ("Amalda", "Факт"),
                        ("Foiz", "%")
                    ], start=1):
                        StatementColumn.objects.create(
                            statement=daromad_statement,
                            parent=oy_node,
                            title=title_uz,
                            title_uz=title_uz,
                            title_ru=title_ru,
                            ordering=f"{oy_order}.{p_idx}",
                            status_plan=(oy_status if title_uz == "Reja" else None),
                            is_user_input=(title_uz == "Reja")
                        )

                    tushum_node = StatementColumn.objects.create(
                        statement=daromad_statement,
                        parent=oy_node,
                        title="tushum",
                        title_uz="tushum",
                        title_ru="поступление",
                        ordering=f"{oy_order}.4"
                    )

                    for t_idx, (title_uz, title_ru) in enumerate([
                        ("kunlik", "ежедневно"),
                        ("Oy boshidan", "с начала месяца")
                    ], start=1):
                        StatementColumn.objects.create(
                            statement=daromad_statement,
                            parent=tushum_node,
                            title=title_uz,
                            title_uz=title_uz,
                            title_ru=title_ru,
                            ordering=f"{oy_order}.4.{t_idx}"
                        )

            year_begin = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushum_info,
                title='Yil boshidan',
                title_uz='Yil boshidan',
                title_ru='С начала года',
                ordering="2.1.11",
            )

            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=year_begin,
                title='Tushum',
                title_uz='Tushum',
                title_ru='Поступление',
                ordering="2.1.11.1",
                is_user_input=False
            )

            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=year_begin,
                title='Yillik rejaga nisbatan %',
                title_uz='Yillik rejaga nisbatan %',
                title_ru='% к годовому плану',
                ordering="2.1.11.2",
                is_user_input=False
            )

            # Svod bo‘limi
            svod = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=None,
                title="Svod",
                title_uz="Svod",
                title_ru="Свод",
                ordering="3"
            )

            svod_title = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=svod,
                title="2025 yil davomida topilgan daromadlar haqida MA'LUMOT",
                title_uz="2025 yil davomida topilgan daromadlar haqida MA'LUMOT",
                title_ru="ИНФОРМАЦИЯ О ДОХОДАХ, ПОЛУЧЕННЫХ В ТЕЧЕНИЕ 2025 ГОДА",
                ordering="3.1"
            )

            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=svod_title,
                title="Tashkilot nomi",
                title_uz="Tashkilot nomi",
                title_ru="Наименование организации",
                ordering="3.1.1",
                is_organization=True
            )

            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=svod_title,
                title="Yillik reja (ming sum)",
                title_uz="Yillik reja (ming so'm)",
                title_ru="Годовой план (в тыс. сумов)",
                ordering="3.1.2",
                status_plan=SC.PlanStatus.YILLIK
            )

            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=svod_title,
                title="Amalda (ming sum)",
                title_uz="Amalda (ming so'm)",
                title_ru="Фактически (в тыс. сумов)",
                ordering="3.1.3",
                is_user_input=False
            )

            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=svod_title,
                title="Rejaga nisbatan %",
                title_uz="Rejaga nisbatan %",
                title_ru="В % к плану",
                ordering="3.1.4",
                is_user_input=False
            )

            self.stdout.write(self.style.SUCCESS("Daromad statement to‘liq yaratildi."))

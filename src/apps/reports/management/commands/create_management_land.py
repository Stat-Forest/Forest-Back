from django.core.management.base import BaseCommand
from django.db import transaction
from apps.reports.models import Statement, StatementColumn as SC
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    help = "Creates default Statement and StatementColumn data (UZ-RU)"

    def create_column(self, **kwargs):
        return SC.objects.create(**kwargs)

    def create_columns_from_titles(self, titles, base_ordering, parent, statement, is_user_input=True):
        for idx, (uz_title, ru_title) in enumerate(titles, 1):
            self.create_column(
                statement=statement,
                parent=parent,
                title=uz_title,
                title_ru=ru_title,
                ordering=f"{base_ordering}.{idx}",
                is_user_input=is_user_input
            )

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            urmon = Statement.objects.create(name="O‘rmon kadastri, ijara", name_ru="Лесной кадастр, аренда")
            land_1 = Statement.objects.create(name="Yer o‘zlashtirish", name_ru="Освоение земель", parent=urmon, period=PeriodChoices.OYLIK)
            land_2 = Statement.objects.create(name="Ijaraga berilgan yerlar hisobi", name_ru="Учет арендованных земель", parent=urmon, period=PeriodChoices.OYLIK)
            land_3 = Statement.objects.create(name="O‘rmon bilan qoplangan yerlar", name_ru="Покрытые лесом земли", parent=urmon, period=PeriodChoices.YILLIK)

            col_14 = self.create_column(statement=land_3, title="2-ilova", title_ru="Приложение-2", ordering="4")
            col_13 = self.create_column(statement=land_3, title="1-ilova", title_ru="Приложение-1", ordering="3")
            col_12 = self.create_column(statement=land_2, title="1-ilova", title_ru="Приложение-1", ordering="2")
            col_11 = self.create_column(statement=land_1, title="1-ilova", title_ru="Приложение-1", ordering="1")

            info_14 = self.create_column(statement=land_3, parent=col_14, title="Urmon bilan qoplangan yerlar tematik qatlam atributiv ma'lumotlari", title_ru="Атрибутивные данные тематического слоя покрытых лесом земель", ordering="4.1")
            info_13 = self.create_column(statement=land_3, parent=col_13, title="O‘rmon bo‘limlari tematik qatlamining atributiv ma’lumotlari", title_ru="Атрибутивные данные тематического слоя лесных участков", ordering="3.1")
            from django.utils import timezone

            current_year = timezone.now().strftime("%Y")

            info_12 = self.create_column(
                statement=land_2,
                parent=col_12,
                title=f"{current_year} yilda xar bir ijarachi bo‘yicha ma’lumot",
                title_ru=f"Информация по каждому арендатору за {current_year} год",
                ordering="2.1"
            )

            info_11 = self.create_column(
                statement=land_1,
                parent=col_11,
                title=f"{current_year} yilda foydalanishga kiritiladigan o‘rmon fondi yerlari maydoni to‘g‘risida ma’lumot",
                title_ru=f"Информация о площади земель лесного фонда, вводимых в эксплуатацию в {current_year} году",
                ordering="1.1"
            )
            # Tashkilot nomi
            for info, ord, stmt in [
                (info_11, "1.1.1", land_1),
                (info_12, "2.1.1", land_2),
                (info_13, "3.1.1", land_3),
                (info_14, "4.1.1", land_3)
            ]:
                self.create_column(statement=stmt, parent=info, title="Tashkilot nomi", title_ru="Наименование организации", ordering=ord, is_organization=True)

            # Reja va boshqa ustunlar
            self.create_column(statement=land_1, parent=info_11, title="Reja", title_ru="План", ordering="1.1.2", status_plan=SC.PlanStatus.YILLIK)
            self.create_column(statement=land_1, parent=info_11, title="Amalda", title_ru="Фактически", ordering="1.1.3",is_user_input=False)
            shundan = self.create_column(statement=land_1, parent=info_11, title="Shundan", title_ru="Из них", ordering="1.1.4")
            for i, (uz, ru) in enumerate([
                ("1-chorak", "1-й квартал"),
                ("2-chorak", "2-й квартал"),
                ("3-chorak", "3-й квартал"),
                ("4-chorak", "4-й квартал")
            ], 1):
                self.create_column(statement=land_1, parent=shundan, title=uz, title_ru=ru, ordering=f"1.1.4.{i}")
            self.create_column(statement=land_1, parent=info_11, title="Foiz", title_ru="Процент", ordering="1.1.5",is_user_input=False)

            # Shartnoma
            contract = self.create_column(statement=land_2, parent=info_12, title="Shartnoma", title_ru="Договор", ordering="2.1.2")
            self.create_column(statement=land_2, parent=contract, title="Sana", title_ru="Дата", ordering="2.1.2.1")

            # Ijarachi ma’lumotlari
            rent_titles = [
                ("JSHSHIR (Yuridik shaxs INN)", "ИНН (юридического лица)"),
                ("To‘liq F.I.SH. (Yuridik shaxs nomi)", "Ф.И.О. полностью (наименование юридического лица)"),
                ("Yashash manzili (Yuridik manzil)", "Адрес проживания (юридический адрес)"),
                ("Pasport seriyasi va raqami (rahbar)", "Серия и номер паспорта (руководитель)"),
                ("Telefon raqami / Telegram", "Номер телефона / Телеграм")
            ]

            info_rent = self.create_column(
                statement=land_2,
                parent=info_12,
                title="Ijarachi ma’lumotlari",
                title_ru="Информация об арендаторе",
                ordering="2.1.3"
            )
            self.create_columns_from_titles(rent_titles, "2.1.3", info_rent, land_2)

            # Ижара ер майдони жойлашган ўрмон бўлими номи (Farzandi yo‘q)
            self.create_column(
                statement=land_2,
                parent=info_12,
                title="Ijara yer maydoni joylashgan o‘rmon bo‘limi nomi",
                title_ru="Наименование лесничества, где расположен арендованный земельный участок",
                ordering="2.1.4"
            )

            # "шундан" va uning farzandlari
            shundan = self.create_column(
                statement=land_2,
                parent=info_12,
                title="шундан",
                title_ru="из них",
                ordering="2.1.5"
            )

            shundan_titles = [
                ("Aylanma raqami", "Номер обхода"),
                ("Kvartal raqami", "Номер квартала"),
                ("Kontur raqami", "Номер контура"),
                ("Vidal raqami", "Номер отдела"),
            ]

            self.create_columns_from_titles(shundan_titles, "2.1.5", shundan, land_2)

            # 1.2.1.6 Жами ижарага олинган ер майдони (га)
            self.create_column(
                statement=land_2,
                parent=info_12,
                title="Jami ijaraga olingan yer maydoni (ga)",
                title_ru="Общая площадь арендованной земли (га)",
                ordering="2.1.6"
            )

            # Shundan faoliyat turlari bo‘yicha
            activity_titles = [
                ("O‘rmon barpo qilish", "Создание лесов"),
                ("Qishloq xo‘jaligi ekinlarini ekish", "Посев сельскохозяйственных культур"),
                ("Mevali bog‘lar barpo etish", "Создание фруктовых садов"),
                ("Yong‘oq mevali bog‘lar (pista, bodom, yong‘oq) faoliyati", "Деятельность ореховых садов (фисташки, миндаль, грецкий орех)"),
                ("Ko‘chat yetishtirish faoliyati", "Выращивание саженцев"),
                ("Limonariy va issiqxonalar tashkil etish faoliyati", "Создание лимонариев и теплиц"),
                ("Pichanzorlardan foydalanish (pichan yig‘ishtirish)", "Использование сенокосов (заготовка сена)"),
                ("Dorivor o‘simliklar yetishtirish faoliyati", "Выращивание лекарственных растений"),
                ("Ovchilik faoliyati (ovchilarni qabul qilish punkti)", "Охотничья деятельность (пункты приема охотников)"),
                ("Boshqa faoliyat turlari", "Другие виды деятельности"),
                ("Cho‘l", "Пустыня"),
                ("Tog‘", "Горы"),
                ("Vodiy", "Долина"),
                ("To‘qay", "Тугай"),
                ("O‘zlashtirilmagan boshqa yerlar", "Другие неосвоенные земли")
            ]
            types_block = self.create_column(statement=land_2, parent=info_12, title="Shundan faoliyat turlari bo‘yicha", title_ru="Из них по видам деятельности", ordering="2.1.7")
            self.create_columns_from_titles(activity_titles, "2.1.7", types_block, land_2)
            # Yer turlari bo‘yicha
            land_types_titles = [
                ("Cho‘l", "Пустыня"),
                ("Tog‘", "Горы"),
                ("Vodiy", "Долина"),
                ("To‘qay", "Тугай"),
                ("O‘zlashtirilmagan boshqa yerlar", "Другие неосвоенные земли")
            ]
            land_types_block = self.create_column(
                statement=land_2,
                parent=info_12,
                title="Shundan yer turali",
                title_ru="Из них по типам земель",
                ordering="2.1.8"
            )
            self.create_columns_from_titles(land_types_titles, "2.1.8", land_types_block, land_2)

            # Imtiyozli maydon
            # 1.2.1.9 - Shundan imtiyozli maydon (asosiy blok)
            preferred_block = self.create_column(
                statement=land_2,
                parent=info_12,
                title="Shundan imtiyozli maydon",
                title_ru="Из них льготная площадь",
                ordering="2.1.9"
            )

            # 1.2.1.9.1 - Jami (bolasisiz)
            self.create_column(
                statement=land_2,
                parent=preferred_block,
                title="Jami",
                title_ru="Итого",
                ordering="2.1.9.1"
            )

            # 1.2.1.9.2 - Shundan (va uning bolalari)
            preferred_inner = self.create_column(
                statement=land_2,
                parent=preferred_block,
                title="Shundan",
                title_ru="Из них",
                ordering="2.1.9.2"
            )

            # 1.2.1.9.2.X - Plantatsiya turlari (children)
            plantation_titles = [
                ("Cho‘l o‘simliklari (saxovul, cherkes, qandim, qoraburoq) ekish (ga) (10 yil)",
                 "Посадка пустынных растений (саксаул, черкес, кандим, карабурук) (га) (10 лет)"),
                ("Yong‘oq mevali bog‘lar ...", "Ореховые фруктовые сады ..."),
                ("Qishloq xo‘jaligi oziq-ovqat ekinlari ...", "Сельскохозяйственные продовольственные культуры ..."),
                ("Dorivor o‘simliklar plantatsiyalari ...", "Плантации лекарственных растений ...")
            ]
            self.create_columns_from_titles(plantation_titles, "2.1.9.2", preferred_inner, land_2)

            current_year = int(timezone.now().strftime("%Y"))
            next_year = current_year + 1

            period = self.create_column(
                statement=land_2,
                parent=info_12,
                title=f"{current_year}–{next_year} yillar",
                title_ru=f"{current_year}–{next_year} годы",
                ordering="2.1.10"
            )

            # 1.2.1.10.X - To‘lovlar
            self.create_column(statement=land_2, parent=period, title="Jami hisoblangan", title_ru="Всего рассчитано",
                               ordering="2.1.10.1")
            self.create_column(statement=land_2, parent=period, title="Jami to‘langan", title_ru="Всего оплачено",
                               ordering="2.1.10.2")
            self.create_column(statement=land_2, parent=period, title="Jami qarzdorlik", title_ru="Общая задолженность",
                               ordering="2.1.10.3")

            # 1.2.1.11 - Yangi ish o‘rinlari (bolasisiz)
            self.create_column(
                statement=land_2,
                parent=info_12,
                title="Yangidan yaratilgan ish o‘rinlari soni",
                title_ru="Количество вновь созданных рабочих мест",
                ordering="2.1.11"
            )

            # 1.2.1.12 - Investitsiya
            self.create_column(
                statement=land_2,
                parent=info_12,
                title="Kiritiladigan investitsiya qiymati (ming so‘m)",
                title_ru="Объем инвестиций (тыс. сум)",
                ordering="2.1.12"
            )

            # 1.2.1.12.1 - Investitsiya ichidagi: O'z hisobidan
            invest_block = self.create_column(
                statement=land_2,
                parent=info_12,
                title="Shundan",
                title_ru="Из них",
                ordering="2.1.12.1"
            )

            self.create_column(
                statement=land_2,
                parent=invest_block,
                title="O'z hisobidan",
                title_ru="За счет собственных средств",
                ordering="2.1.12.1.1"
            )

            # Eksport
            export_block = self.create_column(statement=land_2, parent=info_12, title=f"{current_year} yildagi eksport", title_ru=f"Экспорт за {current_year} год", ordering="2.1.13")
            export_titles = [
                ("Mahsulot turi", "Вид продукции"),
                ("Mahsulot miqdori", "Количество продукции"),
                ("Hajmi (ming AQSh dollari)", "Объем (тыс. долларов США)"),
                ("Sanasi", "Дата")
            ]
            self.create_columns_from_titles(export_titles, "2.1.13", export_block, land_2)

            # Bekor qilingan
            rejected_block = self.create_column(statement=land_2, parent=info_12, title="Bekor qilingan", title_ru="Отменено", ordering="2.1.14")
            self.create_columns_from_titles([
                ("Sana", "Дата"),
                ("Asos", "Основание")
            ], "2.1.14", rejected_block, land_2)

            # O‘rmon bo‘limi
            forest_titles = [
                ("O‘rmon bo‘limining nomi", "Название лесного участка"),
                ("O‘rmon bo‘limining identifikatsiya raqami", "Идентификационный номер участка"),
                ("O‘rmon bo‘limi tashkil etilgan sana", "Дата создания участка"),
                ("Idoraviy mansubligi", "Ведомственная принадлежность"),
                ("O‘rmon bo‘limining joylashgan joyi", "Местоположение участка"),
                ("O‘rmon bo‘limi ma’lumotlari hisobga olingan sana", "Дата учета данных участка")
            ]
            self.create_columns_from_titles(forest_titles, "3.1", info_13, land_3)

            # Tematik qatlam
            them_layer = self.create_column(
                statement=land_3,
                parent=info_13,
                title="Tematik qatlam atributiv ma’lumotlari",
                title_ru="Атрибутивные данные тематического слоя",
                ordering="3.1.8"
            )
            self.create_columns_from_titles([
                ("Kvartalning identifikatsiya raqami", "Идентификационный номер квартала"),
                ("Kvartal raqami", "Номер квартала"),
                ("Izoh", "Примечание")
            ], "3.1.8", them_layer, land_3)

            # Kontur
            contour_titles = [
                ("Kontur identifikatsiya raqami", "Идентификационный номер контура"),
                ("Maydoni (ga)", "Площадь (га)"),
                ("Daraxt nomi", "Наименование дерева"),
                ("O‘rmonlarni ko‘paytirish usuli", "Метод расширения лесов"),
                ("Daraxtlar yoshi bo‘yicha mansubligi", "Принадлежность по возрасту деревьев"),
                ("Daraxtlarning o‘rtacha yoshi", "Средний возраст деревьев"),
                ("O‘rmonlarni tashkil qiluvchi asosiy turlar", "Основные породы лесов"),
                ("O‘rmonlarning holati", "Состояние лесов"),
                ("Bonitet sinfi", "Класс бонитета"),
                ("Daraxtlarning zichlik darajasi", "Степень плотности деревьев"),
                ("O‘rmon turi", "Тип леса"),
                ("Daraxtlar zaxirasi (m³)", "Запас деревьев (м³)"),
                ("Qiymati (so‘m)", "Стоимость (сум)")
            ]
            self.create_columns_from_titles(contour_titles, "4.1", info_14, land_3)

            self.stdout.write(self.style.SUCCESS(f" Land management created successfully."))
from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn


class Command(BaseCommand):
    help = "Create Statement Forest Protect"

    # ===================================================  YONG`INLARNI OLDINI OLISH
    def create_column_with_children(self, statement, parent, base_ordering, title_uz, title_ru, status_plan):
        parent_column = StatementColumn.objects.create(
            statement=statement,
            parent=parent,
            title_uz=title_uz,
            title_ru=title_ru,
            ordering=base_ordering
        )

        StatementColumn.objects.create(
            statement=statement,
            parent=parent_column,
            title_uz="Reja",
            title_ru="План",
            ordering=f"{base_ordering}.1",
            status_plan=status_plan
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=parent_column,
            title_uz="Amalda",
            title_ru="Факт",
            ordering=f"{base_ordering}.2",
            status_plan=status_plan
        )

        return parent_column

    def handle(self, *args, **options):
        YILLIK = StatementColumn.PlanStatus.YILLIK

        root, _ = Statement.objects.get_or_create(name_uz="O‘rmonlarni muhofaza qilish", name_ru="Защита лесов")
        fire_prevent, _ = Statement.objects.get_or_create(
            parent=root,
            name_uz="Yong‘inlarni oldini olish",
            name_ru="Предотвращение пожаров"
        )

        appendix = StatementColumn.objects.create(
            statement=fire_prevent,
            parent=None,
            title_uz="Yong‘inlarni oldini olish-ilovasi",
            title_ru="Приложение по предотвращению пожаров",
            ordering="1"
        )

        title_column = StatementColumn.objects.create(
            statement=fire_prevent,
            parent=appendix,
            title_uz="O‘rmon xo‘jaligi agentligi tizim tashkilotlarida o‘rmon yong‘inlarini oldini olish bo‘yicha HISOBOTLAR",
            title_ru="ОТЧЕТЫ по предотвращению лесных пожаров в организациях системы Агентства лесного хозяйства",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=fire_prevent,
            parent=title_column,
            title_uz="Tashkilot nomi",
            title_ru="Название хозяйства",
            ordering="1.1.1",
            is_organization=True
        )

        new_construction = StatementColumn.objects.create(
            statement=fire_prevent,
            parent=title_column,
            title_uz="Yong‘inga qarshi yangi quriladigan obyektlar, jumladan",
            title_ru="Строящиеся объекты против пожаров, в том числе",
            ordering="1.1.2"
        )

        items_1_1_2 = [
            ("oraliq joylar (km)", "участки (км)"),
            ("yo‘llar (km)", "дороги (км)"),
            ("yong‘inga qarshi himoya chiziqlari (km)", "противопожарные линии (км)"),
            ("zovurlar (km)", "каналы (км)"),
            ("suv havzalari (m3)", "водоемы (м³)")
        ]

        for i, (title_uz, title_ru) in enumerate(items_1_1_2, start=1):
            self.create_column_with_children(
                statement=fire_prevent,
                parent=new_construction,
                base_ordering=f"1.1.2.{i}",
                title_uz=title_uz,
                title_ru=title_ru,
                status_plan=YILLIK
            )

        repairs = StatementColumn.objects.create(
            statement=fire_prevent,
            parent=title_column,
            title_uz="Yong‘inga qarshi taʼmirlanadigan obyektlar, jumladan",
            title_ru="Ремонтируемые объекты против пожаров, в том числе",
            ordering="1.1.3"
        )

        items_1_1_3 = [
            ("oraliq joylar (km)", "участки (км)"),
            ("yo‘llar (km)", "дороги (км)"),
            ("yong‘inga qarshi himoya chiziqlari (km)", "противопожарные линии (км)"),
            ("zovurlar (km)", "каналы (км)"),
            ("suv havzalari (m3)", "водоемы (м³)"),
        ]

        for i, (title_uz, title_ru) in enumerate(items_1_1_3, start=1):
            self.create_column_with_children(
                statement=fire_prevent,
                parent=repairs,
                base_ordering=f"1.1.3.{i}",
                title_uz=title_uz,
                title_ru=title_ru,
                status_plan=YILLIK
            )
        StatementColumn.objects.create(
            statement=fire_prevent,
            parent=title_column,
            title_uz="kichik hajmdagi suv zaxiralari (litrda)",
            title_ru="маленькие водные запасы (литры)",
            ordering="1.1.4"
        )

    # ===================================================  YONG`INLARNI OLDINI OLISH

        second_of_statement, _ = Statement.objects.get_or_create(
            parent=root,
            name_uz="Zararkunanda va kasalliklarga qarshi kurashish",
            name_ru="Борьба с вредителями и болезнями"
        )

        second_app_column = StatementColumn.objects.create(
            statement=second_of_statement,
            parent=None,
            title_uz="Zararkunanda va kasalliklarga qarshi kurashish-ilovasi",
            title_ru="Приложение по борьбе с вредителями и болезнями",
            ordering="1"
        )

        title_of_column = StatementColumn.objects.create(
            statement=second_of_statement,
            parent=second_app_column,
            title_uz="O‘rmon xo‘jaligi agentligi tizim tashkilotlarida o‘rmon zararkunanda va kasalliklarini aniqlash va ularga qarshi kurashish bo‘yicha HISOBOTLAR",
            title_ru="ОТЧЕТЫ по выявлению лесных вредителей и болезней и борьбе с ними в организациях системы Агентства лесного хозяйства",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=second_of_statement,
            parent=title_of_column,
            title_uz="Tashkilot nomi",
            title_ru="Название хозяйства",
            ordering="1.1.1",
            is_organization=True
        )

        items = [
            ("Zararkunanda va kasalliklarni aniqlash bo‘yicha o‘rganiladigan maydon (gektar)", "Исследуемая площадь для выявления вредителей и болезней (га)"),
            ("Aniqlangan zararkunanda va kasallikka qarshi kurashish bo‘yicha olib boriladigan tadbir (gektar)", "Мероприятия по борьбе с выявленными вредителями и болезнями (га)"),
            ("Shu jumladan zararkunandalarga qarshi o‘tkaziladigan biologik tadbir (gektar)", "В том числе биологические мероприятия против вредителей (га)"),
        ]

        for idx, (title_uz, title_ru) in enumerate(items, start=2):
            self.create_column_with_children(
                statement=second_of_statement,
                parent=title_of_column,
                base_ordering=f"1.1.{idx}",
                title_uz=title_uz,
                title_ru=title_ru,
                status_plan=YILLIK
            )
    # ===================================================  XUQUQBUZARLIK

        third_statement, _ = Statement.objects.get_or_create(
            parent=root,
            name_uz="Xuquqbuzarlik",
            name_ru="Нарушение закона"
        )

        third_app_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=None,
            title_uz="Xuquqbuzarlik-ilovasi",
            title_ru="Приложение по нарушениям",
            ordering="1"
        )

        third_title_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_app_column,
            title_uz="HISOBOTLAR",
            title_ru="ОТЧЕТЫ",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=third_title_column,
            title_uz="Tashkilot nomi",
            title_ru="Название хозяйства",
            ordering="1.1.1",
            is_organization=True
        )

        simple_items = [
            ("Aniqlangan qonunbuzarlik turi", "Тип выявленного нарушения", "1.1.2"),
            ("Qonunbuzar to‘g‘risida maʼlumot (F.I.Sh, yashash manzili)", "Сведения о нарушителе (Ф.И.Ш., адрес проживания)", "1.1.4"),
            ("Qonunbuzarlik soni", "Количество нарушений", "1.1.5"),
        ]

        for title_uz, title_ru, ordering in simple_items:
            StatementColumn.objects.create(
                statement=third_statement,
                parent=third_title_column,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=ordering
            )

        # Bayonnoma bloki
        bayonnoma_parent = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_title_column,
            title_uz="Tuzilgan bayonnoma yoki dalolatnoma (to‘ldirilishi shart)",
            title_ru="Составленные протоколы или свидетельства (обязательно к заполнению)",
            ordering="1.1.3"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=bayonnoma_parent,
            title_uz="Bayonnoma raqami va tuzilgan sanasi yoki dalolatnoma tuzilgan sana",
            title_ru="Номер протокола и дата составления или дата составления свидетельства",
            ordering="1.1.3.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=bayonnoma_parent,
            title_uz="Qonunbuzarlikni ro‘yxatga olish kitobidagi qayd raqami",
            title_ru="Номер записи в книге регистрации нарушений",
            ordering="1.1.3.2"
        )

        # Belgilangan summasi
        belgilangan_parent = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_title_column,
            title_uz="Belgilangan summasi (ming so‘m)",
            title_ru="Назначенная сумма (тыс. сум)",
            ordering="1.1.6"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=belgilangan_parent,
            title_uz="zarar",
            title_ru="ущерб",
            ordering="1.1.6.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=belgilangan_parent,
            title_uz="jarima",
            title_ru="штраф",
            ordering="1.1.6.2"
        )

        # O'z ixtiyori bilan to‘langan summa
        oz_ixtiyori_parent = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_title_column,
            title_uz="O‘z ixtiyori bilan to‘langan summasi (MJtK 332-modda)",
            title_ru="Сумма, уплаченная добровольно (статья 332 УК)",
            ordering="1.1.7"
        )
        for i, (title_uz, title_ru) in enumerate([("zarar", "ущерб"), ("jarima 50%", "штраф 50%"), ("jarima 70%", "штраф 70%"), ("jarima 100%", "штраф 100%")], start=1):
            StatementColumn.objects.create(
                statement=third_statement,
                parent=oz_ixtiyori_parent,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=f"1.1.7.{i}"
            )

        # Undirilmagan hujjatlar
        StatementColumn.objects.create(
            statement=third_statement,
            parent=third_title_column,
            title_uz="Undirilmagan zarar yoki jarima summasini undirish uchun hujjatlarni sud yoki MIB organlariga yuborilgan sana va xat raqami",
            title_ru="Дата и номер письма с документами для взыскания невыплаченного ущерба или штрафа, отправленные в суд или органы МЮ",
            ordering="1.1.8"
        )

        # Sud organlariga yuborilgan
        sud_parent = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_title_column,
            title_uz="Sud organlariga yuborilgan daʼvo arizalari",
            title_ru="Исковые заявления, отправленные в суд",
            ordering="1.1.9"
        )

        # Oddiy ustunlar
        simple_sud_items = [
            ("Qabul qilingan qaror (raqami va sanasi)", "Принятое решение (номер и дата)", "1.1.9.1"),
            ("Ajrim (to‘lovni undirish yoki MIB organlariga yuborish to‘g‘risida)", "Решение (о взыскании платежа или направлении в органы МЮ)", "1.1.9.2"),
            ("sud tomonidan rad etilganligir sabablari", "Причины отказа суда", "1.1.9.7"),
        ]
        for title_uz, title_ru, ordering in simple_sud_items:
            StatementColumn.objects.create(
                statement=third_statement,
                parent=sud_parent,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=ordering
            )

        # Ichki ustunlar bilan bloklar
        block_items = [
            ("undirilgan zarar summa (ming so‘mda)", "взысканная сумма ущерба (тыс. сум)", "1.1.9.3"),
            ("undirilmagan summa (ming so‘mda)", "невыплаченная сумма (тыс. сум)", "1.1.9.5"),
        ]
        for i, (block_title_uz, block_title_ru, block_order) in enumerate(block_items):
            block = StatementColumn.objects.create(
                statement=third_statement,
                parent=sud_parent,
                title_uz=block_title_uz,
                title_ru=block_title_ru,
                ordering=block_order
            )
            StatementColumn.objects.create(
                statement=third_statement,
                parent=block,
                title_uz="zarar",
                title_ru="ущерб",
                ordering=f"{block_order}.1"
            )
            StatementColumn.objects.create(
                statement=third_statement,
                parent=block,
                title_uz="jarima",
                title_ru="штраф",
                ordering=f"{block_order}.2"
            )

        # === Majburiy ijro byurosiga berilgan davo arizalari ===
        mib_parent = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_title_column,
            title_uz="Majburiy ijro byurosiga berilgan davo arizalari",
            title_ru="Исковые заявления, поданные в Бюро принудительного исполнения",
            ordering="1.1.10"
        )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=mib_parent,
            title_uz="MIB ga o‘tkazilgan xat nomeri va sanasi",
            title_ru="Номер и дата письма, переданного в МЮ",
            ordering="1.1.10.1"
        )

        # MIB bloklari
        mib_blocks = [
            ("undirilgan summa (ming so‘mda)", "взысканная сумма (тыс. сум)", "1.1.10.2"),
            ("undirilmagan zarar summa (ming so‘mda)", "невыплаченная сумма ущерба (тыс. сум)", "1.1.10.3"),
        ]
        for title_uz, title_ru, ordering in mib_blocks:
            parent_block = StatementColumn.objects.create(
                statement=third_statement,
                parent=mib_parent,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=ordering
            )
            StatementColumn.objects.create(
                statement=third_statement,
                parent=parent_block,
                title_uz="zarar",
                title_ru="ущерб",
                ordering=f"{ordering}.1"
            )
            StatementColumn.objects.create(
                statement=third_statement,
                parent=parent_block,
                title_uz="jarima",
                title_ru="штраф",
                ordering=f"{ordering}.2"
            )

        # === Jami summalar ===
        for title_uz, title_ru, ordering_prefix in [
            ("Jami undirilgan summasi (ming so‘mda)", "Общая взысканная сумма (тыс. сум)", "1.1.11"),
            ("Jami undirilmagan zarar summasi (ming so‘mda)", "Общая невыплаченная сумма ущерба (тыс. сум)", "1.1.12"),
        ]:
            parent_col = StatementColumn.objects.create(
                statement=third_statement,
                parent=third_title_column,
                title_uz=title_uz,
                title_ru=title_ru,
                ordering=ordering_prefix
            )
            StatementColumn.objects.create(
                statement=third_statement,
                parent=parent_col,
                title_uz="zarar",
                title_ru="ущерб",
                ordering=f"{ordering_prefix}.1"
            )
            StatementColumn.objects.create(
                statement=third_statement,
                parent=parent_col,
                title_uz="jarima",
                title_ru="штраф",
                ordering=f"{ordering_prefix}.2"
            )

        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'Предотвращение пожаров' Statement and Columns."))
        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'Борьба с вредителями и болезнями' Statement and Columns."))
        self.stdout.write(self.style.SUCCESS("✅ Успешно создано 'Нарушение закона' Statement and Columns."))
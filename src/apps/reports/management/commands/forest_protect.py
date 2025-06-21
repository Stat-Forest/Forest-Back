from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn


class Command(BaseCommand):
    help = "Create Statement Forest Protect"

    # ===================================================  YONG`INLARNI OLDINI OLISH
    def create_column_with_children(self, statement, parent, base_ordering, title, status_plan):
        parent_column = StatementColumn.objects.create(
            statement=statement,
            parent=parent,
            title=title,
            ordering=base_ordering
        )

        StatementColumn.objects.create(
            statement=statement,
            parent=parent_column,
            title="Reja",
            ordering=f"{base_ordering}.1",
            status_plan=status_plan
        )
        StatementColumn.objects.create(
            statement=statement,
            parent=parent_column,
            title="Amalda",
            ordering=f"{base_ordering}.2",
            status_plan=status_plan
        )

        return parent_column

    def handle(self, *args, **options):
        YILLIK = StatementColumn.PlanStatus.YILLIK

        root, _ = Statement.objects.get_or_create(name="O`rmonlarni muhofaza qilish")
        fire_prevent, _ = Statement.objects.get_or_create(parent=root, name="Yong`inlarni oldini olish")

        appendix = StatementColumn.objects.create(
            statement=fire_prevent,
            parent=None,
            title="Yong`inlarni oldini olish-ilovasi",
            ordering="1"
        )

        title_column = StatementColumn.objects.create(
            statement=fire_prevent,
            parent=appendix,
            title="O‘rmon xo‘jaligi agentligi tizim tashkilotlarida o‘rmon yong‘inlarini oldini olish bo‘yicha HISOBOTLAR",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=fire_prevent,
            parent=title_column,
            title="Xo‘jalik nomi",
            ordering="1.1.1",
            is_organization=True
        )

        new_construction = StatementColumn.objects.create(
            statement=fire_prevent,
            parent=title_column,
            title="Yong‘inga qarshi yangi quriladigan obyektlar, jumladan",
            ordering="1.1.2"
        )

        items_1_1_2 = [
            "oraliq joylar (km)",
            "yo‘llar (km)",
            "yong‘inga qarshi himoya chiziqlari (km)",
            "zovurlar (km)",
            "suv havzalari (m3)"
        ]

        for i, title in enumerate(items_1_1_2, start=1):
            self.create_column_with_children(
                statement=fire_prevent,
                parent=new_construction,
                base_ordering=f"1.1.2.{i}",
                title=title,
                status_plan=YILLIK
            )

        repairs = StatementColumn.objects.create(
            statement=fire_prevent,
            parent=title_column,
            title="Yong‘inga qarshi taʼmirlanadigan obyektlar, jumladan",
            ordering="1.1.3"
        )

        items_1_1_3 = [
            "oraliq joylar (km)",
            "yo‘llar (km)",
            "yong‘inga qarshi himoya chiziqlari (km)",
            "zovurlar (km)",
            "suv havzalari (m3)",
            "kichik hajmdagi suv zaxiralari (litrda)"
        ]

        for i, title in enumerate(items_1_1_3, start=1):
            self.create_column_with_children(
                statement=fire_prevent,
                parent=repairs,
                base_ordering=f"1.1.3.{i}",
                title=title,
                status_plan=YILLIK
            )

    # ===================================================  YONG`INLARNI OLDINI OLISH

        second_of_statement, _ = Statement.objects.get_or_create(
            parent=root,
            name="Zararkunanda va Kasalliklarga qarshi kurashish",
        )

        second_app_column = StatementColumn.objects.create(
            statement=second_of_statement,
            parent=None,
            title="Zararkunanda va Kasalliklarga qarshi kurashish-ilovasi.",
            ordering="1"
        )

        title_of_column = StatementColumn.objects.create(
            statement=second_of_statement,
            parent=second_app_column,
            title=(
                "O‘rmon xo‘jaligi agentligi tizim tashkilotlarida o‘rmon zararkunanda va kasalliklarini aniqlash "
                "va ularga qarshi kurashish bo‘yicha HISOBOTLAR"
            ),
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=second_of_statement,
            parent=title_of_column,
            title="Xo‘jalik nomi",
            ordering="1.1.1",
            is_organization=True
        )

        items = [
            "Zararkunanda va kasalliklarni aniqlash bo‘yicha o‘rganiladigan maydon (gektar)",
            "Aniqlangan zararkunanda va kasallikka qarshi kurashish bo‘yicha olib boriladigan tadbir (gektar)",
            "Shu jumladan zararkunandalarga qarshi o‘tkaziladigan biologik tadbir (gektar)",
        ]

        for idx, title in enumerate(items, start=2):
            self.create_column_with_children(
                statement=second_of_statement,
                parent=title_of_column,
                base_ordering=f"1.1.{idx}",
                title=title,
                status_plan=YILLIK
            )
    # ===================================================  XUQUQBUZARLIK

        third_statement, _ = Statement.objects.get_or_create(
            parent=root,
            name="Xuquqbuzarlik"
        )

        third_app_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=None,
            title="Xuquqbuzarlik-ilovasi",
            ordering="1"
        )

        third_title_column = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_app_column,
            title="HISOBOTLAR",
            ordering="1.1"
        )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=third_title_column,
            title="Xo‘jalik nomi",
            ordering="1.1.1",
            is_organization=True
        )

        simple_items = [
            ("Aniqlangan qonunbuzarlik turi", "1.1.2"),
            ("Qonunbuzar to‘g‘risida maʼlumot (F.I.Sh, yashash manzili)", "1.1.4"),
            ("Qonunbuzarlik soni", "1.1.5"),
        ]

        for title, ordering in simple_items:
            StatementColumn.objects.create(
                statement=third_statement,
                parent=third_title_column,
                title=title,
                ordering=ordering
            )

        # Bayonnoma bloki
        bayonnoma_parent = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_title_column,
            title="Tuzilgan Bayonnoma yoki dalolatnoma (to‘ldirilishi shart)",
            ordering="1.1.3"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=bayonnoma_parent,
            title="Bayonnoma raqami va tuzilgan sanasi yoki dalolatnoma tuzilgan sana",
            ordering="1.1.3.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=bayonnoma_parent,
            title="Qonunbuzarlikni ro‘yxatga olish kitobidagi qayd raqami",
            ordering="1.1.3.2"
        )

        # Belgilangan summasi
        belgilangan_parent = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_title_column,
            title="Belgilangan summasi (ming so‘m)",
            ordering="1.1.6"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=belgilangan_parent,
            title="zarar",
            ordering="1.1.6.1"
        )
        StatementColumn.objects.create(
            statement=third_statement,
            parent=belgilangan_parent,
            title="jarima",
            ordering="1.1.6.2"
        )

        # O'z ixtiyori bilan to‘langan summa
        oz_ixtiyori_parent = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_title_column,
            title="O‘z ixtiyori bilan to‘langan summasi (MJtK 332-modda)",
            ordering="1.1.7"
        )
        for i, label in enumerate(["zarar", "jarima 50%", "jarima 70%", "jarima 100%"], start=1):
            StatementColumn.objects.create(
                statement=third_statement,
                parent=oz_ixtiyori_parent,
                title=label,
                ordering=f"1.1.7.{i}"
            )

        # Undirilmagan hujjatlar
        StatementColumn.objects.create(
            statement=third_statement,
            parent=third_title_column,
            title="Undirilmagan zarar yoki jarima summasini undirish uchun hujjatlarni Sud yoki MIB "
                  "organlariga yuborilgan sana va xat raqami",
            ordering="1.1.8"
        )

        # Sud organlariga yuborilgan
        sud_parent = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_title_column,
            title="Sud organlariga yuborilgan daʼvo arizalari",
            ordering="1.1.9"
        )

        # Oddiy ustunlar
        simple_sud_items = [
            ("Qabul qilingan qaror (raqami va sanasi)", "1.1.9.1"),
            ("Ajrim (to‘lovni undirish yoki MIB organlariga yuborish to‘g‘risida)", "1.1.9.2"),
            ("sud tomonidan rad etilganligir sabablari", "1.1.9.7"),
        ]
        for title, ordering in simple_sud_items:
            StatementColumn.objects.create(
                statement=third_statement,
                parent=sud_parent,
                title=title,
                ordering=ordering
            )

        # Ichki ustunlar bilan bloklar
        block_items = [
            ("undirilgan zarar summa (ming so‘mda)", "1.1.9.3"),
            ("undirilmagan summa (ming so‘mda)", "1.1.9.5"),
        ]
        for i, (block_title, block_order) in enumerate(block_items):
            block = StatementColumn.objects.create(
                statement=third_statement,
                parent=sud_parent,
                title=block_title,
                ordering=block_order
            )
            StatementColumn.objects.create(
                statement=third_statement,
                parent=block,
                title="zarar",
                ordering=f"{block_order}.1"
            )
            StatementColumn.objects.create(
                statement=third_statement,
                parent=block,
                title="jarima",
                ordering=f"{block_order}.2"
            )

        # === Majburiy ijro byurosiga berilgan davo arizalari ===
        mib_parent = StatementColumn.objects.create(
            statement=third_statement,
            parent=third_title_column,
            title="Majburiy ijro byurosiga berilgan davo arizalari",
            ordering="1.1.10"
        )

        StatementColumn.objects.create(
            statement=third_statement,
            parent=mib_parent,
            title="MIB ga o‘tkazilgan xat nomeri va sanasi",
            ordering="1.1.10.1"
        )

        # MIB bloklari
        mib_blocks = [
            ("undirilgan summa (ming so‘mda)", "1.1.10.2"),
            ("undirilmagan zarar summa (ming so‘mda)", "1.1.10.3"),
        ]
        for title, ordering in mib_blocks:
            parent_block = StatementColumn.objects.create(
                statement=third_statement,
                parent=mib_parent,
                title=title,
                ordering=ordering
            )
            StatementColumn.objects.create(
                statement=third_statement,
                parent=parent_block,
                title="zarar",
                ordering=f"{ordering}.1"
            )
            StatementColumn.objects.create(
                statement=third_statement,
                parent=parent_block,
                title="jarima",
                ordering=f"{ordering}.2"
            )

        # === Jami summalar ===
        for title, ordering_prefix in [
            ("Jami undirilgan summasi (ming so‘mda)", "1.1.11"),
            ("Jami undirilmagan zarar summasi (ming so‘mda)", "1.1.12"),
        ]:
            parent_col = StatementColumn.objects.create(
                statement=third_statement,
                parent=third_title_column,
                title=title,
                ordering=ordering_prefix
            )
            StatementColumn.objects.create(
                statement=third_statement,
                parent=parent_col,
                title="zarar",
                ordering=f"{ordering_prefix}.1"
            )
            StatementColumn.objects.create(
                statement=third_statement,
                parent=parent_col,
                title="jarima",
                ordering=f"{ordering_prefix}.2"
            )

        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Yong`inlarni oldini olish' Statement and Columns."))
        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Zararkunanda va kasalliklarga qarshi kurashish' Statement and Columns."))
        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Xuquqbuzarlik' Statement and Columns."))
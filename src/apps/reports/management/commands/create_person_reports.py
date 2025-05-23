from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn


class Command(BaseCommand):
    help = "Create Statement Column for Hodim Hisobi"

    def handle(self, *args, **options):
        first_statement = Statement.objects.create(
            parent=None,
            name="Insoniyat resurslarini boshqarish",
            period=None,
            icon=None,
        )
        second_statement = Statement.objects.create(
            parent=first_statement,
            name="Xodimlar hisobi",
            period=None,
            icon=None
        )

        firest_ilova_column = StatementColumn.objects.create(
            statement=second_statement,
            parent=None,
            title="1-ilova",
            ordering="1",
        )
        title_column = StatementColumn.objects.create(
            parent=firest_ilova_column,
            title="Inson Resurslari blablablablablablablabla",
            ordering="1.1"
        )
        organization_name_column = StatementColumn.objects.create(
            parent=title_column,
            title="Tashkilot nomi",
            ordering="1.1.1",
            is_organization=True
        )
        first_statement_column = StatementColumn.objects.create(
            parent=title_column,
            title="Jami xodimlar soni",
            ordering="1.1.2"
        )
        second_statement_column = StatementColumn.objects.create(
            parent=title_column,
            title="Shundan",
            ordering="1.1.3"
        )
        third_statement_column = StatementColumn.objects.create(
            parent=second_statement_column,
            title="Boshqaruv xodimlari",
            ordering="1.1.3.1"
        )
        fourth_statement_column = StatementColumn.objects.create(
            parent=second_statement_column,
            title="Mutaxassislar",
            ordering="1.1.3.2"
        )
        fifth_statement_column = StatementColumn.objects.create(
            parent=second_statement_column,
            title="Ishlab chiqarish xodimlari",
            ordering="1.1.3.3"
        )
        sixth_statement_column = StatementColumn.objects.create(
            parent=second_statement_column,
            title="Texnik hodim",
            ordering="1.1.3.4"
        )
        seventh_statement_column = StatementColumn.objects.create(
            parent=second_statement_column,
            title="Xizmat korsatuvchi xodimlar",
            ordering="1.1.3.5",
        )
        eighth_statement_column = StatementColumn.objects.create(
            parent=second_statement_column,
            title="ishchilar",
            ordering="1.1.3.6"
        )
        nineth_statement_column = StatementColumn.objects.create(
            parent=title_column,
            title="Jami vakatlar soni",
            ordering="1.1.4"
        )
        tenth_statement_column = StatementColumn.objects.create(
            parent=title_column,
            title="shundan-2",
            ordering="1.1.5"
        )
        eleventh_statement_column = StatementColumn.objects.create(
            parent=tenth_statement_column,
            title="Boshqaruv hodimlari",
            ordering="1.1.5.1"
        )
        twelfth_statement_column = StatementColumn.objects.create(
            parent=tenth_statement_column,
            title="Mutaxassislar",
            ordering="1.1.5.2"
        )

        on_uch_statement_column = StatementColumn.objects.create(
            parent=tenth_statement_column,
            title="Ishlab chiqarish xodimlari",
            ordering="1.1.5.3"
        )
        on_tort_statement_column = StatementColumn.objects.create(
            parent=tenth_statement_column,
            title="Texnik xodim",
            ordering="1.1.5.4"
        )
        on_besh_statement_column = StatementColumn.objects.create(
            parent=tenth_statement_column,
            title="Xizmat korsatuvchi xodimlar",
            ordering="1.1.5.5"
        )
        on_olti_statement_column = StatementColumn.objects.create(
            parent=tenth_statement_column,
            title="Ishchilar",
            ordering="1.1.5.6"
        )
        on_yetti_statement_column = StatementColumn.objects.create(
            parent=title_column,
            title="Amallar",
            ordering="1.1.6"
        )

        second_ilova_column = StatementColumn.objects.create(
            statement=second_statement,
            parent=None,
            title="2-ilova",
            ordering="1"
        )

        title_second_column = StatementColumn.objects.create(
            parent=second_ilova_column,
            title="2-ilovani title blablablablablablablabla",
            ordering="1.1"
        )
        second_organization_column = StatementColumn.objects.create(
            parent=title_second_column,
            title="Tashkilot Nomi 2-ilovaniki",
            ordering="1.1.1",
            is_organization=True
        )

        first_column = StatementColumn.objects.create(
            parent=title_second_column,
            title="Shtat boicha jami",
            ordering="1.1.2"
        )
        second_column = StatementColumn.objects.create(
            parent=title_second_column,
            title="Jami ishlovchi xodimlar soni",
            ordering="1.1.3"
        )
        information = StatementColumn.objects.create(
            parent=title_second_column,
            title="Ma`lumoti",
            ordering="1.1.4"
        )
        fifth_column = StatementColumn.objects.create(
            parent=information,
            title="Oliy",
            ordering="1.1.4.1"
        )
        sixth_column = StatementColumn.objects.create(
            parent=information,
            title="O`rta maxsus",
            ordering="1.1.4.2"
        )
        seventh_column = StatementColumn.objects.create(
            parent=information,
            title="O`rta",
            ordering="1.1.4.3"
        )
        employees = StatementColumn.objects.create(
            parent=title_second_column,
            title="Xodimlar",
            ordering="1.1.5"
        )
        nineth_column = StatementColumn.objects.create(
            parent=employees,
            title="Ayol",
            ordering="1.1.5.1"
        )
        tenth_column = StatementColumn.objects.create(
            parent=employees,
            title="Erkak",
            ordering="1.1.5.2"
        )
        eleventh_column = StatementColumn.objects.create(
            parent=employees,
            title="Yoshlar Jami",
            ordering="1.1.5.3"
        )
        young_people = StatementColumn.objects.create(
            parent=employees,
            title="Yoshlar",
            ordering="1.1.5.4"
        )
        on_uch_column = StatementColumn.objects.create(
            parent=young_people,
            title="Qizlar",
            ordering="1.1.5.4.1"
        )

        on_tort_column = StatementColumn.objects.create(
            parent=young_people,
            title="Yigitlar",
            ordering="1.1.5.4.2"
        )
        on_besh_column = StatementColumn.objects.create(
            parent=employees,
            title="Nafaqadagi xodimlar",
            ordering="1.1.5.5"
        )

        on_olti_column = StatementColumn.objects.create(
            parent=title_second_column,
            title="Ilmiy darajaga ega xodimlar",
            ordering="1.1.6"
        )

        on_yetti_column = StatementColumn.objects.create(
            parent=title_second_column,
            title="Xorijiy til biladigan xodimlar",
            ordering="1.1.7"
        )

        on_sakkiz_column = StatementColumn.objects.create(
            parent=title_second_column,
            title="Chet elda tashil olgan va malaka oshirgan xodimlar",
            ordering="1.1.8"
        )

        on_toqqiz_column = StatementColumn.objects.create(
            parent=title_second_column,
            title="Amallar",
            ordering="1.1.9"
        )

        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Hodim Hisobi' StatementColumns."))
from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn
from apps.utils.services import PeriodChoices

class Command(BaseCommand):
    help = "Create Statement Column for Hodim Hisobi"

    def handle(self, *args, **options):

        # StatementColumn.objects.filter(statement__name="Xodimlar hisobi").delete()
        # Statement.objects.filter(name="Xodimlar hisobi").delete()
        # if not Statement.objects.exists():
        #     Statement.objects.filter(name="Insoniyat resurslarini boshqarish").delete()

        person_statement = Statement.objects.create(
            parent=None,
            name="Insoniyat resurslarini boshqarish",
            period=None,
            icon=None,
        )
        person_report_statement = Statement.objects.create(
            parent=person_statement,
            name="Xodimlar hisobi",
            period=PeriodChoices.CHORAKLIK
        )

        # ==================== 1- ILOVA ========================


        firest_ilova_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=None,
            title="1-ilova",
            ordering="1.1",
        )
        title_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=firest_ilova_column,
            title="2025 yil uchun xodimlar togrisidagi hisobat",
            ordering="1.1.1"
        )
        organization_name_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_column,
            title="Tashkilot nomi",
            ordering="1.1.1.1",
            is_organization=True
        )
        first_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_column,
            title="Jami xodimlar soni",
            ordering="1.1.1.2"
        )
        second_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_column,
            title="Shundan",
            ordering="1.1.1.3"
        )
        third_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=second_statement_column,
            title="Boshqaruv xodimlari",
            ordering="1.1.1.3.1"
        )
        fourth_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=second_statement_column,
            title="Mutaxassislar",
            ordering="1.1.1.3.2"
        )
        fifth_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=second_statement_column,
            title="Ishlab chiqarish xodimlari",
            ordering="1.1.1.3.3"
        )
        sixth_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=second_statement_column,
            title="Texnik hodim",
            ordering="1.1.1.3.4"
        )
        seventh_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=second_statement_column,
            title="Xizmat korsatuvchi xodimlar",
            ordering="1.1.1.3.5",
        )
        eighth_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=second_statement_column,
            title="ishchilar",
            ordering="1.1.1.3.6"
        )
        nineth_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_column,
            title="Jami vakatlar soni",
            ordering="1.1.1.4"
        )
        tenth_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_column,
            title="shundan-2",
            ordering="1.1.1.5"
        )
        eleventh_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=tenth_statement_column,
            title="Boshqaruv hodimlari",
            ordering="1.1.1.5.1"
        )
        twelfth_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=tenth_statement_column,
            title="Mutaxassislar",
            ordering="1.1.1.5.2"
        )

        on_uch_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=tenth_statement_column,
            title="Ishlab chiqarish xodimlari",
            ordering="1.1.1.5.3"
        )
        on_tort_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=tenth_statement_column,
            title="Texnik xodim",
            ordering="1.1.1.5.4"
        )
        on_besh_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=tenth_statement_column,
            title="Xizmat korsatuvchi xodimlar",
            ordering="1.1.1.5.5"
        )
        on_olti_statement_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=tenth_statement_column,
            title="Ishchilar",
            ordering="1.1.1.5.6"
        )

        #==================== 2- ILOVA ========================

        second_ilova_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=None,
            title="2-ilova",
            ordering="1.2"
        )

        title_second_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=second_ilova_column,
            title="Tizim tashkilotlaridagi xodimlarni sifat tarkibi togrisida malumot",
            ordering="1.2.1"
        )
        second_organization_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_second_column,
            title="Tashkilot Nomi ",
            ordering="1.2.1.1",
            is_organization=True
        )

        first_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_second_column,
            title="Shtat boicha jami",
            ordering="1.2.1.2"
        )
        second_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_second_column,
            title="Jami ishlovchi xodimlar soni",
            ordering="1.2.1.3"
        )
        information = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_second_column,
            title="Ma`lumoti",
            ordering="1.2.1.4"
        )
        fifth_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=information,
            title="Oliy",
            ordering="1.2.1.4.1"
        )
        sixth_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=information,
            title="O`rta maxsus",
            ordering="1.2.1.4.2"
        )
        seventh_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=information,
            title="O`rta",
            ordering="1.2.1.4.3"
        )
        employees = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_second_column,
            title="Xodimlar",
            ordering="1.2.1.5"
        )
        nineth_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=employees,
            title="Ayol",
            ordering="1.2.1.5.1"
        )
        tenth_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=employees,
            title="Erkak xodimlar",
            ordering="1.2.1.5.2"
        )
        eleventh_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=employees,
            title="Yoshlar Jami",
            ordering="1.2.1.5.3"
        )
        young_people = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=employees,
            title="Yoshlar",
            ordering="1.2.1.5.4"
        )
        on_uch_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=young_people,
            title="Qizlar",
            ordering="1.2.1.5.4.1"
        )

        on_tort_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=young_people,
            title="Yigitlar",
            ordering="1.2.1.5.4.2"
        )
        on_besh_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=employees,
            title="Nafaqadagi xodimlar",
            ordering="1.2.1.5.5"
        )

        on_olti_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_second_column,
            title="Ilmiy darajaga ega xodimlar",
            ordering="1.2.1.6"
        )

        on_yetti_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_second_column,
            title="Xorijiy til biladigan xodimlar",
            ordering="1.2.1.7"
        )

        on_sakkiz_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_second_column,
            title="Chet elda tashil olgan va malaka oshirgan xodimlar",
            ordering="1.2.1.8"
        )

        # =========================== 3 -ILOVA ========================

        third_ilova_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=None,
            title="3-ilova",
            ordering="1.3"
        )

        title_third_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=third_ilova_column,
            title="Tizim tashkilotlaridagi xodimlarni sifat tarkibi togrisida malumot",
            ordering="1.3.1"
        )
        third_organization_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_third_column,
            title="Tashkilot Nomi ",
            ordering="1.3.1.1",
            is_organization=True
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_third_column,
            title="Jami yangi yaratilgan ish o'rinlar soni ",
            ordering="1.3.1.2",
        )
        from_that = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_third_column,
            title="Shundan",
            ordering="1.3.1.3",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=from_that,
            title="Doimiy",
            ordering="1.3.1.3.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=from_that,
            title="Mavsumiy",
            ordering="1.3.1.3.2",
        )
        under_30 =StatementColumn.objects.create(
            statement=person_report_statement,
            parent=from_that,
            title=" Yoshlar (30 yoshgacha)",
            ordering="1.3.1.3.3",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=under_30,
            title="Erkak",
            ordering="1.3.1.3.3.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=under_30,
            title="Xotin qizlar",
            ordering="1.3.1.3.3.2",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=from_that,
            title="Temir daftar va ayollar daftariga kiritilgan",
            ordering="1.3.1.3.4",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=from_that,
            title="Kambag’al axolidan olingan",
            ordering="1.3.1.3.5",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=from_that,
            title="Kasanachilik asosida",
            ordering="1.3.1.3.6",
        )


        self.stdout.write(self.style.SUCCESS("✅ Successfully created 'Hodim Hisobi' StatementColumns."))

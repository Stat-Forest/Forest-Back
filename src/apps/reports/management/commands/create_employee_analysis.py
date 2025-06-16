from django.core.management import BaseCommand

from apps.reports.models import Statement, StatementColumn
from apps.utils.services import PeriodChoices

class Command(BaseCommand):
    help = "Create Statement Column for Hodim Hisobi Taxlili"

    def handle(self, *args, **options):

        # StatementColumn.objects.filter(statement__name="Xodimlar hisobi taxlili").delete()
        # Statement.objects.filter(name="Xodimlar hisobi taxlili").delete()

        person_statement = Statement.objects.get(
            name="Insoniyat resurslarini boshqarish",
        )
        person_report_statement = Statement.objects.create(
            parent=person_statement,
            name="Xodimlar hisobi taxlili",
            period=PeriodChoices.YILLIK
        )

        # ==================== 1- ILOVA ========================


        firest_ilova_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=None,
            title="4-ilova",
            ordering="1.4",
        )
        title_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=firest_ilova_column,
            title="2025 yil uchun xodimlar statistikasi togrisidagi malumot",
            ordering="1.4.1"
        )

        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_column,
            title="Tashkilot nomi",
            ordering="1.4.1.1",
            is_organization=True
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_column,
            title="Tasdiqlanagan shtat birligi boyicha xodimlar soni(faqat boshqaruv hodimlar soni)",
            ordering="1.4.1.2"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_column,
            title="Amaldagi xodimlar soni(faqat boshqaruv hodimlar soni)",
            ordering="1.4.1.3"
        )

        age_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_column,
            title="Xodimlarning yosh boyicha tarkibi",
            ordering="1.4.1.4"
        )

        age_ranges = [
            "30 yoshgacha bolgan",
            "30 yoshdan 40 yoshgacha bolgan",
            "40 yoshdan 50 yoshgacha bolgan",
            "50 yoshdan 60 yoshgacha bolgan",
            "60 yoshdan yuqori bolgan",
            "Yoshga doir pensiya olayotgan va pensiyaga chiqish huquqiga ega bolib ishlayotgan",
            "2025 yilda pensiya yoshiga yetadigan"
        ]
        for i, title in enumerate(age_ranges, 1):
            StatementColumn.objects.create(
                statement=person_report_statement,
                parent=age_column,
                title=f"{title} boshqaruv xodimlari soni",
                ordering=f"1.4.1.4.{i}"
            )

        exp_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_column,
            title="Xodimlarning ish staji boyicha tarkibi",
            ordering="1.4.1.5"
        )

        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=exp_column,
            title="2 yilgacha",
            ordering="1.4.1.5.1"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=exp_column,
            title="2 yildan ortiq",
            ordering="1.4.1.5.2"
        )

        info_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_column,
            title="Xodimlarning malumot  boyicha tarkibi",
            ordering="1.4.1.6"
        )

        info_fields = [
            "Pedagogika fanlari", "Gumanitar fanlari", "Tabiiy fanlar, matematika va fizika", "Sanoat sahosi",
            "Jurnalistika va axborat", "Iqtisot, bizness va boshqaruv", "Huquq va siyosat", "Muhandislik ishi",
            "Ishlab chiqarish va ishlov berish sohalari", "Arxitektura va qurilish",
            "Qishloq,Urmon va baliq xojaligi ,Irrigatsiya va Viterenariya"
        ]
        for i, title in enumerate(info_fields, 1):
            StatementColumn.objects.create(
                statement=person_report_statement,
                parent=info_column,
                title=title,
                ordering=f"1.4.1.6.{i}"
            )

        degree_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_column,
            title="Xodimlarning darajasi  boyicha tarkibi",
            ordering="1.4.1.7"
        )

        degree_fields = [
            "Sog'liqni saqlash",
            "Komputer texnologiyalari va informatika",
            "PHD, fan nomzodi ilmiy darajasi ega xodimlar soni",
            "Magister darajasi ega xodimlar soni",
            "Bakalavr darajasiga ega xodimlar",
            "O'rta mahsus malumotli xodimlar soni",
            "Xalqaro e’tirof etilgan (...) tamomlagan xodimlar soni"
        ]
        for i, title in enumerate(degree_fields, 1):
            StatementColumn.objects.create(
                statement=person_report_statement,
                parent=degree_column,
                title=title,
                ordering=f"1.4.1.7.{i}"
            )

        ser_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_column,
            title="Xorijiy tillarni biluvchi xodimlar (...)",
            ordering="1.4.1.8"
        )

        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=ser_column,
            title="Xalqaro sertifikatga ega xodimlar soni",
            ordering="1.4.1.8.1"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=ser_column,
            title="Milliy sertifikatga ega xodimlar soni",
            ordering="1.4.1.8.2"
        )

        vak_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_column,
            title="Mavjud vakant (...) lavozimlar bo‘yicha mutaxassisliklar",
            ordering="1.4.1.9"
        )

        vak_fields = [
            "Pedagogika fanlari", "Gumanitar fanlar", "Tabiiy fanlar, matematika va fizika", "San’at sohasi",
            "Jurnalistika va axborot", "Iqtisod, biznes va boshqaruv", "Huquq va siyosat", "Muhandislik ishi",
            "Ishlab chiqarish va ishlov berish sohalari", "Arxitektura va qurilish",
            "Qishloq, o‘rmon va baliq xo‘jaligi, irrigatsiya va melioratsiya, veterinariya",
            "Xizmat ko‘rsatish sohasi", "Transport va logistika", "Ijtimoiy va xulq-atvorga mansub fanlar",
            "Sog‘liqni saqlash", "Kompyuter texnologiyalari va informatika"
        ]
        for i, title in enumerate(vak_fields, 1):
            StatementColumn.objects.create(
                statement=person_report_statement,
                parent=vak_column,
                title=title,
                ordering=f"1.4.1.9.{i}"
            )

        # ==================== 2- ILOVA ========================

        second_ilova_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=None,
            title="5-ilova",
            ordering="1.5",
        )
        title_2_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=second_ilova_column,
            title="O‘rmon xo‘jaligi xodimlari to‘g‘risidagi statistik tahlili",
            ordering="1.5.1"
        )

        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_2_column,
            title="Tashkilot nomi",
            ordering="1.5.1.1",
            is_organization=True
        )
        f_1_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_2_column,
            title="Xodimlarning ish faoliyati me'yorlari va mehnat muhofazasi",
            ordering="1.5.1.2"
        )

        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_1_column,
            title="Tasdiqlangan shtat birligi bo‘yicha xodimlar soni",
            ordering="1.5.1.2.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_1_column,
            title="Shundan xotin-qizlar soni",
            ordering="1.5.1.2.2",
        )
        f_1_1_column=StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_1_column,
            title="Xodimlarning yosh bo‘yicha tarkibi",
            ordering="1.5.1.2.3",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_1_1_column,
            title="30 yoshgacha bo‘lgan xodimlar soni:",
            ordering="1.5.1.2.3.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_1_1_column,
            title="30 yoshdan 50 yoshgacha bo‘lgan xodimlar soni",
            ordering="1.5.1.2.3.2",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_1_1_column,
            title="50 yoshdan yuqori bo‘lgan xodimlar soni",
            ordering="1.5.1.2.3.3",
        )
        f_1_2_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_1_column,
            title="Xodim ish vaqti me'yorlarining ish hajmiga mutanosibligi (foizda)",
            ordering="1.5.1.2.4",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_1_2_column,
            title="Yillik rejaga muvofiq amalga oshiriladigan ish",
            ordering="1.5.1.2.4.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_1_2_column,
            title="Va shunga muvofiq ish hajmining mavjudligi",
            ordering="1.5.1.2.4.2",
        )

        #f_1_3_column
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_1_column,
            title="Bir hisobot yili davomida mehnat ta’tiliga chiqqan xodimlar soni",
            ordering="1.5.1.2.5",
        )
        f_1_4_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_1_column,
            title="Xodimning ish vaqtidan tashqari ishlaganligi uchun qo‘shimcha to‘lov to‘langanligi",
            ordering="1.5.1.2.6",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_1_4_column,
            title="Mablag‘ sarfi, mln. so‘mda",
            ordering="1.5.1.2.6.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_1_4_column,
            title="Dam olish va bayram kunlari ishga jalb qilingan xodimlar soni",
            ordering="1.5.1.2.6.2",
        )
        #f_1_5_column
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_1_column,
            title="Xodimlarning ish vaqtini hisobga olishning avtomatlashtirilgan tizimining mavjudligi (mavjud yoki mavjud emas)",
            ordering="1.5.1.2.7",
        )

        f_2_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_2_column,
            title="Kadrlar qo‘nimsizligi va xodimlarning kasbiy o‘sishi",
            ordering="1.5.1.3"
        )


        f_2_1_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_column,
            title="Xodimlarning bir lavozimda bo‘lishi davomiyligi (yillarda)",
            ordering="1.5.1.3.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_1_column,
            title="Direktor",
            ordering="1.5.1.3.1.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_1_column,
            title="Direktor o'rin bosari",
            ordering="1.5.1.3.1.2",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_1_column,
            title="Bolim boshlig'i",
            ordering="1.5.1.3.1.3",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_1_column,
            title="Sho‘ba mudiri",
            ordering="1.5.1.3.1.4",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_1_column,
            title="Bosh mutaxassislar",
            ordering="1.5.1.3.1.5",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_1_column,
            title="Mutaxassislar",
            ordering="1.5.1.3.1.6",
        )

        f_2_2_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_column,
            title="Xodimlarni ishga qabul qilish",
            ordering="1.5.1.3.2",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_2_column,
            title="2025-yil",
            ordering="1.5.1.3.2.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_2_column,
            title="2024-yil",
            ordering="1.5.1.3.2.2",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_2_column,
            title="2023-yil",
            ordering="1.5.1.3.2.3",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_2_column,
            title="2022-yil",
            ordering="1.5.1.3.2.4",
        )
        f_2_3_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_column,
            title="Xodimlarni ishdan boshatish",
            ordering="1.5.1.3.3",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_3_column,
            title="2025-yil",
            ordering="1.5.1.3.3.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_3_column,
            title="2024-yil",
            ordering="1.5.1.3.3.2",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_3_column,
            title="2023-yil",
            ordering="1.5.1.3.3.3",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_3_column,
            title="2022-yil",
            ordering="1.5.1.3.3.4",
        )
        f_2_4_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_column,
            title="Xodimlarning kasbiy o‘sishi",
            ordering="1.5.1.3.4",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_4_column,
            title="Yuqori lavozimlar",
            ordering="1.5.1.3.4.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_4_column,
            title="Teng lavozimlar",
            ordering="1.5.1.3.4.2",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_4_column,
            title="Quyi lavozimlar",
            ordering="1.5.1.3.4.3",
        )
        f_2_4_1_column =StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_4_column,
            title="Xodimlarning kasbiy o‘sishi",
            ordering="1.5.1.3.4.4",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_4_1_column,
            title="Departament mudiri",
            ordering="1.5.1.3.4.4.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_4_1_column,
            title="Boshqarma boshlig‘i",
            ordering="1.5.1.3.4.4.2",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_4_1_column,
            title="Bo‘lim boshlig‘i",
            ordering="1.5.1.3.4.4.3",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_4_1_column,
            title="Sho'ba mudiri",
            ordering="1.5.1.3.4.4.4",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_4_1_column,
            title="Mutaxassislar",
            ordering="1.5.1.3.4.4.5",
        )
        f_2_5_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_column,
            title="Malaka oshirgan va qayta o‘qish kurslariga qatnashgan xodimlar soni",
            ordering="1.5.1.3.5",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_5_column,
            title="Jami",
            ordering="1.5.1.3.5.1",
        )
        f_2_5_1_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_5_column,
            title="shu jumladan",
            ordering="1.5.1.3.5.2",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_5_1_column,
            title="Departament mudiri",
            ordering="1.5.1.3.5.2.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_5_1_column,
            title="Boshqarma boshlig‘i",
            ordering="1.5.1.3.5.2.2",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_5_1_column,
            title="Bo‘lim boshlig‘i",
            ordering="1.5.1.3.5.2.3",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_5_1_column,
            title="Sho'ba mudiri",
            ordering="1.5.1.3.5.2.4",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_5_1_column,
            title="Mutaxassilar",
            ordering="1.5.1.3.5.2.5",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_column,
            title="Kasallik varaqasi bo‘yicha vaqtincha mehnatga layoqatsizlik davrida bo‘lgan xodimlar va o‘rtacha davolanish (kasallik varaqasi) muddati (soni va o‘rtacha muddati)",
            ordering="1.5.1.3.6",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_column,
            title="Xodimlarni davolash va tibbiy profilaktika choralari uchun to‘langan mablag‘",
            ordering="1.5.1.3.7",
        )
        f_2_8_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_column,
            title="Xodimlarning kasallik turlari (5 yillik dinamikasi bilan)",
            ordering="1.5.1.3.8",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_8_column,
            title="Jami",
            ordering="1.5.1.3.8.1",
        )
        f_2_8_1_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_8_column,
            title="Shu jumladan",
            ordering="1.5.1.3.8.2",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_8_1_column,
            title="Yurak va qon tomir",
            ordering="1.5.1.3.8.2.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_8_1_column,
            title="Asab",
            ordering="1.5.1.3.8.2.2",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_8_1_column,
            title="Oshqazon ichak kasaliklari",
            ordering="1.5.1.3.8.2.3",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_column,
            title="Sport bilan shug‘ullanuvchi xodimlar soni va ushbu tadbirlar uchun to‘langan mablag‘ (kasaba uyushmasi mablag‘laridan tashqari)",
            ordering="1.5.1.3.9",
        )
        f_2_10_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_column,
            title="Madaniy-ma’rifiy tadbirlarda qatnashgan xodimlar va ushbu tadbirlar uchun to‘langan mablag‘lar (kasaba uyushmasi mablag‘laridan tashqari)",
            ordering="1.5.1.3.10",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_10_column,
            title="Jami",
            ordering="1.5.1.3.10.1",
        )
        f_2_10_1_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_column,
            title="Shu jumladan",
            ordering="1.5.1.3.10.2",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_10_1_column,
            title="Teatr",
            ordering="1.5.1.3.10.2.1",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_10_1_column,
            title="KIno",
            ordering="1.5.1.3.10.2.2",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_10_1_column,
            title="Konsert",
            ordering="1.5.1.3.10.2.3",
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=f_2_10_1_column,
            title="Boshqalar",
            ordering="1.5.1.3.10.2.4",
        )



        # ================ 3 -ILOVA ========================

        third_ilova_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=None,
            title="6-ilova",
            ordering="1.6",
        )
        title_3_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=third_ilova_column,
            title="Oliy ta’lim muassasalari va kasb-hunar kollejlarini tamomlagan o‘rmon xo‘jaligi mutaxassislariga bo‘lgan talab",
            ordering="1.6.1"
        )

        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_3_column,
            title="Tashkilot nomi",
            ordering="1.6.1.1",
            is_organization=True
        )
        r_1_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_3_column,
            title="Bosh o‘rmonchi, o‘rmon xo‘jaligi muhandisi, o‘rmonchi, nazoratchi, egermayor va boshqa o‘rmon xo‘jaligi mutaxassislari",
            ordering="1.6.1.2"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_1_column,
            title="Jami",
            ordering="1.6.1.2.1"
        )
        r_1_1_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_1_column,
            title="Shundan",
            ordering="1.6.1.2.2"
        )
        r_1_1_1_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_1_1_column,
            title="Oliy ma'lumotli",
            ordering="1.6.1.2.2.1"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_1_1_1_column,
            title="Jami",
            ordering="1.6.1.2.2.1.1"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_1_1_1_column,
            title="O'rmonshunos",
            ordering="1.6.1.2.2.1.2"
        )
        r_1_1_2_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_1_1_column,
            title="O'rta-maxsus malumotli",
            ordering="1.6.1.2.2.2"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_1_1_2_column,
            title="Jami",
            ordering="1.6.1.2.2.2.1"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_1_1_2_column,
            title="O'rmonshunos",
            ordering="1.6.1.2.2.2.1"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_1_1_column,
            title="O'rta malumotli",
            ordering="1.6.1.2.2.3"
        )

        r_2_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=title_3_column,
            title="Ma’lumot darajasi bo‘yicha mutaxassislarga bo‘lgan talab",
            ordering="1.6.1.6"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent= r_2_column,
            title="Jami",
            ordering="1.6.1.6.1"
        )
        r_2_1_column=StatementColumn.objects.create(
            statement=person_report_statement,
            parent= r_2_column,
            title="Shundan",
            ordering="1.6.1.6.2"
        )
        r_2_1_1_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_2_1_column,
            title="Magister",
            ordering="1.6.1.6.2.1"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_2_1_1_column,
            title="2025",
            ordering="1.6.1.6.2.1.1"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_2_1_1_column,
            title="2026",
            ordering="1.6.1.6.2.1.2"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_2_1_1_column,
            title="2027",
            ordering="1.6.1.6.2.1.6"
        )

        r_2_1_2_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_2_1_column,
            title="Oliy ma'lu,otli",
            ordering="1.6.1.6.2.2"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_2_1_2_column,
            title="2025",
            ordering="1.6.1.6.2.2.1"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_2_1_2_column,
            title="2026",
            ordering="1.6.1.6.2.2.2"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_2_1_2_column,
            title="2027",
            ordering="1.6.1.6.2.2.3"
        )
        r_2_1_3_column = StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_2_1_column,
            title="O'rta-maxsus malumotli",
            ordering="1.6.1.6.2.3"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_2_1_3_column,
            title="2025",
            ordering="1.6.1.6.2.3.1"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_2_1_3_column,
            title="2026",
            ordering="1.6.1.6.2.3.2"
        )
        StatementColumn.objects.create(
            statement=person_report_statement,
            parent=r_2_1_3_column,
            title="2027",
            ordering="1.6.1.6.2.3.3"
        )


        self.stdout.write(self.style.SUCCESS("Successfully created 'Hodim Hisobi Tahlili' StatementColumns."))

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.reports.models import Statement, StatementColumn
from apps.reports.models.statement_column import StatementColumn as SC
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    help = 'Creates default Statement and StatementColumn data'

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            urmon_management = Statement.objects.create(
                name="O'rmon kadastri,ijara",
                parent=None
            )
            land_management = Statement.objects.create(
                name="Yer o'zlashtirish",
                parent=urmon_management,
                period=PeriodChoices.OYLIK,
            )

            land_management_2 = Statement.objects.create(
                name="Ijaraga berilgan yerlar hisobi",
                parent=urmon_management,
                period=PeriodChoices.OYLIK,
            )
            land_management_3 = Statement.objects.create(
                name="Urmon bilan qoplangan yerlar",
                parent=urmon_management,
                period=PeriodChoices.YILLIK,
            )
            land_4 = StatementColumn.objects.create(
                statement=land_management_3,
                parent=None,
                title="2-ilova",
                ordering="1.4"
            )
            land_3 = StatementColumn.objects.create(
                statement=land_management_3,
                parent=None,
                title="1-ilova",
                ordering="1.3"
            )
            land_2 = StatementColumn.objects.create(
                statement=land_management_2,
                parent=None,
                title="1-ilova",
                ordering="1.2"
            )

            land_1 = StatementColumn.objects.create(
                statement=land_management,
                parent=None,
                title="1-ilova",
                ordering="1.1"
            )
            land_info_4 = StatementColumn.objects.create(
                statement=land_management_3,
                parent=land_4,
                title="Urmon bilan qoplangan yerlar tematik qatlam atributiv ma'lumotlari",
                ordering="1.4.1"
            )
            land_info_3 = StatementColumn.objects.create(
                statement=land_management_3,
                parent=land_3,
                title="O‘rmon bo‘limlari tematik qatlamining atributiv ma’lumotlari",
                ordering="1.3.1"
            )
            land_info_2 = StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_2,
                title="2025 yilda xar bir ijarachi boyicha malumot",
                ordering="1.2.1"
            )
            land_info = StatementColumn.objects.create(
                statement=land_management,
                parent=land_1,
                title="2025 yilda foydalanishga kiritiladigan o‘rmon fondi yerlari maydoni to‘g‘risida ma’lumot",
                ordering="1.1.1"
            )
            StatementColumn.objects.create(
                statement=land_management,
                parent=land_info,
                title="Tashkilot nami",
                ordering="1.1.1.1",
                is_organization=True
            )
            StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_info_2,
                title="Tashkilot nami",
                ordering="1.2.1.1",
                is_organization=True
            )
            StatementColumn.objects.create(
                statement=land_management_3,
                parent=land_info_3,
                title="Tashkilot nami",
                ordering="1.3.1.1",
                is_organization=True
            )
            StatementColumn.objects.create(
                statement=land_management,
                parent=land_info_4,
                title="Tashkilot nami",
                ordering="1.4.1.1",
                is_organization=True
            )
            StatementColumn.objects.create(
                statement=land_management,
                parent=land_info,
                title="Reja",
                ordering="1.1.1.2",
                status_plan=SC.PlanStatus.YILLIK
            )
            StatementColumn.objects.create(
                statement=land_management,
                parent=land_info,
                title="Amalda",
                ordering="1.1.1.3",
            )
            shundan = StatementColumn.objects.create(
                statement=land_management,
                parent=land_info,
                title="Shundan",
                ordering="1.1.1.4",
            )
            StatementColumn.objects.create(
                statement=land_management,
                parent=shundan,
                title="1-chorak",
                ordering="1.1.1.4.1",
            )
            StatementColumn.objects.create(
                statement=land_management,
                parent=shundan,
                title="2-chorak",
                ordering="1.1.1.4.2",
            )
            StatementColumn.objects.create(
                statement=land_management,
                parent=shundan,
                title="3-chorak",
                ordering="1.1.1.4.3",
            )
            StatementColumn.objects.create(
                statement=land_management,
                parent=shundan,
                title="4-chorak",
                ordering="1.1.1.4.4",
            )
            StatementColumn.objects.create(
                statement=land_management,
                parent=land_info,
                title="Foiz",
                ordering="1.1.1.5",
            )
            contract = StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_info_2,
                title="Shartnoma",
                ordering="1.2.1.2"
            )
            StatementColumn.objects.create(
                statement=land_management_2,
                parent=contract,
                title="Sana",
                ordering="1.2.1.2.1"
            )
            info_rent = StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_info_2,
                title="Ijarachi malumotlari",
                ordering="1.2.1.3"
            )
            customer_infos = [
                "Shartnoma sana",
                "JSHSHIR (Yuridik shaxs INN)",
                "To‘liq F.I.SH. (Yuridik shaxs nomi)",
                "Yashash manzili (Yuridik manzil)",
                "Pasport seriyasi va raqami (rahbar)",
                "Telefon raqami / Telegram"
            ]



            StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_info_2,
                title="Ijara yer maydoni joylashgan o‘rmon bo‘limi nomi",
                ordering="1.2.1.4"
            )
            dep_that_of = StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_info_2,
                title="shundan-1",
                ordering="1.2.1.5"
            )
            dep_titles = [
                "Aylanma raqami",
                "Kvartal raqami",
                "Kontur raqami",
                "Videl raqami"
            ]
            for i in range(len(dep_titles)):
                StatementColumn.objects.create(
                    statement=land_management_2,
                    parent=dep_that_of,
                    title=dep_titles[i],
                    ordering=f"1.2.1.5.{i+1}"
                )

            StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_info_2,
                title="Jami ijara yer maydoni (ga)",
                ordering="1.2.1.6"
            )
            types_lands = StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_info_2,
                title="Shundan faoliyat turlari bo‘yicha",
                ordering="1.2.1.7"
            )
            land_types_titles = [
                "O‘rmon barpo qilish",
                "Qishloq xo‘jaligi ekinlarini ekish",
                "Mevali bog‘lar barpo etish",
                "Yong‘oq mevali bog‘lar (pista, bodom, yong‘oq) faoliyati",
                "Ko‘chat yetishtirish faoliyati",
                "Limonariy va issiqxonalar tashkil etish faoliyati",
                "Pichanzorlardan foydalanish (pichan yig‘ishtirish)",
                "Dorivor o‘simliklar yetishtirish faoliyati",
                "Ovchilik faoliyati (ovchilarni qabul qilish punkti)",
                "Boshqa faoliyat turlari",
                "Cho‘l",
                "Tog‘",
                "Vodiy",
                "To‘qay",
                "O‘zlashtirilmagan boshqa yerlar"
            ]
            for i in range(len(land_types_titles)):
                StatementColumn.objects.create(
                    statement=land_management_2,
                    parent=types_lands,
                    title=land_types_titles[i],
                    ordering=f"1.2.1.7.{i+1}"
                )
            types_lands_of = StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_info_2,
                title="Shundan yer turali",
                ordering="1.2.1.8"
            )
            land_types_titles_of = [
                "Cho‘l",
                "Tog‘",
                "Vodiy",
                "To‘qay",
                "O‘zlashtirilmagan boshqa yerlar"
            ]
            for i in range(len(land_types_titles_of)):
                StatementColumn.objects.create(
                    statement=land_management_2,
                    parent=types_lands_of,
                    title=land_types_titles_of[i],
                    ordering=f"1.2.1.8.{i+1}"
                )
            preferred_lands = StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_info_2,
                title="Shundan imtiyozli maydon",
                ordering="1.2.1.9"
            )
            StatementColumn.objects.create(
                statement=land_management_2,
                parent=preferred_lands,
                title="Jami",
                ordering="1.2.1.9.1"
            )
            preferred_lands_of=StatementColumn.objects.create(
                statement=land_management_2,
                parent=preferred_lands,
                title="Shundan",
                ordering="1.2.1.9.2"
            )
            plantation_titles = [
                "Cho‘l o‘simliklari (saxovul, cherkes, qandim, qoraburoq) ekish (ga) (10 yil)",
                "Yong‘oq mevali bog‘lar (pista, bodom, yong‘oq) va tez o‘suvchi daraxtlar (pavlovniya, terak) plantatsiyalari (5 yil) (ga)",
                "Qishloq xo‘jaligi oziq-ovqat ekinlari (dukkakli, moyli, boshoqli ekinlar, sabzavot, poliz) (1 yil) (ga)",
                "Dorivor o‘simliklar plantatsiyalari (3 yil) (ga)"
            ]

            for i in range(len(plantation_titles)):
                StatementColumn.objects.create(
                    statement=land_management_2,
                    parent=preferred_lands_of,
                    title=plantation_titles[i],
                    ordering=f"1.2.1.9.{i+1}"
                )
            preferred_years = StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_info_2,
                title="20_20_yillar",
                ordering="1.2.1.10"
            )
            payment_titles = [
                "Jami hisoblangan",
                "Jami to‘langan",
                "Jami qarzdorlik"
            ]
            for i in range(len(payment_titles)):
                StatementColumn.objects.create(
                    statement=land_management_2,
                    parent=preferred_years,
                    title=payment_titles[i],
                    ordering=f"1.2.1.10.{i+1}"
                )
            StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_info_2,
                title="Yangi yaratilgan ish o‘rinlari soni",
                ordering=f"1.2.1.11"
            )
            StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_info_2,
                title="Kiritiladigan investitsiya qiymati (ming so‘m)",
                ordering=f"1.2.1.12"
            )
            lanf_2_of_that = StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_info_2,
                title="shundan-1",
                ordering=f"1.2.1.12"
            )
            StatementColumn.objects.create(
                statement=land_management_2,
                parent=lanf_2_of_that,
                title="O'z hisobidan",
                ordering=f"1.2.1.12.1"
            )
            year_export =StatementColumn.objects.create(
                statement=land_management_2,
                parent=land_info_2,
                title="20__yildagi eksport",
                ordering=f"1.2.1.13"
            )
            export_titles = [
                "Mahsulot turi",
                "Mahsulot miqdori",
                "Hajmi (ming AQSh dollari)",
                "Sanasi"
            ]
            for i in range(len(export_titles)):
                StatementColumn.objects.create(
                    statement=land_management_2,
                    parent=year_export,
                    title=export_titles[i],
                    ordering=f"1.2.1.13.{i+1}"
                )
            rejected = StatementColumn.objects.create(
                    statement=land_management_2,
                    parent=land_info_2,
                    title="Bekor qilingan",
                    ordering=f"1.2.1.14"
                )
            StatementColumn.objects.create(
                statement=land_management_2,
                parent=rejected,
                title="Sana",
                ordering=f"1.2.1.14.1"
            )
            StatementColumn.objects.create(
                statement=land_management_2,
                parent=rejected,
                title="Asos",
                ordering=f"1.2.1.14.2"
            )
            forest_department_titles = [
                "O‘rmon bo‘limining nomi",
                "O‘rmon bo‘limining identifikatsiya raqami",
                "O‘rmon bo‘limi tashkil etilgan sana",
                "Idoraviy mansubligi",
                "O‘rmon bo‘limining joylashgan joyi",
                "O‘rmon bo‘limi ma’lumotlari hisobga olingan sana",
            ]
            for i in range(1,len(forest_department_titles)):
                StatementColumn.objects.create(
                    statement=land_management_3,
                    parent=land_info_3,
                    title=forest_department_titles[i],
                    ordering=f"1.3.1.{i+1}"
                )
            father_tematik =StatementColumn.objects.create(
                    statement=land_management_3,
                    parent=land_info_3,
                    title ="Tematik qatlam atributiv ma’lumotlari",
                    ordering=f"1.3.1.8"
                )
            forest_quarter_titles = [
                "Kvartalning identifikatsiya raqami",
                "Kvartal raqami",
                "Izoh"
            ]
            for i in range(len(forest_quarter_titles)):
                StatementColumn.objects.create(
                    statement=land_management_3,
                    parent=father_tematik,
                    title=forest_quarter_titles[i],
                    ordering=f"1.3.1.8.{i+1}"
                )
            forest_contour_titles = [
                "Kontur identifikatsiya raqami",
                "Maydoni (ga)",
                "Daraxt nomi",
                "O‘rmonlarni ko‘paytirish usuli",
                "Daraxtlar yoshi bo‘yicha mansubligi",
                "Daraxtlarning o‘rtacha yoshi",
                "O‘rmonlarni tashkil qiluvchi asosiy turlar",
                "O‘rmonlarning holati",
                "Bonitet sinfi",
                "Daraxtlarning zichlik darajasi",
                "O‘rmon turi",
                "Daraxtlar zaxirasi (m³)",
                "Qiymati (so‘m)"
            ]

            for i in range(1,len(forest_contour_titles)):
                StatementColumn.objects.create(
                    statement=land_management_3,
                    parent=land_info_4,
                    title=forest_contour_titles[i],
                    ordering=f"1.4.1.{i+1}"
                )
















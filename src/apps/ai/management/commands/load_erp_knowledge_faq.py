from django.core.management.base import BaseCommand

from apps.ai.models import KnowledgeDocument


DOCUMENTS = [
    {
        "source_key": "faq_individual_general_created_by_whom_v1_uz",
        "title": "Individual umumiy hisobotni foydalanuvchi o'zi yaratadimi",
        "source_type": "rule",
        "content": """
Individual umumiy hisobot foydalanuvchi tomonidan qo'lda yaratilmaydi.

Oddiy hisobotni tashkilot hodimi yaratadi. Individual umumiy hisobot esa tizimning ichki hisoblash logikasi orqali avtomatik shakllanadi yoki yangilanadi.

U odatda oddiy hisobot qabul qilingandan keyin yoki qayta hisoblash jarayonida hosil bo'ladi. Shu sababli foydalanuvchi uni alohida yaratmaydi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 10},
    },
    {
        "source_key": "faq_which_reports_are_auto_created_v1_uz",
        "title": "Qaysi hisobotlar avtomatik yaratiladi",
        "source_type": "rule",
        "content": """
Tizimda barcha hisobotlar foydalanuvchi tomonidan qo'lda yaratilmaydi.

Oddiy hisobot odatda tashkilot hodimi tomonidan yaratiladi. Individual umumiy hisobot, viloyat jami va respublika jami esa tizimning ichki hisoblash logikasi orqali avtomatik yaratiladi yoki yangilanadi.

Bunday umumiy hisobotlar qabul qilingan oddiy hisobotlar asosida shakllanadi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 10},
    },
    {
        "source_key": "faq_who_creates_regular_report_v1_uz",
        "title": "Oddiy hisobotni kim yaratadi",
        "source_type": "rule",
        "content": """
Oddiy hisobotni odatda tashkilot hodimi yaratadi.

U o'ziga tegishli tashkilot, hisobot turi va muddat bo'yicha kerakli formani ochadi. Reja qiymatlari yuklangandan keyin amalda qiymatlarini kiritadi va hisobotni saqlaydi.

Keyin hisobot yuborish va tasdiqlash bosqichlari boshqa mas'ul shaxslar orqali davom etadi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 9},
    },
    {
        "source_key": "faq_who_sends_report_v1_uz",
        "title": "Hisobotni kim yuboradi",
        "source_type": "rule",
        "content": """
Hisobotni odatda tashkilot rahbari yoki vakolatli shaxs yuboradi.

Hisobot avval saqlangan holatda bo'ladi. Yuborish bosqichida u yuborilgan holatga o'tadi va ko'pincha E-IMZO bilan tasdiqlanadi.

Shundan keyin hisobot tekshiruv bosqichiga o'tadi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 9},
    },
    {
        "source_key": "faq_who_accepts_report_v1_uz",
        "title": "Hisobotni kim qabul qiladi",
        "source_type": "rule",
        "content": """
Yuborilgan hisobotni odatda bo'lim boshliq yoki vakolatli tekshiruvchi ko'rib chiqadi.

Agar hisobot to'g'ri bo'lsa, u qabul qilingan holatga o'tkaziladi. Agar xatolik bo'lsa, qaytarilgan holatga tushishi mumkin.

Shu sababli hisobotni yaratish, yuborish va qabul qilish bir xil foydalanuvchi vazifasi emas.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 9},
    },
    {
        "source_key": "faq_what_happens_after_accepted_v1_uz",
        "title": "Hisobot qabul qilinsa keyin nima bo'ladi",
        "source_type": "workflow",
        "content": """
Hisobot qabul qilingandan keyin u yakuniy tasdiqlangan hisobot hisoblanadi.

Shundan so'ng tizimda umumiy hisoblash jarayoni ishga tushishi mumkin. Natijada individual umumiy hisobot, viloyat jami va respublika jami kabi umumiy natijalar yaratiladi yoki yangilanadi.

Faqat qabul qilingan hisobotlar umumiy yig'indilarni hisoblashda qatnashadi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 10},
    },
    {
        "source_key": "faq_what_if_deadline_missing_v1_uz",
        "title": "Muddat bo'lmasa nima bo'ladi",
        "source_type": "rule",
        "content": """
Agar kerakli hisobot turi va tashkilot uchun muddat yaratilmagan bo'lsa, hisobot yaratib bo'lmaydi.

Chunki hisobot yaratish jarayoni muddat mavjudligiga bog'langan. Muddat bo'lmasa foydalanuvchi kerakli formani to'liq ocholmaydi yoki yaratish bosqichidan o'tolmaydi.

Bunday holatda odatda avval muddat yaratish kerak bo'ladi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 10},
    },
    {
        "source_key": "faq_who_creates_deadline_v1_uz",
        "title": "Muddatni kim yaratadi",
        "source_type": "rule",
        "content": """
Muddatni odatda Super Admin yoki yuqori darajadagi mas'ul shaxs yaratadi.

Muddat ma'lum bir hisobot turi va ma'lum tashkilotlar uchun ochiladi. Hisobot yaratishdan oldin muddat mavjud bo'lishi kerak.

Agar muddat yaratilmagan bo'lsa, foydalanuvchi hisobot yaratolmaydi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 10},
    },
    {
        "source_key": "faq_what_if_plan_missing_v1_uz",
        "title": "Reja bo'lmasa nima bo'ladi",
        "source_type": "rule",
        "content": """
Agar reja yaratilmagan bo'lsa, hisobot yaratish jarayoni to'liq ishlamaydi.

Muddat mavjud bo'lsa ham, tashkilot tanlanganda reja qiymatlari chiqmasa, bu odatda o'sha hisobot turi uchun reja yaratilmaganini bildiradi.

Bunday vaziyatda foydalanuvchi tegishli bo'lim boshliq yoki mas'ul shaxsga murojaat qilishi kerak. Rejasiz hisobot yaratib bo'lmaydi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 10},
    },
    {
        "source_key": "faq_difference_saved_sent_accepted_v1_uz",
        "title": "Saqlangan yuborilgan va qabul qilingan holatlar farqi nima",
        "source_type": "rule",
        "content": """
Saqlangan holat hisobot saqlanganini, lekin hali yuborilmaganini bildiradi.

Yuborilgan holat hisobot yuborilganini va tekshiruv bosqichiga o'tganini bildiradi.

Qabul qilingan holat esa hisobot tekshirilib, to'g'ri deb topilganini bildiradi. Aynan qabul qilingan hisobotlar umumiy yig'indilarga kiradi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 10},
    },
    {
        "source_key": "faq_cancelled_report_meaning_v1_uz",
        "title": "Qaytarilgan hisobot degani nima",
        "source_type": "rule",
        "content": """
Qaytarilgan hisobot xatolik yoki kamchilik sababli qaytarilgan hisobotni bildiradi.

Bu holatda hisobot yakuniy tasdiqdan o'tmagan bo'ladi. Odatda foydalanuvchi uni qayta ko'rib chiqishi, tuzatishi yoki kerakli ma'lumotlarni to'ldirishi kerak bo'ladi.

Qaytarilgan hisobot qabul qilingan hisobot kabi umumiy yig'indiga kirmaydi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 9},
    },
    {
        "source_key": "faq_viloyat_jami_created_by_whom_v1_uz",
        "title": "Viloyat jamini kim yaratadi",
        "source_type": "rule",
        "content": """
Viloyat jamini foydalanuvchi qo'lda yaratmaydi.

U qabul qilingan tashkilot hisobotlari asosida tizimning umumiy hisoblash logikasi orqali avtomatik yaratiladi yoki yangilanadi.

Viloyat jami bu ma'lum bir viloyatdagi tashkilotlar natijalarining umumiy yig'indisidir.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 10},
    },
    {
        "source_key": "faq_republic_jami_created_by_whom_v1_uz",
        "title": "Respublika jamini kim yaratadi",
        "source_type": "rule",
        "content": """
Respublika jamini oddiy foydalanuvchi qo'lda yaratmaydi.

U tizim tomonidan qabul qilingan hisobotlar va umumiy natijalar asosida avtomatik shakllantiriladi yoki yangilanadi.

Bu mamlakat bo'yicha eng yuqori darajadagi umumiy natijani ifodalaydi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 10},
    },
    {
        "source_key": "faq_plant_report_who_fills_v1_uz",
        "title": "O‘simlik asosidagi hisobotni kim va qanday to'ldiradi",
        "source_type": "workflow",
        "content": """
O'simlik asosidagi hisobotni odatda tashkilotdagi foydalanuvchi to'ldiradi, lekin u oddiy hisobotdan farq qiladi.

Bunday hisobotlarda foydalanuvchi bitta umumiy qiymat emas, balki har bir o'simlik bo'yicha alohida qiymat kiritadi. Bu qiymatlar ichki satrlar orqali saqlanadi.

Keyin tizim shu o'simliklar qiymatlari asosida ota qatorlar va umumiy natijalarni hisoblaydi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 9},
    },
    {
        "source_key": "faq_what_is_statement_in_simple_words_v1_uz",
        "title": "Hisobot bo'limi oddiy tilda nima degani",
        "source_type": "model_doc",
        "content": """
Hisobot bo'limi degani tizimdagi alohida hisobot turi yoki alohida yo'nalish degani.

Oddiy foydalanuvchi buni ko'pincha alohida forma, bo'lim yoki hisobot yo'nalishi sifatida ko'radi. Masalan Daromad, Urug' xarakati yoki Ko'chat va Nihol alohida hisobot bo'limlari bo'lishi mumkin.

Shuning uchun bu texnik atama bo'lsa ham, foydalanuvchi uchun bu hisobotning qaysi bo'limi ekanini bildiradi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 8},
    },
    {
        "source_key": "faq_what_is_plan_in_simple_words_v1_uz",
        "title": "Reja oddiy tilda nima degani",
        "source_type": "model_doc",
        "content": """
Reja bu oldindan belgilangan ko'rsatkich yoki oldindan kiritilgan qiymat degani.

Foydalanuvchi hisobot yaratganda tizim ko'pincha shu reja qiymatlarini avtomatik yuklaydi. Keyin foydalanuvchi bajarilgan natijalarni kiritadi.

Agar reja bo'lmasa, hisobot yaratish jarayoni to'liq ishlamaydi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 8},
    },
    {
        "source_key": "faq_what_is_deadline_in_simple_words_v1_uz",
        "title": "Muddat oddiy tilda nima degani",
        "source_type": "model_doc",
        "content": """
Muddat bu hisobot topshirish uchun belgilangan vaqt degani.

Hisobot yaratish uchun avval muddat bo'lishi kerak. Tizimda muddat ma'lum hisobot turi va ma'lum tashkilotlarga bog'lab yaratiladi.

Foydalanuvchi uchun muddat bu hisobot qachon va qaysi davr bo'yicha topshirilishini bildiradi.
""",
        "metadata": {"lang": "uz", "faq": True, "priority": 8},
    },
]


class Command(BaseCommand):
    help = "Load Uzbek ERP FAQ knowledge documents into KnowledgeDocument"

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for item in DOCUMENTS:
            _, is_created = KnowledgeDocument.objects.update_or_create(
                source_key=item["source_key"],
                defaults={
                    "title": item["title"],
                    "source_type": item["source_type"],
                    "content": item["content"].strip(),
                    "metadata": item.get("metadata", {}),
                    "is_active": True,
                },
            )

            if is_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Uzbek FAQ knowledge loaded successfully. Created: {created}, Updated: {updated}"
            )
        )
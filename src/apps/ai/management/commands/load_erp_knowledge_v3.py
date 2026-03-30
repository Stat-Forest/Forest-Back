from django.core.management.base import BaseCommand

from apps.ai.models import KnowledgeDocument


DOCUMENTS = [
    {
        "source_key": "auth_and_login_v1",
        "title": "Tizimga kirish va autentifikatsiya qanday ishlaydi",
        "source_type": "workflow",
        "content": """
Stat-Urmon ERP tizimida foydalanuvchi tizimga bir nechta usul orqali kirishi mumkin. Asosiy kirish mexanizmlaridan biri oddiy login-parol orqali autentifikatsiya bo'lsa, ayrim bosqichlarda E-IMZO orqali tasdiqlash ham ishlatiladi.

Oddiy autentifikatsiyada foydalanuvchi o'z login ma'lumotlari orqali tizimga kiradi va o'z roliga mos interfeys hamda vakolatlarni oladi. Masalan, tashkilot hodimi hisobot yaratish oynalarini ko'radi, bo'lim boshliq esa tekshirish va tasdiqlash bilan bog'liq imkoniyatlarga ega bo'ladi.

E-IMZO tizimga oddiy kirishning o'rnini to'liq bosmaydi, balki ayrim muhim amallarni rasmiy tasdiqlash uchun ishlatiladi. Ayniqsa hisobotni yuborish yoki rahbar darajasidagi tasdiqlash kabi jarayonlarda E-IMZO ishonchli identifikatsiya va tasdiqlash vositasi bo'lib xizmat qiladi.

Shu sababli autentifikatsiya tizimida foydalanuvchining roli, tashkiloti va qaysi amalni bajarayotgani juda muhim hisoblanadi.
""",
        "metadata": {"lang": "uz", "priority": 9},
    },
    {
        "source_key": "eimzo_usage_v1",
        "title": "E-IMZO qaysi jarayonlarda ishlatiladi",
        "source_type": "rule",
        "content": """
E-IMZO tizimdagi muhim jarayonlarni tasdiqlash uchun ishlatiladi. U oddiy ma'lumot kiritishdan ko'ra rasmiyroq bosqichlarda qo'llanadi.

Ko'pincha tashkilot rahbari hisobotni yuborish jarayonida E-IMZO bilan tasdiqlaydi. Bu reportning oddiy saqlangan holatdan rasmiy yuborilgan holatga o'tishida muhim rol o'ynaydi.

E-IMZO ishlatiladigan bosqichlarda tizim faqat kimdir tugmani bosganini emas, balki aynan qaysi vakolatli shaxs bu amalni bajarganini ham qayd etadi. Shu sababli sent_by, sent_by_org yoki sent_by_role kabi maydonlar jarayon auditida ahamiyatli bo'ladi.

Agar E-IMZO bilan yuborish jarayoni muvaffaqiyatli yakunlansa, report sent statusiga o'tadi va keyingi tekshiruv bosqichiga yuboriladi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "report_sending_workflow_v1",
        "title": "Hisobotni yuborish bosqichi qanday ishlaydi",
        "source_type": "workflow",
        "content": """
Hisobotni yuborish report hayot siklidagi eng muhim bosqichlardan biridir. Odatda foydalanuvchi avval reportni to'ldiradi va saved holatda saqlaydi. Saved holat report hali yakuniy tekshiruvga yuborilmaganini bildiradi.

Tashkilot rahbari yoki vakolatli shaxs reportni ko'rib chiqib, kerakli ma'lumotlar to'liq ekaniga ishonch hosil qilgandan keyin uni yuboradi. Yuborish jarayoni E-IMZO bilan tasdiqlanishi mumkin.

Report yuborilgach, u sent statusiga o'tadi. Shu vaqtda report tekshiruvchi yoki bo'lim boshliq ko'rishi mumkin bo'lgan navbatga tushadi. sent_at maydoni yuborilgan vaqtni, sent_by esa kim yuborganini qayd etadi.

Shu tariqa saved report ichki ishchi holat bo'lsa, sent report allaqachon yuqori bosqichdagi tekshiruvga yuborilgan hisobot hisoblanadi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "report_accept_cancel_workflow_v1",
        "title": "Hisobotni accepted yoki cancelled qilish jarayoni",
        "source_type": "workflow",
        "content": """
Sent holatga o'tgan hisobot keyingi bosqichda bo'lim boshliq yoki vakolatli tekshiruvchi tomonidan ko'rib chiqiladi. Bu bosqichda report tarkibi, to'ldirilgan qiymatlar va biznes qoidalarga mosligi tekshiriladi.

Agar report to'g'ri bo'lsa, u accepted statusiga o'tkaziladi. Accepted bo'lishi report yakuniy tasdiqdan o'tganini bildiradi va aynan shu bosqichdan keyin report aggregation jarayonlariga ta'sir qila boshlaydi.

Agar reportda xatolik bo'lsa, u cancelled statusiga qaytarilishi mumkin. Cancel qilingan report foydalanuvchi tomonidan qayta ko'rib chiqilishi yoki tuzatilishi kerak bo'ladi. cancelled_at maydoni qachon qaytarilganini qayd etadi.

Demak sent faqat yuborilganini bildiradi, accepted esa tasdiqlanganini, cancelled esa xatolik sabab qaytarilganini anglatadi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "daromad_statement_v1",
        "title": "Daromad statement qanday ishlaydi",
        "source_type": "rule",
        "content": """
Daromad statement tizimdagi murakkab hisobot turlaridan biri bo'lib, unda vaqt bo'yicha kesimlar, masalan choraklar yoki oylar bilan ishlash uchrashi mumkin. Bu statementda foydalanuvchi barcha ustunlarni to'ldirmaydi, ayrim ustunlar tizim tomonidan hisoblanadi.

Daromad hisobotida ba'zi qiymatlar user input bo'ladi, ba'zi qiymatlar esa oldingi ustunlar, chorak natijalari yoki umumiy summalar asosida avtomatik hosil qilinadi. Shu sababli Daromad statementda StatementColumn tarkibi va orderinglari juda muhim rol o'ynaydi.

Daromad hisobotida qaysi ustun foydalanuvchi tomonidan to'ldirilishi, qaysi biri tizim tomonidan hisoblanishi oldindan belgilangan bo'ladi. Tizim aynan shu qoidalarga qarab jami, qoldiq yoki boshqa natijalarni chiqaradi.

Bu statement bo'yicha savollarda ko'pincha reja va amalda qiymatlari, davriy natijalar va hisoblangan ustunlar orasidagi farq tushuntirilishi kerak bo'ladi.
""",
        "metadata": {"lang": "uz", "priority": 9},
    },
    {
        "source_key": "jamgarma_statement_v1",
        "title": "Jamg‘arma statement qanday ishlaydi",
        "source_type": "rule",
        "content": """
Jamg'arma statementda ko'pincha tushum, to'lanishi kerak bo'lgan summa, to'langan summa va qoldiq kabi qiymatlar bilan ishlanadi. Bu statementda ham barcha ustunlar foydalanuvchi tomonidan kiritilmaydi.

Ayrim ustunlar to'g'ridan-to'g'ri user input bo'lsa, ayrimlari oldingi ustunlar asosida avtomatik hisoblanadi. Masalan qoldiq ko'pincha to'lanishi kerak va to'langan qiymatlar orasidagi farq sifatida hosil bo'ladi.

Jamg'arma statementdagi yakuniy jami bloklari odatda pastki turdagi daromad yoki tushum satrlarining yig'indisiga asoslanadi. Shu sababli bu statementda alohida satrlar va final jamilar o'rtasidagi bog'liqlik muhim.

Bunday hisobotlarda noto'g'ri qatorga qiymat kiritish yoki tizim hisoblaydigan ustunni qo'lda to'ldirish xatolarga olib kelishi mumkin.
""",
        "metadata": {"lang": "uz", "priority": 9},
    },
    {
        "source_key": "urug_xarakati_statement_v1",
        "title": "Urug‘ xarakati statement qanday ishlaydi",
        "source_type": "rule",
        "content": """
Urug' xarakati statement urug'lar bilan bog'liq reja va amaldagi harakatlarni ifodalaydi. Bu statementda reja, amalda va ularga bog'liq avtomatik hisoblanadigan ustunlar bo'lishi mumkin.

Ba'zi urug' xarakati hisobotlarida global plan logikasi muhim bo'ladi. Ya'ni reja qiymati alohida manbadan olinadi, foiz esa to'g'ridan-to'g'ri yig'ilmaydi, balki reja va amalda qiymatlari asosida qayta hisoblanadi.

Shu sababli urug' xarakati bo'yicha savollarda foydalanuvchiga foizning oddiy yig'indi emasligi, balki qayta hisoblangan natija bo'lishi tushuntirilishi kerak. Reja va amaldagi farq ham shu statement uchun muhim tushunchalardan biridir.

Accepted hisobotlardan keyin urug' xarakati bo'yicha viloyat va respublika umumiy ko'rsatkichlari ham avtomatik shakllanishi mumkin.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "foiz_and_calculated_columns_v1",
        "title": "Foiz, qoldiq va boshqa hisoblangan ustunlar qanday ishlaydi",
        "source_type": "rule",
        "content": """
Tizimdagi barcha ustunlar foydalanuvchi tomonidan qo'lda to'ldirilmaydi. Ayrim ustunlar hisoblangan ustunlar hisoblanadi va ular boshqa qiymatlar asosida hosil bo'ladi.

Masalan foiz ustuni ko'pincha reja va amalda qiymatlari orasidagi nisbat asosida hisoblanadi. Bunday ustunni oddiy yig'ish yoki qo'lda kiritish noto'g'ri bo'lishi mumkin.

Qoldiq ham ko'pincha ikki ustun orasidagi farq sifatida chiqadi. Jami esa bir nechta qator yoki ustun qiymatlarining yig'indisi sifatida shakllanadi.

Shu sababli foydalanuvchi qaysi ustunlarni to'ldirishi kerakligi va qaysi ustunlar tizim tomonidan hisoblanishini aniq bilishi kerak. Hisoblangan ustunlar ko'pincha is_user_input=False kabi belgilarga asoslanadi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "seedlings_and_plant_reports_v1",
        "title": "Ko‘chat va Nihol hisobotlari qanday ishlaydi",
        "source_type": "workflow",
        "content": """
Ko'chat va Nihol hisobotlari plant-based reportlar turiga kiradi. Bu hisobotlarda foydalanuvchi umumiy bitta qiymat kiritib qo'ymaydi, balki o'simliklar bo'yicha alohida qiymatlar bilan ishlaydi.

Plant modeli oldindan daraxtsimon ko'rinishda yaratilgan bo'ladi. Ota kategoriya va uning ichidagi child o'simliklar mavjud bo'ladi. Foydalanuvchi odatda child plantlar bo'yicha qiymat kiritadi.

Bu qiymatlar ReportItemInner orqali saqlanadi. Keyinchalik parent o'simliklar va umumiy yakuniy satrlar child qiymatlar yig'indisi asosida hisoblanadi. Shu sababli Ko'chat va Nihol hisobotlarida yig'indilar ko'pincha plantlar kesimidan hosil bo'ladi.

Bu turdagi hisobotlarda faqat umumiy natijani ko'rish yetarli emas. Ichki plantlar bo'yicha ham ma'lumot saqlanadi va hisob-kitoblar aynan shu ichki qiymatlar asosida quriladi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "plant_report_update_rules_v1",
        "title": "Plant-based hisobotlarni yangilash qoidalari",
        "source_type": "rule",
        "content": """
Plant-based hisobotni yangilash oddiy reportni yangilashdan farq qiladi. Bunda foydalanuvchi har bir StatementColumn uchun plantlar bo'yicha inner qiymatlarni yuboradi.

Tizim update vaqtida faqat foydalanuvchi to'ldirishi mumkin bo'lgan ustunlarni qabul qiladi. Agar calculated ustun yoki is_user_input=False bo'lgan ustun uchun qiymat yuborilsa, bu validatsiya xatosiga olib kelishi mumkin.

Har bir report item ichida mavjud plant qiymatlari yangilanadi, yangi inner lar yaratiladi va kerak bo'lsa eski inner lar o'chiriladi. So'ngra tizim calculated ustunlarni qayta hisoblaydi va individual umumiy natijalarni yangilaydi.

Shu sababli plant-based hisobotni update qilishda inner qiymatlar, plant identifikatori va qaysi statement_column yangilanayotgani juda muhim.
""",
        "metadata": {"lang": "uz", "priority": 9},
    },
    {
        "source_key": "regional_and_republic_reports_v1",
        "title": "Viloyat jami va Respublika jami amalda qanday shakllanadi",
        "source_type": "workflow",
        "content": """
Viloyat jami va Respublika jami oddiy foydalanuvchi tomonidan qo'lda yaratilmaydi. Ular accepted bo'lgan hisobotlar asosida service logikasi orqali avtomatik shakllanadi.

Viloyat jami ma'lum bir viloyatdagi accepted tashkilot hisobotlarining umumiy yig'indisidir. Bunday report odatda is_general=True flagi bilan ajratiladi. Unda faqat shu hududga tegishli reportlar hisobga olinadi.

Respublika jami esa undan ham yuqori darajadagi umumlashma bo'lib, butun tizim bo'yicha yakuniy natijani ifodalaydi. Bunday report odatda is_republic=True bilan belgilanadi.

Bu reportlar foydalanuvchining oddiy CRUD jarayonining qismi emas. Ular business logika va aggregation service natijasida hosil bo'ladi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "individual_general_reports_v1",
        "title": "Individual umumiy hisobot nima",
        "source_type": "rule",
        "content": """
Individual umumiy hisobot oddiy report bilan bog'liq ichki umumlashtirilgan natija hisoblanadi. U ko'pincha is_individual_general=True flagi bilan ajratiladi.

Bunday report tashkilot hodimi yaratgan oddiy reportdan keyin, ayniqsa accepted yoki qayta hisoblash jarayonlarida hosil bo'lishi mumkin. Unda report ichidagi ayrim yig'indi qiymatlar va umumiy natijalar saqlanadi.

Plant-based hisobotlarda individual umumiy report yanada muhim bo'lishi mumkin, chunki ichki plantlar bo'yicha kiritilgan qiymatlarni umumlashtirish zarur bo'ladi.

Individual umumiy report oddiy foydalanuvchi to'ldiradigan asosiy report bilan bir xil narsa emas. U tizimning ichki hisoblash va umumlashtirish bosqichi hisoblanadi.
""",
        "metadata": {"lang": "uz", "priority": 8},
    },
    {
        "source_key": "report_api_payload_logic_v1",
        "title": "Report create va update payload logikasi qanday",
        "source_type": "model_doc",
        "content": """
Oddiy report create yoki update payloadida odatda deadline va report_items yuboriladi. Har bir report_item ma'lum bir statement_column ga tegishli bo'ladi.

Oddiy reportlarda report_item ichida value yoki oddiy qiymat bilan ishlanadi. Plant-based reportlarda esa report_item ichida inners ro'yxati bo'ladi va u yerda har bir inner alohida plant hamda value bilan yuboriladi.

Demak plant-based report payloadi oddiy report payloadidan murakkabroq. Chunki unda faqat bitta ustun qiymati emas, balki shu ustun ichidagi plantlar kesimida qiymatlar ham keladi.

Create va update vaqtida tizim qaysi ustun calculated, qaysi ustun user input ekanini ham tekshiradi. Shu sababli payload tuzilmasi statement turiga qarab farq qilishi mumkin.
""",
        "metadata": {"lang": "uz", "priority": 9},
    },
]


class Command(BaseCommand):
    help = "Load advanced ERP knowledge documents into KnowledgeDocument"

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for item in DOCUMENTS:
            obj, is_created = KnowledgeDocument.objects.update_or_create(
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
                f"Advanced knowledge loaded successfully. Created: {created}, Updated: {updated}"
            )
        )
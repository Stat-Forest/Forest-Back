from django.core.management.base import BaseCommand

from apps.ai.models import KnowledgeDocument


DOCUMENTS = [
    {
        "source_key": "erp_roles_and_permissions_v1",
        "title": "ERP tizimida foydalanuvchi rollari va vakolatlari",
        "source_type": "rule",
        "content": """
Stat-Urmon ERP tizimida foydalanuvchilar bir nechta rollarga bo'linadi va har bir rolning o'z vazifasi bor.

Tashkilot hodimi odatda oddiy hisobotni yaratadi, ko'radi, tahrir qiladi va o'z tashkilotiga tegishli ma'lumotlar bilan ishlaydi. Bu foydalanuvchi asosan report yaratish bosqichida faol qatnashadi.

Tashkilot rahbari tayyorlangan hisobotni jo'natish jarayonida qatnashadi. Hisobot jo'natish yoki qaytarish E-IMZO bilan tasdiqlanishi mumkin. Rahbar reportni tizimdagi keyingi bosqichga yuboradi.

Bo'lim boshliq o'ziga biriktirilgan statementlar bo'yicha hisobotlarni ko'radi. U hisobotni tekshiradi va to'g'ri bo'lsa accepted holatiga o'tkazadi, xato bo'lsa cancelled holatiga qaytaradi. Rejalarni yaratish ham ko'pincha shu rol bilan bog'liq bo'ladi.

Super Admin tizimdagi yuqori darajadagi boshqaruv rolidir. U deadline yaratadi, umumiy sozlamalarni boshqaradi va tizimdagi ko'p obyektlarga to'liq kirish huquqiga ega bo'ladi.

Shunday qilib, oddiy report yaratish, uni jo'natish, tekshirish va tasdiqlash turli rollar o'rtasida bosqichma-bosqich amalga oshiriladi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "organization_definition_v1",
        "title": "Tashkilot nima va u tizimda qanday ishlatiladi",
        "source_type": "model_doc",
        "content": """
Organization modeli tizimdagi tashkilotlarni ifodalaydi. Masalan, Andijon DUX yoki boshqa hududiy tashkilotlar Organization sifatida saqlanadi.

Foydalanuvchilar odatda ma'lum bir tashkilotga biriktiriladi. Hisobot yaratish, deadline tanlash, reja yuklash va umumiy natijalarni hisoblash jarayonlari shu tashkilot bilan bog'liq bo'ladi.

Deadline yaratilganda u ma'lum statement va ma'lum organizationlar bilan bog'lanadi. Report ham aynan organization, statement va deadline asosida yaratiladi.

Viloyat darajasidagi umumiy hisobotlar tashkilotlar hisobotlarining yig'indisiga asoslanadi. Shu sababli organization tizimdagi eng muhim bog'lovchi obyektlardan biridir.
""",
        "metadata": {"lang": "uz", "priority": 8},
    },
    {
        "source_key": "statement_definition_v1",
        "title": "Statement nima va u nimani bildiradi",
        "source_type": "model_doc",
        "content": """
Statement tizimdagi hisobot bo'limi yoki hisobot formasi hisoblanadi. Masalan, Urug' xarakati Reja, Xodimlar hisobi, O'rmon barpo qilish kabi yo'nalishlar statement bo'lishi mumkin.

Statement reportning qaysi turga tegishli ekanini bildiradi. Har bir report ma'lum bir statement uchun yaratiladi.

Statementlarda parent-child tuzilma bo'lishi mumkin. Bu yirik bo'limlar ichida kichik yo'nalishlar va ichki hisobot shakllarini ifodalash uchun kerak bo'ladi.

Statement period bilan ham bog'liq bo'ladi. Masalan, kunlik, haftalik, oylik, choraklik yoki yillik logika aynan statement va deadline bilan birga ishlaydi.
""",
        "metadata": {"lang": "uz", "priority": 9},
    },
    {
        "source_key": "statement_column_definition_v1",
        "title": "StatementColumn nima va jadval qanday quriladi",
        "source_type": "model_doc",
        "content": """
StatementColumn bu hisobot formasining ustunlari, satrlari va ichki daraxtsimon qismlarini ifodalaydigan modeldir. Tizimdagi jadval aynan StatementColumn lar asosida quriladi.

Hisobot formasida ko'rinadigan qatorlar, ichki bo'limlar, 1-chorak, amalda, reja, foiz, jami yoki boshqa tarkibiy qismlar StatementColumn bo'lishi mumkin.

StatementColumn lar parent-child ko'rinishida joylashishi mumkin. Shu sababli bir statement ichida murakkab ko'p darajali jadval shakllantiriladi.

Ba'zi StatementColumn lar foydalanuvchi tomonidan to'ldiriladi, ba'zilari esa tizim tomonidan hisoblanadi. is_organization, status_plan va is_user_input kabi belgilar hisobotning qanday ishlashiga ta'sir qiladi.

Demak, hisobotdagi jadval dizayni, qaysi qator user input bo'lishi va qaysi qator avtomatik hisoblanishi StatementColumn orqali boshqariladi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "deadline_definition_v1",
        "title": "Deadline nima va qachon yaratiladi",
        "source_type": "workflow",
        "content": """
Deadline bu hisobot topshirish muddati va report yaratishdan oldingi majburiy bosqichdir. Tizimda report yaratish uchun avval deadline mavjud bo'lishi kerak.

Super Admin ma'lum statement va ma'lum organizationlar uchun deadline yaratadi. Deadline statementning periodiga mos ravishda yaratiladi.

Deadline submit_at maydoni orqali saqlanadi. U kunlik, haftalik, oylik, choraklik yoki yillik ko'rinishda bo'lishi mumkin. deadline_at esa oxirgi sana yoki topshirish muddatini bildiradi.

Agar kerakli statement va organization uchun deadline yaratilmagan bo'lsa, foydalanuvchi hisobot yaratolmaydi.

Shuning uchun deadline report jarayonining boshlanish nuqtasi hisoblanadi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "plan_definition_v1",
        "title": "Plan va PlanItem qanday ishlaydi",
        "source_type": "workflow",
        "content": """
Plan bu oldindan belgilangan reja ma'lumotlarini saqlovchi modeldir. U organization, statement, year va ba'zi holatlarda season bilan bog'lanadi.

PlanItem esa plan ichidagi konkret ustun qiymatlarini saqlaydi. Har bir PlanItem bitta StatementColumn ga tegishli bo'ladi va reja qiymati plan_value maydonida saqlanadi.

Rejalar odatda bo'lim boshliq tomonidan yaratiladi. Report yaratish jarayonida foydalanuvchi organization va deadline tanlaganda reja qiymatlari avtomatik yuklanadi.

Agar deadline mavjud bo'lsa-yu, organization tanlanganda reja qiymatlari kelmasa, bu odatda o'sha statement uchun plan yaratilmaganini bildiradi. Bunday vaziyatda foydalanuvchi tegishli bo'lim boshliq bilan bog'lanishi kerak.

Hisobot yaratish uchun deadline va plan ikkalasi ham zarur. Rejasiz report yaratib bo'lmaydi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "report_creation_workflow_v1",
        "title": "Hisobot yaratish jarayoni",
        "source_type": "workflow",
        "content": """
Hisobot yaratish jarayoni bir necha bosqichdan iborat.

Avval foydalanuvchi o'ziga tegishli organization va kerakli statement uchun mavjud deadline ni tanlaydi. Keyin organization tanlanganda, shu reportga tegishli reja qiymatlari avtomatik yuklanadi.

Foydalanuvchi reja qiymatlarini ko'rgandan keyin kerakli StatementColumn lar bo'yicha ma'lumotlarni kiritadi. Ayrim ustunlar user input bo'ladi, ayrimlari esa tizim tomonidan avtomatik hisoblanadi.

Agar deadline yoki plan bo'lmasa, hisobot yaratib bo'lmaydi. Tizim bu holatda report create jarayonini to'xtatadi yoki kerakli qiymatlarni yuklay olmaydi.

Bitta period ichida bir xil organization, statement, deadline va report_season kombinatsiyasi uchun ikkita bir xil oddiy report yaratib bo'lmaydi. Bu unique constraint orqali himoyalangan.

Natijada report yaratish uchun deadline, plan va to'g'ri period bo'yicha yagona report mavjudligi tekshiriladi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "report_statuses_v1",
        "title": "Hisobot statuslari va ularning ma'nosi",
        "source_type": "rule",
        "content": """
Report tizimda bir nechta status bosqichlaridan o'tadi.

saved status report saqlanganini bildiradi. Bu holatda hisobot hali keyingi bosqichga yuborilmagan bo'ladi.

sent status hisobot yuborilganini bildiradi. Odatda tashkilot rahbari bu bosqichda hisobotni E-IMZO orqali tasdiqlab jo'natadi.

accepted status hisobot tekshirilib, to'g'ri deb topilganini bildiradi. Bo'lim boshliq accepted holatiga o'tkazishi mumkin.

cancelled status hisobot xato yoki kamchilik sababli qaytarilganini bildiradi. cancelled_at, sent_at va accepted_at kabi maydonlar jarayon qachon sodir bo'lganini saqlaydi. sent_by, sent_by_org va sent_by_role esa kim tomonidan yuborilganini ko'rsatadi.

Faqat accepted bo'lgan hisobotlar keyingi umumiy yig'indi va agregatsiya jarayonlarida qatnashadi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "report_flags_v1",
        "title": "Report flaglari: is_report, is_individual_general, is_general, is_republic",
        "source_type": "rule",
        "content": """
Report modelida bir nechta muhim flaglar mavjud bo'lib, ular hisobot turini ajratadi.

is_report=True bo'lsa, bu odatda tashkilot hodimi yaratgan oddiy report hisoblanadi. Oddiy foydalanuvchi asosan shunday report yaratadi.

is_individual_general=True bo'lsa, bu oddiy report bilan birga yaratiladigan individual umumiy hisobotni bildiradi. Unda tegishli report qiymatlarining yig'indilari saqlanishi mumkin.

is_general=True bo'lsa, bu viloyat darajasidagi umumiy hisobot hisoblanadi. U accepted bo'lgan tashkilot hisobotlari yig'indisiga asoslanadi.

is_republic=True bo'lsa, bu respublika darajasidagi umumiy hisobot bo'ladi. U viloyatlar yoki accepted hisobotlar yig'indisining yuqori darajadagi natijasini ifodalaydi.

Shu flaglar sababli tizimda oddiy report, individual general, viloyat general va respublika general bir-biridan aniq ajratiladi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "aggregation_workflow_v1",
        "title": "Accepted hisobotdan keyin aggregation qanday ishlaydi",
        "source_type": "workflow",
        "content": """
Oddiy foydalanuvchi yaratgan report accepted bo'lganidan keyin tizimda avtomatik aggregation jarayoni ishga tushadi.

Avvalo shu reportga tegishli individual umumiy report yaratilishi yoki yangilanishi mumkin. Bu report o'sha report ichidagi yig'indi natijalarni saqlaydi.

Shundan keyin viloyat darajasidagi umumiy report hisoblanadi. is_general=True bo'lgan report o'sha organization joylashgan viloyat bo'yicha accepted hisobotlar qiymatlarining yig'indisini oladi.

Parallel ravishda respublika darajasidagi umumiy report ham yaratiladi yoki yangilanadi. is_republic=True bo'lgan report mamlakat miqyosidagi umumiy natijani ifodalaydi.

Demak accepted bo'lgan oddiy report faqat o'zi bilan tugamaydi. U individual, viloyat va respublika darajasidagi umumiy ko'rsatkichlarni ham shakllantirishga ta'sir qiladi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "report_item_and_inner_v1",
        "title": "ReportItem va ReportItemInner nima",
        "source_type": "model_doc",
        "content": """
ReportItem report ichidagi konkret StatementColumn ga tegishli qiymatni saqlovchi model hisoblanadi. Har bir ReportItem bitta report va bitta statement_column bilan bog'langan bo'ladi.

Oddiy reportlarda asosiy ustun qiymatlari aynan ReportItem orqali saqlanadi. Bu model report ichidagi jadval qatorlari bilan ishlash uchun asosiy bo'g'inlardan biridir.

ReportItemInner esa ReportItem ichidagi batafsil qiymatlarni saqlaydi. U ko'pincha plant bo'yicha yoki ayrim hollarda boshqa ichki bo'linmalar bo'yicha qiymatlarni saqlashda ishlatiladi.

Murakkab reportlarda, ayniqsa plant-based reportlarda, bitta ustun uchun bir nechta ichki qiymat bo'lishi mumkin. Bunday holatda umumiy qiymat ReportItem darajasida, ichki elementlar esa ReportItemInner darajasida ifodalanadi.

Shunday qilib, ReportItem asosiy qator qiymatini, ReportItemInner esa shu qatorning ichki kesimidagi qiymatlarni saqlaydi.
""",
        "metadata": {"lang": "uz", "priority": 9},
    },
    {
        "source_key": "plant_based_reports_v1",
        "title": "Plant asosidagi hisobotlar qanday ishlaydi",
        "source_type": "workflow",
        "content": """
Tizimda ikki xil asosiy report oqimi mavjud: oddiy report va plant-based report.

Plant-based reportlarda qo'shimcha ravishda Plant modeli ishlatiladi. Har bir statement o'ziga tegishli o'simliklar ro'yxatiga ega bo'lishi mumkin. Plant modeli parent-child ko'rinishida daraxtsimon tuzilmani ham saqlaydi.

Bunday hisobotlarda foydalanuvchi faqat umumiy qiymat emas, balki har bir o'simlik bo'yicha alohida qiymat kiritadi. Shu qiymatlar odatda ReportItemInner orqali saqlanadi.

Plant parent va child lar bir statement doirasida bo'lishi kerak. Plant o'zi o'ziga parent bo'la olmaydi. Bu validatsiya bilan nazorat qilinadi.

Plant-based reportlarda umumiy natija ko'pincha alohida kiritilgan plant qiymatlarining yig'indisi asosida shakllanadi. Shu sababli bu turdagi reportlar oddiy reportlarga qaraganda murakkabroq hisoblanadi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
    {
        "source_key": "report_constraints_v1",
        "title": "Hisobot yaratishdagi asosiy cheklovlar",
        "source_type": "rule",
        "content": """
Hisobot yaratishda bir nechta muhim biznes cheklovlari mavjud.

Birinchidan, report yaratish uchun deadline bo'lishi shart. Ikkinchidan, shu statement va organization uchun plan yaratilgan bo'lishi kerak. Deadline bo'lsa-yu, reja bo'lmasa, report to'liq yaratilmaydi yoki kerakli qiymatlar kelmaydi.

Bitta periodda bir xil organization, statement, deadline va report_season kombinatsiyasi bo'yicha ikkita bir xil oddiy report yaratishga ruxsat berilmaydi. Bu duplicate reportlarning oldini oladi.

Faqat oddiy reportni tashkilot hodimi yaratadi. Individual general, viloyat general va respublika general kabi boshqa reportlarni service logikasi avtomatik shakllantiradi.

Faqat accepted hisobotlar umumiy yig'indilar va keyingi agregatsiya jarayoniga kiradi. Saved yoki sent bo'lgan hisobotlar hali yakuniy umumiy natijalarga qo'shilmaydi.
""",
        "metadata": {"lang": "uz", "priority": 10},
    },
]


class Command(BaseCommand):
    help = "Load structured ERP knowledge documents into KnowledgeDocument"

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
                f"Knowledge loaded successfully. Created: {created}, Updated: {updated}"
            )
        )
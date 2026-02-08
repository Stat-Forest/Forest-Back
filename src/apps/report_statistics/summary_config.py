"""
SUMMARY_CONFIG - Login statistikasi uchun konfiguratsiya

MUHIM ESLATMALAR:
1. Statement nomlari database dagi name_uz qiymatlari bilan ANIQ mos kelishi kerak
2. Loglardan olingan to'g'ri nomlar:
   - "Dorivor yetishtirish" ✅
   - "O'rmon barpo qilish bo'limi" ✅
   - "Ko'chatxona va Niholxona Jami" ✅
   - "Tut Ko'chat va Tut Nihol" ✅

3. Quyidagi 2 ta statement nomi database da yo'q - ularni topish kerak:
   - "O'rmon bilan qoplangan yerlar" ❌
   - "Yer o'zlashtirish" ❌ (Lekin document 3 da bu nom bilan report mavjud!)

TAXMIN: Document 3 da "statement_name": "Yer o'zlashtirish" ko'rinib turibdi,
demak bu statement database da mavjud, lekin name yoki name_uz boshqacha bo'lishi mumkin.
"""

SUMMARY_CONFIG = [
    {
        "column_name": "O'rmon bilan qoplangan yer maydonlari",
        "unit": "gektar",
        # ESLATMA: Bu statement nomi database da yo'q - tekshirish kerak
        # Ehtimol "Покрытые лесом земли" yoki boshqa nom bilan saqlangandir
        "statement_name": "O'rmon bilan qoplangan yerlar",
        "period": "yearly",
        "plan": None,
        "actual": {
            "column_id": "5529a809-75d8-4ba9-aeb6-7f52dace489e",
        },
    },
    {
        "column_name": "O'rmon yerlarini o'zlashtirib, foydalanishga kiritish",
        "unit": "gektar",
        # MUHIM: Document 3 da bu statement ID = "0f5eb130-a67b-4555-a526-1c88fa86a5f3"
        # va "statement_name": "Yer o'zlashtirish" deb ko'rinadi.
        # Column ID lar ham shu statementga tegishli.
        # Ammo logda bu statement topilmayapti!
        # Ehtimol name_uz boshqacha: masalan "Yer o'zlashtirib foydalanish" yoki boshqa variant
        "statement_name": "Yer o'zlashtirish",
        "period": "yearly",
        "plan": {
            "column_id": "b0397d0b-5cfe-4325-8e1e-391b955c195f",
        },
        "actual": {
            "column_id": "3331238c-d045-461a-ac4d-bee8c064d41e",
        },
    },
    {
        "column_name": "Dorivor o'simliklar plantatsiyalarini barpo etish",
        "unit": "gektar",
        # ✅ TO'G'RI - logda tasdiqlangan
        # ID: 2017abdc-8b00-45bf-beaa-85337dc3d734
        # Name: Лекарственное выращивание
        # Name UZ: Dorivor yetishtirish
        "statement_name": "Dorivor yetishtirish",
        "period": "monthly",
        "plan": {
            "column_id": "bb660080-02c3-439c-b1ca-aa7b5d317540",
        },
        "actual": {
            "column_id": "e8616e77-006b-4f04-bde5-3d533b03caa5",
        },
    },
    {
        "column_name": "Dorivor o'simliklar xomashyosini tayyorlash",
        "unit": "tonna",
        # ✅ TO'G'RI - logda tasdiqlangan
        "statement_name": "Dorivor yetishtirish",
        "period": "monthly",
        "plan": {
            "column_id": "09a4a0ee-de86-4a5f-a868-abc78b3ab527",
        },
        "actual": {
            "column_id": "cbc819af-5e4f-4a68-bc6e-d1b304500f65",
        },
    },
    {
        "column_name": "Cho'l, tog'li va tog'oldi hududlarida himoya o'rmonzorlari (ihota) barpo etish",
        "unit": "gektar",
        # ✅ TO'G'RI - logda tasdiqlangan
        # ID: c9027a9e-6c1f-483e-96d5-c752a99c1394
        # Name: Отдел создания леса
        # Name UZ: O'rmon barpo qilish bo'limi
        "statement_name": "O'rmon barpo qilish bo'limi",
        "period": "monthly",
        "plan": {
            "column_id": "c4f486c9-7d07-4aac-abd9-7bdbdfe0ea9c",
        },
        "actual": {
            "column_id": "9a293811-04c9-49ac-9bf3-7f9922e5d3da",
        },
    },
    {
        "column_name": "Niholxona va ko'chatchonalar tashkil etish",
        "unit": "mln dona",
        # ✅ TO'G'RI - logda tasdiqlangan
        # ID: 7b246be3-c3a3-4053-be76-afbdf636e703
        # Name: Питомник и Саженец Всего
        # Name UZ: Ko'chatxona va Niholxona Jami
        "statement_name": "Ko'chatxona va Niholxona Jami",
        "period": "monthly",
        "plan": {
            "column_id": "c58868c3-927d-4ec0-8e3c-279d3fe59046",
        },
        "actual": {
            "column_id": "23c07e35-c41c-4558-ae04-3ab5a2528305",
        },
    },
    {
        "column_name": "Orolbo'yi mintaqasi va boshqa cho'l hududlarida yashil qoplama barpo etish",
        "unit": "ming gektar",
        # ✅ TO'G'RI - logda tasdiqlangan
        "statement_name": "O'rmon barpo qilish bo'limi",
        "period": "monthly",
        "plan": {
            "column_id": "97332716-b82f-4c3c-9a68-16b6690d4115",
        },
        "actual": {
            "column_id": "b78efe32-7498-4ec9-a21b-fb30a9255c72",
        },
    },
    {
        "column_name": "Jumladan, tut ko'chatlari yetishtirish",
        "unit": "mln dona",
        # ✅ TO'G'RI - logda tasdiqlangan va ishlayapti!
        # ID: c7bca5cc-1983-49c5-ad42-24a8f8bbe01b
        # Name: Саженец и саженец тутового дерева
        # Name UZ: Tut Ko'chat va Tut Nihol
        # Plan: 1600000, Actual: 1620112 ✅
        "statement_name": "Tut Ko'chat va Tut Nihol",
        "period": "monthly",
        "plan": {
            "column_id": "da520dc4-e753-43bf-bf56-49155bc14310",
        },
        "actual": {
            "column_id": "1101a199-9b38-4da6-81fb-65929cd57e16",
        },
    },
]
REPORT_DASHBOARD_COLUMNS = [

    # =====================================================
    # 1. O‘rmon bilan qoplangan yer maydonlari
    # =====================================================

    {
        "statement_name": "O‘rmon bilan qoplangan yerlar",
        "parent_column_title": "O‘rmon bilan qoplanmagan yerlar tematik qatlamining atributiv ma’lumotlari",
        "column_title": "O‘rmon bilan qoplanmagan yerlar (ga)",
        "parent_column_ordering": "6.1",
        "column_ordering": "6.1.2",
        "period": "yearly",
        "data_ordering": 1
    },

    # =====================================================
    # 2. O‘rmon yerlarini o‘zlashtirib, foydalanishga kiritish
    # =====================================================

    {   "key":"yer_reja",
        "statement_name": "Yer o‘zlashtirish",
        "parent_column_title": "2025 yilda foydalanishga kiritiladigan o‘rmon fondi yerlari maydoni to‘g‘risida ma’lumot",
        "column_title": "Reja",
        "parent_column_ordering": "1.1",
        "column_ordering": "1.1.2",
        "period": "yearly",
        "type":"plan",
        "data_ordering": 2
    },
    {
        "key":"yer_amalda",
        "statement_name": "Yer o‘zlashtirish",
        "parent_column_title": "2025 yilda foydalanishga kiritiladigan o‘rmon fondi yerlari maydoni to‘g‘risida ma’lumot",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1",
        "column_ordering": "1.1.3",
        "period": "yearly",
        "type":"actual",
        "data_ordering": 3
    },
    {
        "key": "yer_farq",
        "depends_on": ["yer_reja", "yer_amalda"],
        "type": "diff",
        "data_ordering": 4,
    },
    {
        "key": "yer_foiz",
        "depends_on": ["yer_reja", "yer_amalda"],
        "type": "percent",
        "data_ordering": 5,
    },


    # =====================================================
    # 3. O‘rmonlar (yashil qoplamalar) barpo etish va qayta tiklash
    # =====================================================

    {
        "key":"urmon_barpo_reja",
        "statement_name": " O'rmon barpo qilish bo'limi",
        "parent_column_title": "O‘rmonlar (yashil qoplamalar) barpo etish va qayta tiklash (ga)",
        "column_title": "Reja",
        "parent_column_ordering": "1.1.3",
        "column_ordering": "1.1.3.1",
        "period": "monthly",
        "type":"plan",
        "data_ordering": 6
    },
    {
        "key":"urmon_barpo_amalda",
        "statement_name": " O'rmon barpo qilish bo'limi",
        "parent_column_title": "O‘rmonlar (yashil qoplamalar) barpo etish va qayta tiklash (ga)",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1.3",
        "column_ordering": "1.1.3.2",
        "period": "monthly",
        "type":"actual",
        "data_ordering": 7
    },
    {
        "key": "urmon_barpo_farq",
        "depends_on": ["urmon_barpo_reja", "urmon_barpo_amalda"],
        "type": "diff",
        "data_ordering": 8,
    },
    {
        "key": "urmon_barpo_foiz",
        "depends_on": ["urmon_barpo_reja", "urmon_barpo_amalda"],
        "type": "percent",
        "data_ordering": 9,
    },


    # =====================================================
    # 4. Orolbo‘yi mintaqasi va cho‘l hududlari
    # =====================================================

    {
        "key":"urmon_orolboyi_reja",
        "statement_name": "O'rmon barpo qilish bo'limi",
        "parent_column_title": "Orolbo‘yi mintaqasida yashil qoplama barpo etish (ga)",
        "column_title": "Reja",
        "parent_column_ordering": "1.1.5",
        "column_ordering": "1.1.5.1",
        "period": "monthly",
        "type":'plan',
        "data_ordering": 10
    },
    {
        "key":"urmon_orolboyi_amalda",
        "statement_name": "O'rmon barpo qilish bo'limi",
        "parent_column_title": "Orolbo‘yi mintaqasida yashil qoplama barpo etish (ga)",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1.5",
        "column_ordering": "1.1.5.2",
        "period": "monthly",
        "type":"actual",
        "data_ordering": 11
    },
    {
        "key": "urmon_orolboyi_farq",
        "depends_on": ["urmon_orolboyi_reja", "urmon_orolboyi_amalda"],
        "type": "diff",
        "data_ordering": 12,
    },
    {
        "key": "urmon_orolboyi_foiz",
        "depends_on": ["urmon_orolboyi_reja", "urmon_orolboyi_amalda"],
        "type": "percent",
        "data_ordering": 13,
    },

    # =====================================================
    # 5. Ko‘chat va nihollar yetishtirish
    # =====================================================

    {
        "key":"urmon_yashil_reja",
        "statement_name": "O'rmon barpo qilish bo'limi",
        "parent_column_title": "Orolning qurigan tubida yashil qoplamalar barpo etish (ga)",
        "column_title": "Reja",
        "parent_column_ordering": "1.1.6",
        "column_ordering": "1.1.6.1",
        "period": "monthly",
        "type":"plan",
        "data_ordering": 14
    },
    {
        "key":"urmon_yashil_amalda",
        "statement_name": "O'rmon barpo qilish bo'limi",
        "parent_column_title": "Orolning qurigan tubida yashil qoplamalar barpo etish (ga)",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1.6",
        "column_ordering": "1.1.6.2",
        "period": "monthly",
        "type":"actual",
        "data_ordering": 15
    },
    {
        "key": "urmon_yashil_farq",
        "depends_on": ["urmon_yashil_reja", "urmon_yashil_amalda"],
        "type": "diff",
        "data_ordering": 16,
    },
    {
        "key": "urmon_yashil_foiz",
        "depends_on": ["urmon_yashil_reja", "urmon_yashil_amalda"],
        "type": "percent",
        "data_ordering": 17,
    },


    # =====================================================
    # 6. Daraxt va butalarning urug‘larini jamg‘arish
    # =====================================================

    {
        "key":"urmon_himoya_reja",
        "statement_name": "O'rmon barpo qilish bo'limi",
        "parent_column_title": "Himoya o‘rmonzorlarini barpo etish (ga)",
        "column_title": "Reja",
        "parent_column_ordering": "1.1.4",
        "column_ordering": "1.1.4.1",
        "period": "monthly",
        "type":"plan",
        "data_ordering": 18
    },
    {
        "key":"urmon_himoya_amalda",
        "statement_name": "O'rmon barpo qilish bo'limi",
        "parent_column_title": "Himoya o‘rmonzorlarini barpo etish (ga)",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1.4",
        "column_ordering": "1.1.4.2",
        "period": "yearly",
        "type":"actual",
        "data_ordering": 19
    },
    {
        "key": "urmon_himoya_farq",
        "depends_on": ["urmon_himoya_reja", "urmon_himoya_amalda"],
        "type": "diff",
        "data_ordering": 20,
    },
    {
        "key": "urmon_himoya_foiz",
        "depends_on": ["urmon_yashil_reja", "urmon_himoya_amalda"],
        "type": "percent",
        "data_ordering": 21,
    },

    # =====================================================
    # 7. Himoya o‘rmonzorlarini (ihota) barpo etish
    # =====================================================

    {
        "key":"urmon_tog_reja",
        "statement_name": "Terassa",
        "parent_column_title": "O‘rmon xo‘jaliklari tomonidan 2025-yil bahorgi mavsumdan boshlab tog‘ va tog‘oldi"
                               " hududlarida tuproq eroziyasiga qarshi kurashish uchun terrasa usul bilan o‘rmon tuzish"
                               " ko‘rsatkichlari",
        "column_title": "Reja",
        "parent_column_ordering": "1.1",
        "column_ordering": "1.1.3",
        "period": "quarterly",
        "type":"plan",
        "data_ordering": 22
    },
    {
        "key":"urmon_tog_amalda",
        "statement_name": "Terassa",
        "parent_column_title": "O‘rmon xo‘jaliklari tomonidan 2025-yil bahorgi mavsumdan boshlab tog‘ va tog‘oldi"
                               " hududlarida tuproq eroziyasiga qarshi kurashish uchun terrasa usul bilan o‘rmon tuzish"
                               " ko‘rsatkichlari",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1",
        "column_ordering": "1.1.4",
        "period": "quarterly",
        "type":"actual",
        "data_ordering": 23
    },
    {
        "key": "urmon_tog_farq",
        "depends_on": ["urmon_tog_reja", "urmon_tog_amalda"],
        "type": "diff",
        "data_ordering": 24,
    },
    {
        "key": "urmon_tog_foiz",
        "depends_on": ["urmon_tog_reja", "urmon_tog_amalda"],
        "type": "percent",
        "data_ordering": 25,
    },

    # =====================================================
    # 8. Terassa uslubida o‘rmonlar barpo etish
    # =====================================================

    {
        "key":"bryusanetta_reja",
        "statement_name": "Bryusanetta",
        "parent_column_title": "Reja",
        "column_title": "Maydoni (gektar) Reja",
        "parent_column_ordering": "1.1.3",
        "column_ordering": "1.1.3.1",
        "period": "quarterly",
        "type":"plan",
        "data_ordering": 26
    },
    {
        "key":"bryusanetta_amalda",
        "statement_name": "Bryusanetta",
        "parent_column_title": "Amalda",
        "column_title": "Maydoni (gektar)",
        "parent_column_ordering": "1.1.4",
        "column_ordering": "1.1.4.1",
        "period": "quarterly",
        "type":"actual",
        "data_ordering": 27
    },
    {
        "key": "bryusanetta_farq",
        "depends_on": ["bryusanetta_reja", "bryusanetta_amalda"],
        "type": "diff",
        "data_ordering": 28,
    },
    {
        "key": "bryusanetta_foiz",
        "depends_on": ["bryusanetta_reja", "bryusanetta_amalda"],
        "type": "percent",
        "data_ordering": 29,
    },

    {
        "key": "bryusanetta_kochat_foiz",
        "statement_name": "Bryusanetta",
        "parent_column_title": "Reja",
        "column_title": "Ekiladigan ko'chatlar soni Reja",
        "parent_column_ordering": "1.1.3",
        "column_ordering": "1.1.3.2",
        "period": "quarterly",
        "type":"plan",
        "data_ordering": 30
    },
    {
        "key": "bryusanetta_kochat_amalda",
        "statement_name": "Bryusanetta",
        "parent_column_title": "Amalda",
        "column_title": "Ekiladigan ko'chatlar soni",
        "parent_column_ordering": "1.1.4",
        "column_ordering": "1.1.4.2",
        "period": "quarterly",
        "type":"actual",
        "data_ordering": 31
    },
    {
        "key": "bryusanetta_kochat_farq",
        "depends_on": ["bryusanetta_kochat_reja", "bryusanetta_kochat_amalda"],
        "type": "diff",
        "data_ordering": 32
    },
    {
        "key": "bryusanetta_kochat_foiz",
        "depends_on": ["bryusanetta_kochat_reja", "bryusanetta_kochat_amalda"],
        "type": "percent",
        "data_ordering": 33
    },

    # =====================================================
    # 9. Brussonetia yetishtirish
    # =====================================================

    {
        "key": "urug_xarakat_reja",
        "statement_name": "Urug' xarakati Reja",
        "parent_column_title": "Urug' jamg'arish miqdori",
        "column_title": "Reja",
        "parent_column_ordering": "1.1.2",
        "column_ordering": "1.1.2.1",
        "period": "daily",
        "plan":"plan",
        "data_ordering": 34
    },
    {
        "key": "urug_xarakat_amalda",
        "statement_name": "Urug' xarakati Reja",
        "parent_column_title": "Urug' jamg'arish miqdori",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1.2",
        "column_ordering": "1.1.2.2",
        "period": "daily",
        "plan":"actual",
        "data_ordering": 36
    },
    {
        "key": "urug_xarakat_farq",
        "depends_on": ["urug_xarakat_reja", "urug_xarakat_amalda"],
        "type": "diff",
        "data_ordering": 37
    },
    {
        "key": "urug_xarakat_foiz",
        "depends_on": ["urug_xarakat_reja", "urug_xarakat_amalda"],
        "type": "percent",
        "data_ordering": 38
    },

    # =====================================================
    # 10. Urug‘ jamg‘arish
    # =====================================================

    {
        "key": "kochat_nihol_reja",
        "statement_name": "Ko'chatxona va Niholxona Jami",
        "parent_column_title": "Jami niholxona va ko‘chatxonalar tashkil etish (ga)",
        "column_title": "Reja",
        "parent_column_ordering": "1.1.2",
        "column_ordering": "1.1.2.1",
        "period": "monthly",
        "type":"plan",
        "data_ordering": 39
    },
    {
        "key": "kochat_nihol_amalda",
        "statement_name": "Ko'chatxona va Niholxona Jami",
        "parent_column_title": "Jami niholxona va ko‘chatxonalar tashkil etish (ga)",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1.2",
        "column_ordering": "1.1.2.2",
        "period": "monthly",
        "type":"actual",
        "data_ordering": 40
    },
    {
        "key": "kochat_nihol_farq",
        "depends_on": ["kochat_nihol_reja", "kochat_nihol_amalda"],
        "type": "diff",
        "data_ordering": 41
    },
    {
        "key": "kochat_nihol_foiz",
        "depends_on": ["kochat_nihol_reja", "kochat_nihol_amalda"],
        "type": "percent",
        "data_ordering": 42
    },

    # =====================================================
    # 11. Niholxona va ko‘chatxona
    # =====================================================

    {
        "key": "kochat_nihol_jami_reja",
        "statement_name": "Ko'chat va Nihol Yetishtirish Jami",
        "parent_column_title": "Jami niholxona va ko‘chatxonalar tashkil etish (dona)",
        "column_title": "Reja",
        "parent_column_ordering": "1.1.2",
        "column_ordering": "1.1.2.1",
        "period": "yearly",
        "type":"plan",
        "data_ordering": 43
    },
    {
        "key": "kochat_nihol_jami_amalda",
        "statement_name": "Ko'chat va Nihol Yetishtirish Jami",
        "parent_column_title": "Jami niholxona va ko‘chatxonalar tashkil etish (dona)",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1.2",
        "column_ordering": "1.1.2.2",
        "period": "yearly",
        "type":"actual",
        "data_ordering": 44
    },
    {
        "key": "kochat_nihol_jami_farq",
        "depends_on": ["kochat_nihol_jami_reja", "kochat_nihol_jami_amalda"],
        "type": "diff",
        "data_ordering": 45
    },
    {
        "key": "kochat_nihol_jami_foiz",
        "depends_on": ["kochat_nihol_jami_reja", "kochat_nihol_jami_amalda"],
        "type": "percent",
        "data_ordering": 46
    },

    # =====================================================
    # 12. Ko‘chat va nihol
    # =====================================================

    {
        "key": "kochat_tut_reja",
        "statement_name": "Tut Ko'chat va Tut Nihol",
        "parent_column_title": "Jami niholxona va ko'chatxonalar tashkil etish",
        "column_title": "Reja",
        "parent_column_ordering": "1.1.2",
        "column_ordering": "1.1.2.1",
        "period": "monthly",
        "type":"plan",
        "data_ordering": 47
    },
    {
        "key": "kochat_tut_amalda",
        "statement_name": "Tut Ko'chat va Tut Nihol",
        "parent_column_title": "Jami niholxona va ko'chatxonalar tashkil etish",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1.2",
        "column_ordering": "1.1.2.2",
        "period": "monthly",
        "type":"actual",
        "data_ordering": 48
    },
    {
        "key": "kochat_tut_farq",
        "depends_on": ["kochat_tut_reja", "kochat_tut_amalda"],
        "type": "diff",
        "data_ordering": 49
    },
    {
        "key": "kochat_tut_foiz",
        "depends_on": ["kochat_tut_reja", "kochat_tut_amalda"],
        "type": "percent",
        "data_ordering": 50
    },

    # =====================================================
    # 13. Tut ko‘chatlari
    # =====================================================

    {
        "key": "ogir_mahala_reja",
        "statement_name": "Og'ir mahalla",
        "parent_column_title": "O‘zbekiston Respublikasi Prezidentining 2025-yil 17-yanvardagi PQ-12 sonli qarorining"
                               " 2025-yilda aholi bandligini ta’minlash va kambag‘alchilikni qisqartirish chora tadbirlari"
                               " to‘g‘risida”gi qarorida berilgan topshiriqlari ijrosi yuzasidan yetkazib beriladigan ko'chatlar"
                               " soni to‘g‘risidagi ma’lumot",
        "column_title": "Reja",
        "parent_column_ordering": "1.1",
        "column_ordering": "1.1.4",
        "period": "quarterly",
        "type":"plan",
        "data_ordering": 51
    },
    {
        "key": "ogir_mahala_amalda",
        "statement_name": "Og'ir mahalla",
        "parent_column_title": "O‘zbekiston Respublikasi Prezidentining 2025-yil 17-yanvardagi PQ-12 sonli qarorining"
                               " 2025-yilda aholi bandligini ta’minlash va kambag‘alchilikni qisqartirish chora tadbirlari"
                               " to‘g‘risida”gi qarorida berilgan topshiriqlari ijrosi yuzasidan yetkazib beriladigan ko'chatlar"
                               " soni to‘g‘risidagi ma’lumot",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1",
        "column_ordering": "1.1.5",
        "period": "quarterly",
        "type":"actual",
        "data_ordering": 52
    },
    {
        "key": "ogir_mahala_farq",
        "depends_on": ["ogir_mahala_reja", "ogir_mahala_amalda"],
        "type": "diff",
        "data_ordering": 53
    },
    {
        "key": "ogir_mahala_foiz",
        "depends_on": ["ogir_mahala_reja", "ogir_mahala_amalda"],
        "type": "percent",
        "data_ordering": 54
    },

    # =====================================================
    # 14. Mahallalarga yetkazib berish
    # =====================================================

    {
        "key": "sogliq_saqlash_reja",
        "statement_name": "Sog'liqni saqlash",
        "parent_column_title": "Reja",
        "column_title": "Jami Reja",
        "parent_column_ordering": "1.1.3.1",
        "column_ordering": "1.1.3.1.1",
        "period": "quarterly",
        "type":"plan",
        "data_ordering": 55
    },
    {
        "key": "sogliq_saqlash_amalda",
        "statement_name": "Sog'liqni saqlash",
        "parent_column_title": "Amalda",
        "column_title": "Jami",
        "parent_column_ordering": "1.1.3.2",
        "column_ordering": "1.1.3.2.1",
        "period": "quarterly",
        "type":"actual",
        "data_ordering": 56
    },
    {
        "key": "sogliq_saqlash_farq",
        "depends_on": ["sogliq_saqlash_reja", "sogliq_saqlash_amalda"],
        "type": "diff",
        "data_ordering": 57
    },
    {
        "key": "sogliq_saqlash_foiz",
        "depends_on": ["sogliq_saqlash_reja", "sogliq_saqlash_amalda"],
        "type": "percent",
        "data_ordering": 58
    },

    # =====================================================
    # 15. Dorivor o‘simliklar
    # =====================================================

    {
        "key": "talim_reja",
        "statement_name": " Talim muassasalariga yetkazib berilgan ko'chatlar",
        "parent_column_title": "Reja",
        "column_title": "Jami Reja",
        "parent_column_ordering": "1.1.3.1",
        "column_ordering": "1.1.3.1.1",
        "period": "quarterly",
        "type":"plan",
        "data_ordering": 59
    },
    {
        "key": "talim_amalda",
        "statement_name": " Talim muassasalariga yetkazib berilgan ko'chatlar",
        "parent_column_title": "Amalda",
        "column_title": "Jami",
        "parent_column_ordering": "1.1.3.2",
        "column_ordering": "1.1.3.2.1",
        "period": "quarterly",
        "type":"actual",
        "data_ordering": 60
    },
    {
        "key": "talim_farq",
        "depends_on": ["talim_reja", "talim_amalda"],
        "type": "diff",
        "data_ordering": 61
    },
    {
        "key": "talim_foiz",
        "depends_on": ["talim_reja", "talim_amalda"],
        "type": "percent",
        "data_ordering": 62
    },

    # =====================================================
    # 16. Chorvachilik / qishloq xo‘jaligi
    # =====================================================

    {
        "key": "dorivor_reja",
        "statement_name": "Dorivor yetishtirish",
        "parent_column_title": "Plantatsiya barpo etish, ga",
        "column_title": "Reja",
        "parent_column_ordering": "1.1.2",
        "column_ordering": "1.1.2.1",
        "period": "monthly",
        "type":"plan",
        "data_ordering": 63
    },
    {
        "key": "dorivor_amalda",
        "statement_name": "Dorivor yetishtirish",
        "parent_column_title": "Plantatsiya barpo etish, ga",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1.2",
        "column_ordering": "1.1.2.2",
        "period": "monthly",
        "type":"actual",
        "data_ordering": 64
    },
    {
        "key": "dorivor_farq",
        "depends_on": ["dorivor_reja", "dorivor_amalda"],
        "type": "diff",
        "data_ordering": 65
    },
    {
        "key": "dorivor_foiz",
        "depends_on": ["dorivor_reja", "dorivor_amalda"],
        "type": "percent",
        "data_ordering": 66
    },
    # =====================================================
    # 17. Daromadlar
    # =====================================================

    {
        "key": "xomashyos_reja",
        "statement_name": "Dorivor yetishtirish",
        "parent_column_title": "Xomashyosini tayyorlash, tn",
        "column_title": "Reja",
        "parent_column_ordering": "1.1.3",
        "column_orderinXususiy sektor tomonidan tashkil etildi 01.01.2026 yil holatigag": "1.1.3.1",
        "period": "monthly",
        "type":"plan",
        "data_ordering": 67
    },
    {
        "key": "xomashyos_amalda",
        "statement_name": "Dorivor yetishtirish",
        "parent_column_title": "Xomashyosini tayyorlash, tn",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1.3",
        "column_ordering": "1.1.3.2",
        "period": "monthly",
        "type":"actual",
        "data_ordering": 68
    },
    {
        "key": "xomashyos_farq",
        "depends_on": ["xomashyos_reja", "xomashyos_amalda"],
        "type": "diff",
        "data_ordering": 69
    },
    {
        "key": "xomashyos_foiz",
        "depends_on": ["xomashyos_reja", "xomashyos_amalda"],
        "type": "percent",
        "data_ordering": 70
    },

    # =====================================================
    # 18. Galofit bog‘lar
    # =====================================================

    {
        "key": "chorvachilik_reja",
        "statement_name": "Chorvachilik",
        "parent_column_title": "xususiy sektor tomonidan asalari oilasi tashkil etish",
        "column_title": "Reja",
        "parent_column_ordering": "5.1.7",
        "column_ordering": "5.1.7.1",
        "period": "monthly",
        "type":"plan",
        "data_ordering": 71
    },
    {
        "key": "chorvachilik_amalda",
        "statement_name": "Chorvachilik",
        "parent_column_title": "xususiy sektor tomonidan asalari oilasi tashkil etish",
        "column_title": "Amalda",
        "parent_column_ordering": "5.1.7",
        "column_ordering": "5.1.7.2",
        "period": "monthly",
        "type":"actual",
        "data_ordering": 72
    },
    {
        "key": "chorvachilik_farq",
        "depends_on": ["chorvachilik_reja", "chorvachilik_amalda"],
        "type": "diff",
        "data_ordering": 73
    },
    {
        "key": "chorvachilik_foiz",
        "depends_on": ["chorvachilik_reja", "chorvachilik_amalda"],
        "type": "percent",
        "data_ordering": 74
    },

    # =====================================================
    # 19. Qishloq xojaligi
    # =====================================================

    {
        "key": "qishloq_reja",
        "statement_name": "Qishloq xo'jaligi",
        "parent_column_title": "Jami qishloq xo‘jaligi mahsulotlari ekilishi",
        "column_title": "Reja",
        "parent_column_ordering": "9.1.2",
        "column_ordering": "9.1.2.2",
        "period": "monthly",
        "type":"plan",
        "data_ordering": 75
    },
    {
        "key": "qishloq_amalda",
        "statement_name": "Qishloq xo'jaligi",
        "parent_column_title": "Jami qishloq xo‘jaligi mahsulotlari ekilishi",
        "column_title": "Amalda",
        "parent_column_ordering": "9.1.2",
        "column_ordering": "9.1.2.4",
        "period": "monthly",
        "type":"actual",
        "data_ordering": 76
    },
    {
        "key": "qishloq_farq",
        "depends_on": ["qishloq_reja", "qishloq_amalda"],
        "type": "diff",
        "data_ordering": 77
    },
    {
        "key": "qishloq_foiz",
        "depends_on": ["qishloq_reja", "qishloq_amalda"],
        "type": "percent",
        "data_ordering": 78
    },

    # =====================================================
    # 20. Galofit bog‘lar
    # =====================================================

    {
        "key": "qishloq_jami_reja",
        "statement_name": "Chorvachilik",
        "parent_column_title": "Jami bosh soni",
        "column_title": "Reja",
        "parent_column_ordering": "3.1.13.1",
        "column_ordering": "3.1.13.1.1",
        "period": "monthly",
        "type":"plan",
        "data_ordering": 79
    },
    {
        "key": "qishloq_jami_amalda",
        "statement_name": "Chorvachilik",
        "parent_column_title": "Jami bosh soni",
        "column_title": "Amalda",
        "parent_column_ordering": "3.1.13.1",
        "column_ordering": "3.1.13.1.1",
        "period": "monthly",
        "type":"actual",
        "data_ordering": 80
    },
    {
        "key": "qishloq_jami_farq",
        "depends_on": ["qishloq_jami_reja", "qishloq_jami_amalda"],
        "type": "diff",
        "data_ordering": 81
    },
    {
        "key": "qishloq_jami_foiz",
        "depends_on": ["qishloq_jami_reja", "qishloq_jami_amalda"],
        "type": "percent",
        "data_ordering": 82
    },

# =====================================================
#     21. Chorvachilik
#     =====================================================

    {
        "key": "jami_parranda_reja",
        "statement_name": "Chorvachilik",
        "parent_column_title": "Jami parranda",
        "column_title": "Reja",
        "parent_column_ordering": "4.1.6.1",
        "column_ordering": "4.1.6.1.1",
        "period": "monthly",
        "type":"plan",
        "data_ordering": 83
    },
    {
        "key": "jami_parranda_amalda",
        "statement_name": "Chorvachilik",
        "parent_column_title": "Jami parranda",
        "column_title": "Amalda",
        "parent_column_ordering": "4.1.6.1",
        "column_ordering": "4.1.6.1.2",
        "period": "monthly",
        "type":"actual",
        "data_ordering": 84
    },
    {
        "key": "jami_parranda_farq",
        "depends_on": ["jami_parranda_reja", "jami_parranda_amalda"],
        "type": "diff",
        "data_ordering": 85
    },
    {
        "key": "jami_parranda_foiz",
        "depends_on": ["jami_parranda_reja", "jami_parranda_amalda"],
        "type": "percent",
        "data_ordering": 86
    },

    {
        "key": "daromad_reja",
        "statement_name": "Daromad",
        "parent_column_title": "2025 yil holatiga daromad tushumi to‘g‘risida ma’lumot",
        "column_title": "Yillik reja",
        "parent_column_ordering": "1.1",
        "column_ordering": "1.1.2",
        "period": "yearly",
        "type":"plan",
        "data_ordering": 87
    },
    {
        "key": "daromad_amalda",
        "statement_name": "Daromad",
        "parent_column_title": "2025 yil holatiga daromad tushumi to‘g‘risida ma’lumot",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1",
        "column_ordering": "1.1.3",
        "period": "yearly",
        "type":"actual",
        "data_ordering": 88
    },
    {
        "key": "daromad_farq",
        "depends_on": ["daromad_reja", "daromad_amalda"],
        "type": "diff",
        "data_ordering": 89
    },
    {
        "key": "daromad_foiz",
        "depends_on": ["daromad_reja", "daromad_amalda"],
        "type": "percent",
        "data_ordering": 90
    },


    {
        "key": "golofit_reja",
        "statement_name": "Golofit",
        "parent_column_title": "2025-yilda galofit bog‘lar barpo etish to‘g‘risida ma’lumot",
        "column_title": "Reja",
        "parent_column_ordering": "1.1",
        "column_ordering": "1.1.3",
        "period": "quarterly",
        "type":"plan",
        "data_ordering": 91
    },
    {
        "key": "golofit_amalda",
        "statement_name": "Golofit",
        "parent_column_title": "2025-yilda galofit bog‘lar barpo etish to‘g‘risida ma’lumot",
        "column_title": "Amalda",
        "parent_column_ordering": "1.1",
        "column_ordering": "1.1.4",
        "period": "quarterly",
        "type":"actual",
        "data_ordering": 92
    },
    {
        "key": "golofit_farq",
        "depends_on": ["golofit_reja", "golofit_amalda"],
        "type": "diff",
        "data_ordering": 93
    },
    {
        "key": "golofit_foiz",
        "depends_on": ["golofit_reja", "golofit_amalda"],
        "type": "percent",
        "data_ordering": 94
    },
]


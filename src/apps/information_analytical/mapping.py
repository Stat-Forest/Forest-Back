MAPPING_RULES = [
    # 1) O‘rmon bilan qoplangan yer maydonlari (mln ga)
    dict(target="1.1.2", source_statement_name_uz="O'rmon bilan qoplangan yerlar", source="6.1.2"),

    # 2) O‘rmon yerlarini o‘zlashtirib, foydalanishga kiritish (ga)
    dict(target="1.1.3.1", source_statement_name_uz="Yer o'zlashtirish", source="1.1.2"),  # Reja
    dict(target="1.1.3.2", source_statement_name_uz="Yer o'zlashtirish", source="1.1.3"),  # Amalda

    # 3) O‘rmonlar (yashil qoplamalar) barpo etish va qayta tiklash (ga)
    dict(target="1.1.4.1", source_statement_name_uz="O'rmon barpo qilish", source="1.1.3.1"),
    dict(target="1.1.4.2", source_statement_name_uz="O'rmon barpo qilish", source="1.1.3.2"),

    # 4) Orolbo‘yi mintaqasida yashil qoplama (ming ga)
    dict(target="1.1.5.1", source_statement_name_uz="O'rmon barpo qilish", source="1.1.5.1"),
    dict(target="1.1.5.2", source_statement_name_uz="O'rmon barpo qilish", source="1.1.5.2"),

    # 5) Orol dengizining qurigan tubida (ga)
    dict(target="1.1.6.1", source_statement_name_uz="O'rmon barpo qilish", source="1.1.6.1"),
    dict(target="1.1.6.2", source_statement_name_uz="O'rmon barpo qilish", source="1.1.6.2"),

    # 6) Ihota (ga)
    dict(target="1.1.7.1", source_statement_name_uz="O'rmon barpo qilish", source="1.1.4.1"),
    dict(target="1.1.7.2", source_statement_name_uz="O'rmon barpo qilish", source="1.1.4.2"),

    # 7) Terassa (ga)
    dict(target="1.1.8.1", source_statement_name_uz="Terassa", source="1.1.3"),
    dict(target="1.1.8.2", source_statement_name_uz="Terassa", source="1.1.4"),

    # 8) Brussonetiya - Maydon (ga)
    dict(target="1.1.9.1.1", source_statement_name_uz="Bryusanetta", source="1.1.3.1"),
    dict(target="1.1.9.1.2", source_statement_name_uz="Bryusanetta", source="1.1.4.1"),

    # 9) Brussonetiya - Ko‘chatlar soni (dona)
    dict(target="1.1.9.2.1", source_statement_name_uz="Bryusanetta", source="1.1.3.2"),
    dict(target="1.1.9.2.2", source_statement_name_uz="Bryusanetta", source="1.1.4.2"),

    # 10) Urug‘ xarakati Reja
    dict(target="1.1.10.1", source_statement_name_uz="Urug' xarakati Reja", source="1.1.2.1"),
    dict(target="1.1.10.2", source_statement_name_uz="Urug' xarakati Reja", source="1.1.2.2"),

    # 11) Niholxona va ko‘chatxona (ga)
    dict(target="1.1.11.1", source_statement_name_uz="Ko'chatxona va Niholxona Jami", source="1.1.2.1"),
    dict(target="1.1.11.2", source_statement_name_uz="Ko'chatxona va Niholxona Jami", source="1.1.2.2"),

    # 12) Ko‘chat va nihol (ming dona)
    dict(target="1.1.12.1", source_statement_name_uz="Ko'chat va Nihol Yetishtirish Jami", source="1.1.2.1"),
    dict(target="1.1.12.2", source_statement_name_uz="Ko'chat va Nihol Yetishtirish Jami", source="1.1.2.2"),

    # 13) Tut ko‘chatlari (ming dona)
    dict(target="1.1.13.1", source_statement_name_uz="Tut Ko'chat va Tut Nihol", source="1.1.2.1"),
    dict(target="1.1.13.2", source_statement_name_uz="Tut Ko'chat va Tut Nihol", source="1.1.2.2"),

    # 14) 1024 mahalla (tup)
    dict(target="1.1.14.1", source_statement_name_uz="Og'ir mahalla", source="1.1.4"),
    dict(target="1.1.14.2", source_statement_name_uz="Og'ir mahalla", source="1.1.5"),

    # 15) Sog‘liqni saqlash (tup)
    dict(target="1.1.15.1", source_statement_name_uz="Sog'liqni saqlash", source="1.1.3.1.1"),
    dict(target="1.1.15.2", source_statement_name_uz="Sog'liqni saqlash", source="1.1.3.2.1"),

    # 16) Xalq ta’limi (tup)
    dict(target="1.1.16.1", source_statement_name_uz="Ta'lim muassasalariga yetkazib berilgan ko'chatlar", source="1.1.3.1.1"),
    dict(target="1.1.16.2", source_statement_name_uz="Ta'lim muassasalariga yetkazib berilgan ko'chatlar", source="1.1.3.2.1"),

    # 17) Dorivor plantatsiya (ga)
    dict(target="1.1.17.1", source_statement_name_uz="Dorivor yetishtirish", source="1.1.2.1"),
    dict(target="1.1.17.2", source_statement_name_uz="Dorivor yetishtirish", source="1.1.2.2"),

    # 18) Dorivor xomashyo (tn)
    dict(target="1.1.18.1", source_statement_name_uz="Dorivor yetishtirish", source="1.1.3.1"),
    dict(target="1.1.18.2", source_statement_name_uz="Dorivor yetishtirish", source="1.1.3.2"),

    # 19) Asalarichilik (ming oila)
    dict(target="1.1.19.1", source_statement_name_uz="Chorvachilik", source="5.1.8.1"),
    dict(target="1.1.19.2", source_statement_name_uz="Chorvachilik", source="5.1.8.2"),

    # 20) Qishloq xo‘jaligi (tn)
    dict(target="1.1.20.1", source_statement_name_uz="Qishloq xo'jaligi", source="9.1.2.2"),
    dict(target="1.1.20.2", source_statement_name_uz="Qishloq xo'jaligi", source="9.1.2.4"),

    # 21) Mayda shoxli chorvachilik
    dict(target="1.1.21.1", source_statement_name_uz="Chorvachilik", source="3.1.14.1.1"),
    dict(target="1.1.21.2", source_statement_name_uz="Chorvachilik", source="3.1.14.1.2"),

    # 22) Parrandachilik
    dict(target="1.1.22.1", source_statement_name_uz="Chorvachilik", source="4.1.7.1.1"),
    dict(target="1.1.22.2", source_statement_name_uz="Chorvachilik", source="4.1.7.1.2"),

    # 23) Korxonalar daromadi (mlrd so‘m)
    dict(target="1.1.23.1", source_statement_name_uz="Daromad", source="1.1.2"),
    dict(target="1.1.23.2", source_statement_name_uz="Daromad", source="1.1.3"),

    # 24) Galofit (ga)
    dict(target="1.1.24.1", source_statement_name_uz="Golofit", source="1.1.3"),
    dict(target="1.1.24.2", source_statement_name_uz="Golofit", source="1.1.4"),
]


# Hammasi bir xil formula: (Amalda/Reja*100) va (Reja-Amalda)
FORMULA_BLOCKS = [
    # 2)
    ("1.1.3.1", "1.1.3.2", "1.1.3.3", "1.1.3.4"),
    # 3)
    ("1.1.4.1", "1.1.4.2", "1.1.4.3", "1.1.4.4"),
    # 4)
    ("1.1.5.1", "1.1.5.2", "1.1.5.3", "1.1.5.4"),
    # 5)
    ("1.1.6.1", "1.1.6.2", "1.1.6.3", "1.1.6.4"),
    # 6)
    ("1.1.7.1", "1.1.7.2", "1.1.7.3", "1.1.7.4"),
    # 7)
    ("1.1.8.1", "1.1.8.2", "1.1.8.3", "1.1.8.4"),
    # 8)
    ("1.1.9.1.1", "1.1.9.1.2", "1.1.9.1.3", "1.1.9.1.4"),
    # 9)
    ("1.1.9.2.1", "1.1.9.2.2", "1.1.9.2.3", "1.1.9.2.4"),
    # 10)
    ("1.1.10.1", "1.1.10.2", "1.1.10.3", "1.1.10.4"),
    # 11)
    ("1.1.11.1", "1.1.11.2", "1.1.11.3", "1.1.11.4"),
    # 12)
    ("1.1.12.1", "1.1.12.2", "1.1.12.3", "1.1.12.4"),
    # 13)
    ("1.1.13.1", "1.1.13.2", "1.1.13.3", "1.1.13.4"),
    # 14)
    ("1.1.14.1", "1.1.14.2", "1.1.14.3", "1.1.14.4"),
    # 15)
    ("1.1.15.1", "1.1.15.2", "1.1.15.3", "1.1.15.4"),
    # 16)
    ("1.1.16.1", "1.1.16.2", "1.1.16.3", "1.1.16.4"),
    # 17)
    ("1.1.17.1", "1.1.17.2", "1.1.17.3", "1.1.17.4"),
    # 18)
    ("1.1.18.1", "1.1.18.2", "1.1.18.3", "1.1.18.4"),
    # 19)
    ("1.1.19.1", "1.1.19.2", "1.1.19.3", "1.1.19.4"),
    # 20)
    ("1.1.20.1", "1.1.20.2", "1.1.20.3", "1.1.20.4"),
    # 21)
    ("1.1.21.1", "1.1.21.2", "1.1.21.3", "1.1.21.4"),
    # 22)
    ("1.1.22.1", "1.1.22.2", "1.1.22.3", "1.1.22.4"),
    # 23)
    ("1.1.23.1", "1.1.23.2", "1.1.23.3", "1.1.23.4"),
    # 24)
    ("1.1.24.1", "1.1.24.2", "1.1.24.3", "1.1.24.4"),
]

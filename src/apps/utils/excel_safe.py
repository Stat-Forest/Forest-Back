"""
Excel (openpyxl) ga foydalanuvchi matnini xavfsiz yozish (audit B6).

openpyxl `=` bilan boshlangan har qanday str'ni FORMULA (data_type 'f') sifatida
saqlaydi — ijarachi nomi `=HYPERLINK(...)` yoki `=cmd|' /C calc'!A0` bo'lsa,
eksportni ochgan admin kompyuterida bajariladi (CSV/formula injection).
Bu yerdagi yordamchilar har qanday str'ni MATN (data_type 's') qilib saqlaydi;
raqam/sana/None o'zgarmaydi. Dasturning o'z formulalari (masalan JAMI uchun
=SUM(...)) bu yordamchilardan o'tkazilmaydi.
"""


def set_safe(cell, value):
    cell.value = value
    if isinstance(value, str):
        cell.data_type = "s"
    return cell


def append_safe(ws, values):
    ws.append(values)
    for cell in ws[ws.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = "s"
    return ws[ws.max_row]

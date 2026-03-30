FAST_RESPONSE_MAP = {
    "muddat nima": "Muddat - hisobot topshirish uchun belgilangan vaqt. Kunlik, haftalik, oylik bo'lishi mumkin.",
    "hisobot nima": "Hisobot - foydalanuvchi tomonidan yaratiladigan ma'lumot. Reja va amalda qiymatlaridan iborat.",
    "reja nima": "Reja - oldindan belgilangan qiymat. Bo'lim boshligi tomonidan yaratiladi.",
    "amalda nima": "Amalda - bajarilgan natija. Haqiqiy bajarilgan ishlar.",
    "viloyat jami nima": "Viloyat jami - viloyatdagi barcha tashkilot hisobotlari yig'indisi.",
    "respublika jami nima": "Respublika jami - barcha viloyatlar yig'indisi.",
    "bo'lim nima": "Bo'lim - tashkilotning tarkibiy qismi. Har bir bo'lim o'z hisobotlarini beradi.",
    "tashkilot nima": "Tashkilot - hisobot yuborish huquqiga ega bo'lgan muassasa.",
    "что такое муда": "Муда - срок сдачи отчета. Может быть ежедневным, еженедельным, месячным.",
    "что такое отчет": "Отчет - информация, создаваемая пользователем. Содержит план и факт.",
    "что такое план": "План - заранее определенные значения. Создается начальником отдела.",
    "что такое факт": "Факт - выполненный результат. Фактически выполненная работа.",
    "что такое областной итог": "Областной итог - сумма всех отчетов организаций в области.",
    "что такое республиканский итог": "Республиканский итог - сумма всех областей.",
    "что такое отдел": "Отдел - структурная часть организации. Каждый отдел сдает свои отчеты.",
    "что такое организация": "Организация - учреждение с правом сдачи отчетов.",
}

SIMPLE_PATTERNS = [
    "nima", "qanday", "qayerda", "qachon", "kim", "nechta", 
    "что", "как", "где", "когда", "кто", "сколько"
]

def get_fast_response(question: str) -> str:
    question_lower = question.lower().strip()
    return FAST_RESPONSE_MAP.get(question_lower)

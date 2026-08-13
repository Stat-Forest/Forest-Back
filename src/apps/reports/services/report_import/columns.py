# apps/reports/services/report_import/columns.py
"""
Berilgan Statement uchun foydalanuvchi import qilishi mumkin bo'lgan
"Amalda" ustunlarni qaytaradi.

Amalda ustun = StatementColumn WHERE:
    - status_plan IS NULL       (Reja ustuni EMAS)
    - is_user_input = True      (avto-hisoblangan EMAS)
    - is_organization = False   (tashkilot ustuni EMAS)
    - parent IS NOT NULL        (leaf darajadagi)

Template generator VA parser bir xil ustun ro'yxatidan foydalanadi —
shu funksiya orqali.
"""

from django.db.models import Q

from apps.reports.models import StatementColumn


def get_importable_columns(statement):
    """
    Statement uchun import qilinadigan barcha leaf ustunlarni
    `ordering` bo'yicha tartiblangan QuerySet sifatida qaytaradi.
    """
    return (
        StatementColumn.objects
        .filter(
            statement=statement,
            is_organization=False,
        )
        .filter(parent__isnull=False)
        .select_related("parent")
        .order_by("ordering")
    )

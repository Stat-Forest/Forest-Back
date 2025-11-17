from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.reports.models import StatementColumn, Plan, PlanItem


def _is_empty_plan_value(raw_value) -> bool:
    """Plan qiymati bo‘sh yoki nolga tengligini tekshiradi."""
    if raw_value in (None, "", 0, "0"):
        return True
    try:
        value = Decimal(str(raw_value))
        return value == 0
    except (InvalidOperation, TypeError, ValueError):
        return True

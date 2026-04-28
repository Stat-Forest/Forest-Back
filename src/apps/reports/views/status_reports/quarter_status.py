from apps.reports.models import Report
from apps.reports.services.quarter_validator import DaromadQuarterService


def _get_daromad_quarter_status_field(report: Report) -> str | None:
    """
    Faqat Daromad reportlar uchun current_quarter ga mos status field nomini qaytaradi.
    Masalan:
        current_quarter = 'q1' -> 'quarter_1_status'
    Qolgan reportlar uchun None qaytaradi.
    """
    if not DaromadQuarterService.is_daromad_report(report):
        return None

    current_quarter = getattr(report, "current_quarter", None)
    if not current_quarter:
        return None

    return DaromadQuarterService.get_quarter_status_field(current_quarter)


def _sync_daromad_current_quarter_status(
    report: Report,
    new_status: str,
    update_fields: list[str] | None = None,
) -> list[str]:
    """
    Faqat Daromad uchun:
    report.current_quarter qaysi bo'lsa, o'sha quarter_X_status ni report.status bilan sinxron qiladi.

    Qolgan reportlarga tegmaydi.
    """
    if update_fields is None:
        update_fields = []

    status_field = _get_daromad_quarter_status_field(report)
    if not status_field:
        return update_fields

    setattr(report, status_field, new_status)
    if status_field not in update_fields:
        update_fields.append(status_field)

    return update_fields
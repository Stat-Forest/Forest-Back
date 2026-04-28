from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional
from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.reports.models import Report, StatementColumn


@dataclass(frozen=True, slots=True)
class QuarterAccessInfo:
    current_quarter: Optional[str]
    next_available_quarter: Optional[str]
    can_create: bool
    can_update: bool


class DaromadQuarterService:
    """
    Daromad hisobotlari uchun chorak workflow servisi.

    Asosiy qoidalar:
    - Yangi report faqat Q1 bilan yaratiladi.
    - Q2 faqat Q1 ACCEPTED bo'lsa ochiladi.
    - Q3 faqat Q2 ACCEPTED bo'lsa ochiladi.
    - Q4 faqat Q3 ACCEPTED bo'lsa ochiladi.
    - User faqat har quarter uchun belgilangan AMALDA orderinglarga qiymat kiritadi.
    - status_plan bor rejalik columnlarga tegilmaydi.
    - is_organization=True columnlarga tegilmaydi.
    - Boshqa statementlar uchun bu service ishlatilmaydi.
    """

    QUARTER_ORDER: tuple[str, ...] = ("q1", "q2", "q3", "q4")
    DAROMAD_NAMES: tuple[str, ...] = ("Daromad",)

    QUARTER_INPUT_ORDERINGS: dict[str, tuple[str, ...]] = {
        "q1": ("1.3.2.1.2", "1.3.2.2.2", "1.3.2.3.2"),
        "q2": ("1.4.2.1.2", "1.4.2.2.2", "1.4.2.3.2"),
        "q3": ("1.5.2.1.2", "1.5.2.2.2", "1.5.2.3.2"),
        "q4": ("1.6.2.1.2", "1.6.2.2.2", "1.6.2.3.2"),
    }

    COMMON_ALLOWED_PREFIXES: tuple[str, ...] = ("1.1",)
    QUARTER_DATE_KEYS: tuple[str, ...] = ("saved_at", "sent_at", "accepted_at", "cancelled_at")

    @classmethod
    def is_daromad_statement(cls, statement) -> bool:
        name_uz = getattr(statement, "name_uz", None)
        name = getattr(statement, "name", None)
        return name_uz in cls.DAROMAD_NAMES or name in cls.DAROMAD_NAMES

    @classmethod
    def is_daromad_report(cls, report: Report) -> bool:
        return cls.is_daromad_statement(report.statement)

    @classmethod
    def validate_create(
        cls,
        *,
        statement,
        organization,
        deadline,
        quarter: str | None,
    ) -> None:
        if not cls.is_daromad_statement(statement):
            return

        cls._validate_quarter_required(quarter)

        if quarter != "q1":
            raise ValidationError({
                "quarter": _("Daromad hisoboti faqat I-chorakdan boshlanishi mumkin.")
            })

        if Report.objects.filter(
            organization=organization,
            statement=statement,
            deadline=deadline,
            is_individual_general=False,
            is_report=True,
        ).exists():
            raise ValidationError({
                "quarter": _(
                    "Bu tashkilot uchun Daromad hisoboti allaqachon yaratilgan. "
                    "Keyingi choraklarni yangi report ochib emas, mavjud reportni update qilib to'ldirasiz."
                )
            })

    @classmethod
    def validate_update(
        cls,
        *,
        report: Report,
        requested_quarter: str | None,
    ) -> None:
        if not cls.is_daromad_report(report):
            return

        cls._validate_quarter_required(requested_quarter)

        next_quarter = cls.get_next_available_quarter(report)

        if next_quarter is None:
            raise ValidationError({
                "quarter": _("Barcha choraklar yakunlangan. Qo'shimcha chorak kiritib bo'lmaydi.")
            })

        if requested_quarter != next_quarter:
            raise ValidationError({
                "quarter": _(f"Hozir faqat {cls.get_quarter_display(next_quarter)} ni to'ldirish mumkin.")
            })

        previous_quarter = cls.get_previous_quarter(requested_quarter)
        if previous_quarter:
            previous_status = report.get_quarter_status(previous_quarter)
            if previous_status != Report.StatusChoices.ACCEPTED:
                raise ValidationError({
                    "quarter": _(
                        f"{cls.get_quarter_display(requested_quarter)} ni to'ldirishdan oldin "
                        f"{cls.get_quarter_display(previous_quarter)} E-IMZO orqali ACCEPTED bo'lishi kerak."
                    )
                })

        requested_status = report.get_quarter_status(requested_quarter)
        if requested_status in (Report.StatusChoices.SENT, Report.StatusChoices.ACCEPTED):
            raise ValidationError({
                "quarter": _(
                    f"{cls.get_quarter_display(requested_quarter)} allaqachon jo'natilgan yoki qabul qilingan. "
                    "Uni qayta tahrirlab bo'lmaydi."
                )
            })

    @classmethod
    def validate_columns_for_quarter(
        cls,
        *,
        statement,
        quarter: str,
        column_ids: Iterable[str],
        allow_common: bool = True,
    ) -> None:
        if not column_ids:
            return

        columns = StatementColumn.objects.filter(
            statement=statement,
            id__in=list(column_ids),
        ).only(
            "id",
            "ordering",
            "title",
            "title_uz",
            "is_organization",
            "status_plan",
        )

        found_ids = {str(column.id) for column in columns}
        requested_ids = {str(column_id) for column_id in column_ids}
        missing = requested_ids - found_ids
        if missing:
            raise ValidationError({
                "statement_column": _(
                    f"Quyidagi column(lar) topilmadi: {', '.join(sorted(missing))}"
                )
            })

        current_quarter_orderings = set(cls.get_manual_input_orderings(quarter))
        other_quarter_orderings = set(cls.get_other_quarter_manual_input_orderings(quarter))

        for column in columns:
            if column.is_organization:
                continue

            if column.status_plan:
                continue

            if allow_common and any(column.ordering.startswith(prefix) for prefix in cls.COMMON_ALLOWED_PREFIXES):
                continue

            if column.ordering in current_quarter_orderings:
                continue

            if column.ordering in other_quarter_orderings:
                continue

            title = getattr(column, "title_uz", None) or column.title
            raise ValidationError({
                "statement_column": _(
                    f"Column '{title}' (ordering: {column.ordering}) "
                    f"{cls.get_quarter_display(quarter)} uchun ruxsat etilmagan."
                )
            })

    @classmethod
    def get_manual_input_orderings(cls, quarter: str) -> list[str]:
        return list(cls.QUARTER_INPUT_ORDERINGS.get(quarter, ()))

    @classmethod
    def get_other_quarter_manual_input_orderings(cls, quarter: str) -> list[str]:
        result: list[str] = []
        for q, orderings in cls.QUARTER_INPUT_ORDERINGS.items():
            if q == quarter:
                continue
            result.extend(orderings)
        return result

    @classmethod
    def get_next_available_quarter(cls, report: Report) -> Optional[str]:
        if report.get_quarter_status("q1") != Report.StatusChoices.ACCEPTED:
            return "q1"
        if report.get_quarter_status("q2") != Report.StatusChoices.ACCEPTED:
            return "q2"
        if report.get_quarter_status("q3") != Report.StatusChoices.ACCEPTED:
            return "q3"
        if report.get_quarter_status("q4") != Report.StatusChoices.ACCEPTED:
            return "q4"
        return None

    @classmethod
    def get_quarter_access_info(cls, report: Report) -> QuarterAccessInfo:
        next_quarter = cls.get_next_available_quarter(report)
        current_quarter = report.current_quarter or next_quarter

        can_create = cls.is_daromad_report(report) and next_quarter == "q1"
        can_update = cls.is_daromad_report(report) and next_quarter is not None and next_quarter != "q1"

        return QuarterAccessInfo(
            current_quarter=current_quarter,
            next_available_quarter=next_quarter,
            can_create=can_create,
            can_update=can_update,
        )

    @classmethod
    def prepare_report_for_create(cls, *, report: Report, quarter: str) -> None:
        """
        Faqat Daromad create paytida ishlaydi.
        Q1 dan boshlanadi va quarter_1_status SAVED bo'ladi.
        Shu vaqtda quarter_status_dates ham yangilanadi.
        """
        if not cls.is_daromad_report(report):
            return

        report.quarter = quarter
        report.current_quarter = quarter
        report.status = Report.StatusChoices.SAVED

        if quarter == "q1" and not report.quarter_1_status:
            report.quarter_1_status = Report.StatusChoices.SAVED

        cls.mark_quarter_saved(report, quarter)

    @classmethod
    def prepare_report_for_update(cls, *, report: Report, quarter: str) -> None:
        """
        Faqat Daromad update paytida ishlaydi.

        Workflow:
        - current quarter yangilanadi
        - report.status doim current quarter uchun SAVED ga tushadi
        - mos quarter_X_status ham SAVED bo'ladi
        - oldingi quarter statuslariga tegilmaydi
        - quarter_status_dates ichida saved_at yangilanadi
        """
        if not cls.is_daromad_report(report):
            return

        report.quarter = quarter
        report.current_quarter = quarter
        report.status = Report.StatusChoices.SAVED

        status_field = cls.get_quarter_status_field(quarter)
        setattr(report, status_field, Report.StatusChoices.SAVED)

        cls.mark_quarter_saved(report, quarter)

    @classmethod
    def get_quarter_status_field(cls, quarter: str) -> str:
        return f"quarter_{quarter[-1]}_status"

    @classmethod
    def get_previous_quarter(cls, quarter: str) -> Optional[str]:
        if quarter not in cls.QUARTER_ORDER:
            return None
        idx = cls.QUARTER_ORDER.index(quarter)
        if idx == 0:
            return None
        return cls.QUARTER_ORDER[idx - 1]

    @classmethod
    def get_quarter_display(cls, quarter: str) -> str:
        choices = dict(Report.QuarterChoices.choices)
        return choices.get(quarter, quarter)

    @classmethod
    def get_quarter_dates(cls, report: Report, quarter: str) -> dict:
        data = cls._ensure_quarter_status_dates(report)
        quarter_data = data.get(quarter, cls._empty_quarter_dates())

        return {
            "saved_at": cls._format_quarter_date_for_response(quarter_data.get("saved_at")),
            "sent_at": cls._format_quarter_date_for_response(quarter_data.get("sent_at")),
            "accepted_at": cls._format_quarter_date_for_response(quarter_data.get("accepted_at")),
            "cancelled_at": cls._format_quarter_date_for_response(quarter_data.get("cancelled_at")),
        }

    @classmethod
    def mark_quarter_saved(cls, report: Report, quarter: str) -> None:
        cls._set_quarter_date(report, quarter, "saved_at")

    @classmethod
    def mark_quarter_sent(cls, report: Report, quarter: str) -> None:
        cls._set_quarter_date(report, quarter, "sent_at")

    @classmethod
    def mark_quarter_accepted(cls, report: Report, quarter: str) -> None:
        cls._set_quarter_date(report, quarter, "accepted_at")

    @classmethod
    def mark_quarter_cancelled(cls, report: Report, quarter: str) -> None:
        cls._set_quarter_date(report, quarter, "cancelled_at")

    @classmethod
    def _set_quarter_date(
        cls,
        report: Report,
        quarter: str,
        date_key: str,
        when: Optional[datetime] = None,
    ) -> None:
        """
        report.quarter_status_dates ichida kerakli quarter/date field ni yangilaydi.
        Query urmaydi, faqat in-memory objectni o'zgartiradi.
        save(update_fields=[...]) tashqarida qilinadi.
        """
        if not cls.is_daromad_report(report):
            return

        if quarter not in cls.QUARTER_ORDER:
            return

        if date_key not in cls.QUARTER_DATE_KEYS:
            return

        payload = cls._ensure_quarter_status_dates(report)
        payload[quarter][date_key] = cls._serialize_dt(when or timezone.now())
        report.quarter_status_dates = payload

    @classmethod
    def _ensure_quarter_status_dates(cls, report: Report) -> dict:
        """
        quarter_status_dates ni har doim to'liq strukturaga keltiradi.
        default=dict bo'lgani uchun eski reportlarda {} bo'lishi mumkin.
        """
        payload = report.quarter_status_dates or {}

        normalized = {}
        for quarter in cls.QUARTER_ORDER:
            quarter_payload = payload.get(quarter) or {}
            normalized[quarter] = {
                "saved_at": quarter_payload.get("saved_at"),
                "sent_at": quarter_payload.get("sent_at"),
                "accepted_at": quarter_payload.get("accepted_at"),
                "cancelled_at": quarter_payload.get("cancelled_at"),
            }

        report.quarter_status_dates = normalized
        return normalized

    @classmethod
    def _empty_quarter_dates(cls) -> dict:
        return {
            "saved_at": None,
            "sent_at": None,
            "accepted_at": None,
            "cancelled_at": None,
        }

    @staticmethod
    def _serialize_dt(value: datetime | None) -> str | None:
        if value is None:
            return None
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        return value.isoformat()

    @staticmethod
    def _format_quarter_date_for_response(value: str | None) -> str | None:
        if not value:
            return None

        try:
            dt = datetime.fromisoformat(value)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return value

    @classmethod
    def _validate_quarter_required(cls, quarter: str | None) -> None:
        if not quarter:
            raise ValidationError({
                "quarter": _("Daromad hisobotida chorak majburiy.")
            })
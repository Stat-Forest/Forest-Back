from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional
from datetime import datetime

from django.utils import timezone
from django.core.exceptions import ValidationError
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
    - report.status doim "kamida bitta ACCEPTED quarter bor" holatini aks ettiradi:
        * Birorta ACCEPTED quarter bor → report.status = ACCEPTED
        * Hech biri ACCEPTED emas     → report.status = SAVED
      Bu ReportListAPIView va filtered-general'da report ko'rinishini ta'minlaydi.
    """

    QUARTER_ORDER: tuple[str, ...] = ("q1", "q2", "q3", "q4")
    DAROMAD_NAMES: tuple[str, ...] = ("Daromad",)

    QUARTER_INPUT_ORDERINGS: dict[str, tuple[str, ...]] = {
        "q1": ("1.3.2.1.2", "1.3.2.2.2", "1.3.2.3.2", "1.3.1.2"),
        "q2": ("1.4.2.1.2", "1.4.2.2.2", "1.4.2.3.2", "1.4.1.2"),
        "q3": ("1.5.2.1.2", "1.5.2.2.2", "1.5.2.3.2", "1.5.1.2"),
        "q4": ("1.6.2.1.2", "1.6.2.2.2", "1.6.2.3.2", "1.6.1.2"),
    }

    COMMON_ALLOWED_PREFIXES: tuple[str, ...] = ("1.1",)
    QUARTER_DATE_KEYS: tuple[str, ...] = ("saved_at", "sent_at", "accepted_at", "cancelled_at")

    # ----------------------------------------------------------------
    # Statement / report type checks
    # ----------------------------------------------------------------

    @classmethod
    def is_daromad_statement(cls, statement) -> bool:
        name_uz = getattr(statement, "name_uz", None)
        name = getattr(statement, "name", None)
        return name_uz in cls.DAROMAD_NAMES or name in cls.DAROMAD_NAMES

    @classmethod
    def is_daromad_report(cls, report: Report) -> bool:
        return cls.is_daromad_statement(report.statement)

    # ----------------------------------------------------------------
    # FIX: report.status ni to'g'ri hisoblash
    # ----------------------------------------------------------------

    @classmethod
    def compute_report_status(cls, report: Report) -> str:
        """
        Daromad report'ining umumiy status'ini hisoblaydi.

        Qoidasi (ustunlik tartibi):
          1. Kamida bitta ACCEPTED → report.status = ACCEPTED
          2. Kamida bitta SENT (va hech biri ACCEPTED emas) → report.status = SENT
          3. Hech biri ACCEPTED/SENT emas → report.status = SAVED
        """
        has_sent = False
        for q in cls.QUARTER_ORDER:
            quarter_num = q[-1]
            status = getattr(report, f"quarter_{quarter_num}_status", None)
            if status == Report.StatusChoices.ACCEPTED:
                return Report.StatusChoices.ACCEPTED
            if status == Report.StatusChoices.SENT:
                has_sent = True
        return Report.StatusChoices.SENT if has_sent else Report.StatusChoices.SAVED

    # ----------------------------------------------------------------
    # Validation
    # ----------------------------------------------------------------

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
            "id", "ordering", "title", "title_uz",
            "is_organization", "status_plan",
        )

        found_ids = {str(c.id) for c in columns}
        requested_ids = {str(cid) for cid in column_ids}
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
            if allow_common and any(
                column.ordering.startswith(prefix)
                for prefix in cls.COMMON_ALLOWED_PREFIXES
            ):
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

    # ----------------------------------------------------------------
    # Quarter ordering helpers
    # ----------------------------------------------------------------

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
        for q in cls.QUARTER_ORDER:
            quarter_num = q[-1]
            status = getattr(report, f"quarter_{quarter_num}_status", None)
            if status != Report.StatusChoices.ACCEPTED:
                return q
        return None

    @classmethod
    def get_quarter_access_info(cls, report: Report) -> QuarterAccessInfo:
        next_quarter = cls.get_next_available_quarter(report)
        current_quarter = report.current_quarter or next_quarter

        can_create = cls.is_daromad_report(report) and next_quarter == "q1"
        can_update = (
            cls.is_daromad_report(report)
            and next_quarter is not None
            and next_quarter != "q1"
        )

        return QuarterAccessInfo(
            current_quarter=current_quarter,
            next_available_quarter=next_quarter,
            can_create=can_create,
            can_update=can_update,
        )

    # ----------------------------------------------------------------
    # FIX: prepare_report_for_create va prepare_report_for_update
    # ----------------------------------------------------------------

    @classmethod
    def prepare_report_for_create(cls, *, report: Report, quarter: str) -> None:
        """
        Q1 create paytida chaqiriladi.
        Q1 hali ACCEPTED emas → report.status = SAVED.
        """
        if not cls.is_daromad_report(report):
            return

        report.quarter = quarter
        report.current_quarter = quarter

        # Q1 status
        if quarter == "q1" and not report.quarter_1_status:
            report.quarter_1_status = Report.StatusChoices.SAVED

        # report.status — hech qanday quarter ACCEPTED emas → SAVED
        report.status = cls.compute_report_status(report)

        cls.mark_quarter_saved(report, quarter)

    @classmethod
    def prepare_report_for_update(cls, *, report: Report, quarter: str) -> None:
        """
        QN update paytida chaqiriladi (N >= 2).

        FIX:
        - Joriy quarter'ning status_field'ini SAVED qilamiz.
        - report.status'ni compute_report_status() orqali hisoblaymiz.
          Bu Q1=ACCEPTED bo'lsa report.status=ACCEPTED bo'lib qolishini kafolatlaydi.
        - Oldingi quarter statuslariga TEGMAYMIZ.
        """
        if not cls.is_daromad_report(report):
            return

        report.quarter = quarter
        report.current_quarter = quarter

        # Joriy quarter'ni SAVED qilamiz
        status_field = cls.get_quarter_status_field(quarter)
        setattr(report, status_field, Report.StatusChoices.SAVED)

        # FIX: report.status = kamida bitta ACCEPTED bor → ACCEPTED, aks holda SAVED
        report.status = cls.compute_report_status(report)

        cls.mark_quarter_saved(report, quarter)

    # ----------------------------------------------------------------
    # Quarter status field helpers
    # ----------------------------------------------------------------

    @classmethod
    def get_quarter_status_field(cls, quarter: str) -> str:
        return f"quarter_{quarter[-1]}_status"

    @classmethod
    def get_previous_quarter(cls, quarter: str) -> Optional[str]:
        if quarter not in cls.QUARTER_ORDER:
            return None
        idx = cls.QUARTER_ORDER.index(quarter)
        return cls.QUARTER_ORDER[idx - 1] if idx > 0 else None

    @classmethod
    def get_quarter_display(cls, quarter: str) -> str:
        return dict(Report.QuarterChoices.choices).get(quarter, quarter)

    # ----------------------------------------------------------------
    # Quarter status dates
    # ----------------------------------------------------------------

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
        payload = report.quarter_status_dates or {}
        normalized = {}
        for quarter in cls.QUARTER_ORDER:
            q_data = payload.get(quarter) or {}
            normalized[quarter] = {
                "saved_at": q_data.get("saved_at"),
                "sent_at": q_data.get("sent_at"),
                "accepted_at": q_data.get("accepted_at"),
                "cancelled_at": q_data.get("cancelled_at"),
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
            return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return value

    @classmethod
    def _validate_quarter_required(cls, quarter: str | None) -> None:
        if not quarter:
            raise ValidationError({
                "quarter": _("Daromad hisobotida chorak majburiy.")
            })
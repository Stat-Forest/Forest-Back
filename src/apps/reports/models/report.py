from django.conf import settings
from django.db import models, transaction
from django.db.models import Q, TextChoices
from django.db.models.constraints import UniqueConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.base.models import AbstractBaseModel
from apps.reports.choices import UserRoleChoices
from apps.utils.services import RegionChoices


def default_quarter_status_dates():
    return {
        "q1": {"saved_at": None, "sent_at": None, "accepted_at": None, "cancelled_at": None},
        "q2": {"saved_at": None, "sent_at": None, "accepted_at": None, "cancelled_at": None},
        "q3": {"saved_at": None, "sent_at": None, "accepted_at": None, "cancelled_at": None},
        "q4": {"saved_at": None, "sent_at": None, "accepted_at": None, "cancelled_at": None},
    }


class Report(AbstractBaseModel):
    """
    Hisobot modeli.

    Asosiy qoidalar:
    - Har bir tashkilot uchun bitta statement + deadline + season kombinatsiyasi bo'lishi mumkin
      (is_individual_general=False bo'lganda UniqueConstraint ishlaydi).
    - Daromad hisobotlari uchun qo'shimcha chorak (quarter) logikasi mavjud.
    - Chorakka oid business-logika serializer/service qatlamida boshqariladi.
    """

    class StatusChoices(models.TextChoices):
        SAVED = "saved", _("Saved")
        SENT = "sent", _("Sent")
        CANCELLED = "cancelled", _("Cancelled")
        ACCEPTED = "accepted", _("Accepted")

    class TimeStatus(models.TextChoices):
        ON_TIME = "on_time", _("Bajarilgan")
        LATE = "late", _("Kechiktirilgan")

    class ReportSeasonChoices(TextChoices):
        SPRING = "spring", "Bahorgi"
        AUTUMN = "autumn", "Kuzgi"

    class QuarterChoices(TextChoices):
        Q1 = "q1", "I-chorak"
        Q2 = "q2", "II-chorak"
        Q3 = "q3", "III-chorak"
        Q4 = "q4", "IV-chorak"

    republic = models.ForeignKey(
        "general.Republic",
        on_delete=models.PROTECT,
        related_name="reports",
        blank=True,
        null=True,
    )
    organization = models.ForeignKey(
        "general.Organization",
        on_delete=models.PROTECT,
        verbose_name=_("Organization"),
        related_name="reports",
        db_index=True,
        blank=True,
        null=True,
    )
    statement = models.ForeignKey(
        "reports.Statement",
        on_delete=models.PROTECT,
        verbose_name=_("Statement"),
        related_name="reports",
    )
    deadline = models.ForeignKey(
        "reports.Deadline",
        on_delete=models.PROTECT,
        verbose_name=_("Deadline"),
        related_name="reports",
    )
    source_report = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text=_("Agar bu hisobot boshqa hisobotdan nusxa ko'chirilgan bo'lsa, asl hisobot"),
    )

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.SAVED,
        verbose_name=_("Status"),
        db_index=True,
    )
    cancel_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Cancel reason"),
        help_text=_("Reason for cancelling the report"),
    )
    sent_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    accepted_at = models.DateTimeField(blank=True, null=True)

    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False,
        related_name="reports_sent_by",
    )
    sent_by_org = models.ForeignKey(
        "general.Organization",
        on_delete=models.PROTECT,
        verbose_name=_("Sent by organization"),
        related_name="sent_by_reports",
        db_index=True,
        null=True,
        blank=True,
    )
    sent_by_role = models.CharField(
        choices=UserRoleChoices.choices,
        max_length=50,
        null=True,
        blank=True,
    )

    is_general = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Umumiy (konsolidatsiya) hisobot"),
    )
    is_individual_general = models.BooleanField(
        default=False,
        help_text=_("Tashkilot bo'yicha individual umumiy hisobot (UniqueConstraint dan ozod)"),
    )
    is_report = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Haqiqiy hisobot (False bo'lsa qoralama/loyiha)"),
    )
    is_republic = models.BooleanField(
        default=False,
        help_text=_("Respublika darajasidagi hisobot"),
    )
    is_plant_based = models.BooleanField(
        default=False,
        help_text=_("O'simlik yaratish bilan bog'liq hisobot"),
    )

    region = models.CharField(
        max_length=50,
        choices=RegionChoices.choices,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Viloyatni to'g'ridan-to'g'ri bog'lash uchun"),
    )
    time_status = models.CharField(
        max_length=20,
        choices=TimeStatus.choices,
        blank=True,
        null=True,
    )
    report_season = models.CharField(
        max_length=10,
        choices=ReportSeasonChoices.choices,
        blank=True,
        null=True,
    )
    foot_note = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Foydalanuvchi tomonidan kiritilgan izoh"),
    )

    # Faqat Daromad uchun ishlatiladi
    quarter = models.CharField(
        max_length=2,
        choices=QuarterChoices.choices,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Hisobot qaysi chorak uchun ekanligi (faqat Daromad uchun)"),
    )
    quarter_1_status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.SAVED,
        blank=True,
        null=True,
    )
    quarter_2_status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        blank=True,
        null=True,
    )
    quarter_3_status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        blank=True,
        null=True,
    )
    quarter_4_status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        blank=True,
        null=True,
    )
    current_quarter = models.CharField(
        max_length=2,
        choices=QuarterChoices.choices,
        blank=True,
        null=True,
    )

    quarter_status_dates = models.JSONField(
        default=default_quarter_status_dates,
        blank=True,
        verbose_name="Quarter status dates",
    )

    def clean(self):
        """
        Model-level business validation bu yerda qilinmaydi.
        Daromad quarter workflow service/serializer qatlamida boshqariladi.
        """
        super().clean()

    def save(self, *args, **kwargs):
        """
        Save minimal bo'lishi kerak.
        Quarter defaultlarini bu yerda emas, service qatlamida boshqaramiz.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_daromad(self) -> bool:
        """
        Hozircha name_uz / name orqali tekshiradi.
        Keyinroq slug yoki code ga o'tkazish tavsiya etiladi.
        """
        statement_name_uz = getattr(self.statement, "name_uz", None)
        statement_name = getattr(self.statement, "name", None)
        return statement_name_uz == "Daromad" or statement_name == "Daromad"

    def get_quarter_status(self, quarter: str) -> str | None:
        """
        Berilgan chorak ('q1'..'q4') uchun status qiymatini qaytaradi.
        """
        if not quarter or len(quarter) < 2:
            return None

        quarter_num = quarter[-1]
        status_field = f"quarter_{quarter_num}_status"
        return getattr(self, status_field, None)

    @property
    def can_edit_current_quarter(self) -> bool:
        """
        Backward compatibility uchun qoldirilgan.
        Bu faqat current_quarter statusiga qaraydi.
        To'liq workflow logika DaromadQuarterService ichida boshqariladi.
        """
        if not self.is_daromad or not self.current_quarter:
            return False

        current_status = self.get_quarter_status(self.current_quarter)
        return current_status not in (
            self.StatusChoices.SENT,
            self.StatusChoices.ACCEPTED,
        )

    def cancel(self, reason: str) -> None:
        """
        Hisobotni bekor qiladi.
        Agar oldingi holat ACCEPTED bo'lsa, umumiy hisobot qayta hisoblanadi.
        """
        if not reason or not reason.strip():
            raise ValueError("Bekor qilish sababi majburiy va bo'sh bo'lmasligi kerak.")

        prev_status = self.status

        with transaction.atomic():
            self.status = Report.StatusChoices.CANCELLED
            self.cancel_reason = reason.strip()
            self.cancelled_at = timezone.now()
            self.save(update_fields=["status", "cancel_reason", "cancelled_at"])

            if prev_status == Report.StatusChoices.ACCEPTED:
                from apps.reports.services.general_report import aggregate_general_report

                aggregate_general_report(
                    statement=self.statement,
                    deadline=self.deadline,
                )

    class Meta:
        verbose_name = "Hisobot"
        verbose_name_plural = "Hisobotlar"
        ordering = ["-created_at"]
        constraints = [
            UniqueConstraint(
                fields=["organization", "statement", "deadline", "report_season"],
                condition=Q(is_individual_general=False),
                name="unique_org_statement_deadline_only_for_non_individual_general",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "statement", "status", "-created_at"]),
            models.Index(fields=["statement", "status"]),
            models.Index(fields=["organization", "status"]),
        ]
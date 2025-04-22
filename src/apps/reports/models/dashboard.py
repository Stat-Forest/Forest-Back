from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.base.models import AbstractBaseModel
from apps.general.models import Organization


class DashboardStat(AbstractBaseModel):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="dashboard_stats",
        blank=True,
        null=True,
        verbose_name=_("Organization"),
    )
    sent_reports = models.PositiveIntegerField(_("Sent Reports"), default=0)
    returned_reports = models.PositiveIntegerField(_("Returned Reports"), default=0)
    accepted_reports = models.PositiveIntegerField(_("Accepted Reports"), default=0)
    draft_reports = models.PositiveIntegerField(_("Draft Reports"), default=0)
    responsible_users = models.PositiveIntegerField(_("Responsible Users"), default=0)
    deadlines = models.PositiveIntegerField(_("Deadlines"), default=0)

    def __str__(self):
        if self.organization:
            return f"{self.organization.name} Dashboard - Sent: {self.sent_reports}, Accepted: {self.accepted_reports}"
        return f"Dashboard - Sent: {self.sent_reports}, Accepted: {self.accepted_reports}"

    class Meta:
        verbose_name = _("Dashboard Statistic")
        verbose_name_plural = _("Dashboard Statistics")
        ordering = ['-created_at']
        unique_together = ('organization',)

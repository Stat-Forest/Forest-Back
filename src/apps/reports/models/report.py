from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from apps.base.models import AbstractBaseModel
from apps.users.models import CustomUser


class Report(AbstractBaseModel):
    class StatusChoices(models.TextChoices):
        SAVED = 'saved', _('Saved')
        SENT = 'sent', _('Sent')
        CANCELLED = 'cancelled', _('Cancelled')
        ACCEPTED = 'accepted', _('Accepted')

    organization = models.ForeignKey(
        "general.Organization",
        on_delete=models.PROTECT,
        verbose_name=_("Organization"),
        related_name="reports",
        db_index=True,
        blank=True,
        null=True
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
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.SAVED,
        verbose_name=_("Status"),
        db_index=True
    )
    cancel_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Cancel reason"),
        help_text=_("Reason for cancelling the report")
    )
    sent_at = models.DateTimeField(
        blank=True,
        null=True,
    )
    cancelled_at = models.DateTimeField(
        blank=True,
        null=True,
    )
    accepted_at = models.DateTimeField(
        blank=True,
        null=True,
    )
    sent_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False,
        related_name="reports_sent_by",
    )
    sent_by_org = models.ForeignKey(
        "general.Organization",
        on_delete=models.PROTECT,
        verbose_name=_("Organization"),
        related_name="sent_by_reports",
        db_index=True,
        null=True,
        blank=True,
    )
    sent_by_role =  models.CharField(
        choices=CustomUser.Role.choices,
        max_length=50,
        help_text="Foydalanuvchining tizimdagi roli",
        null=True,
        blank=True,
    )
    is_general = models.BooleanField(
      default=False, db_index=True
    )

    # def __str__(self):
    #     return f"{self.organization.name} "

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        ordering = ['-created_at']
        unique_together = ('organization', 'statement','deadline')


{
  "deadline": "c1a56dd9-d890-43b4-a025-f5496f5a7672",
  "report_items": [
    {
      "statement_column": "b8dd26fd-a332-4a48-ba2c-7fcac3d741dc",
      "inners": [
        { "value": "bc44cdde-68a8-41ef-af84-a827722cb21b" }
      ]
    },
    {
      "statement_column": "9b8d3d19-20d7-41e2-9d38-6b5ffaf97e17",
      "inners": [
        { "value": "10" },
        { "value": "20" },
        { "value": "30" },
        { "value": "30" },
        { "value": "30" },
        { "value": "30" },
        { "value": "30" }
      ]
    },
    {
      "statement_column": "5e99bc2e-b3e0-4946-b04e-89900b1c89ee",
      "inners": [
        { "value": "Golden" },
        { "value": "Bronza" },
        { "value": "Victus" },
        { "value": "HP" },
        { "value": "ZYXEL" },
        { "value": "Lenovo" }
      ]
    },
    {
      "statement_column": "398d534e-90b5-4023-9345-275ad58d33fb",
      "inners": [
        { "value": "Golden" },
        { "value": "Bronza" },
        { "value": "Victus" },
        { "value": "HP" },
        { "value": "ZYXEL" },
        { "value": "Lenovo" }
      ]
    },
    {
      "statement_column": "b6a00914-0c5d-43ae-9ef2-861ee626d217",
      "inners": [
        { "value": "Golden" },
        { "value": "Bronza" },
        { "value": "Victus" },
        { "value": "HP" },
        { "value": "ZYXEL" },
        { "value": "Lenovo" }
      ]
    },
    {
      "statement_column": "8023a136-9b1e-46e7-bea8-e909edf236d7",
      "inners": [
        { "value": "Golden" },
        { "value": "Bronza" },
        { "value": "Victus" },
        { "value": "HP" },
        { "value": "ZYXEL" },
        { "value": "Lenovo" }
      ]
    },
    {
      "statement_column": "a731d5f9-34a8-4140-b9a8-a23024baf5b3",
      "inners": [
        { "value": "Golden" },
        { "value": "Bronza" },
        { "value": "Victus" },
        { "value": "HP" },
        { "value": "ZYXEL" },
        { "value": "Lenovo" }
      ]
    },
    {
      "statement_column": "b1f95ba9-5120-4177-8187-e36fa7e595b0",
      "inners": [
        { "value": "Golden" },
        { "value": "Bronza" },
        { "value": "Victus" },
        { "value": "HP" },
        { "value": "ZYXEL" },
        { "value": "Lenovo" }
      ]
    },
    {
      "statement_column": "7f132de4-327b-4238-a633-6eef1dc04a38",
      "inners": [
        { "value": "1" },
        { "value": "2" },
        { "value": "3" },
        { "value": "4" },
        { "value": "5" },
        { "value": "6" }
      ]
    },
    {
      "statement_column": "89ad4033-5751-44c7-a515-3def9d2aec2b",
      "inners": [
        { "value": "1" },
        { "value": "2" },
        { "value": "3" },
        { "value": "4" },
        { "value": "5" },
        { "value": "6" }
      ]
    },
    {
      "statement_column": "5d97744a-5332-4dac-b2b9-81cc331fc32c",
      "inners": [
        { "value": "1" },
        { "value": "2" },
        { "value": "3" },
        { "value": "4" },
        { "value": "5" },
        { "value": "6" }
      ]
    },
    {
      "statement_column": "feceb74b-bfa9-474b-8a9b-8bc4efd6609c",
      "inners": [
        { "value": "1" },
        { "value": "2" },
        { "value": "3" },
        { "value": "4" },
        { "value": "5" },
        { "value": "6" }
      ]
    },
    {
      "statement_column": "6632a731-5258-4038-9859-4f1a94535ac7",
      "inners": [
        { "value": "1" },
        { "value": "2" },
        { "value": "3" },
        { "value": "4" },
        { "value": "5" },
        { "value": "6" }
      ]
    },
    {
      "statement_column": "ce53935b-5581-44f2-bbcb-ef2dcb7529e5",
      "inners": [
        { "value": "1" },
        { "value": "2" },
        { "value": "3" },
        { "value": "4" },
        { "value": "5" },
        { "value": "6" }
      ]
    },
    {
      "statement_column": "80c63e4e-05d5-498d-827e-dc03b0366f4e",
      "inners": [
        { "value": "1" },
        { "value": "2" },
        { "value": "3" },
        { "value": "4" },
        { "value": "5" },
        { "value": "6" }
      ]
    },
    {
      "statement_column": "b615b1b2-168c-42fe-b2d8-3fc60f3aae9f",
      "inners": [
        { "value": "bc44cdde-68a8-41ef-af84-a827722cb21b" }
      ]
    },
    {
      "statement_column": "3b1f6e10-0cc5-4364-9963-4516ee1a0e63",
      "inners": [
        { "value": "11" },
        { "value": "22" },
        { "value": "33" }
      ]
    },
    {
      "statement_column": "bda4d460-551d-43fe-98bf-eae0c73d46f3",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "a610a653-dcd8-44d7-8e0f-3f2a6572c0e8",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "907c47a0-da07-47ef-bcd1-e73f63183c92",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "dc813e10-89e7-4e70-adb8-40b6b2bdef6e",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "ce1fd11a-2953-406c-a705-8b07946ebeee",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "3c2ae198-2ef6-40e7-bf5c-43a618e09105",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "ab6fa397-f0d7-4b2e-a5b5-62455602c04e",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "f4fb5285-4e8a-4e61-ad61-37a18956630a",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "fca7a157-8fa9-4860-b384-5a18e2167228",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "e8412601-cab9-41f8-a044-f9bf064e02f8",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "24b04d8a-a1f4-40ff-8f6a-b7b3271802b1",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "500fe73c-16e0-42de-8b34-1dfdde3ea026",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "a5a54539-d3e1-4198-8f3b-fceac98483a9",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "4152d9d3-275e-48b7-aafa-4bc965c2e6a5",
      "inners": [
        { "value": "bc44cdde-68a8-41ef-af84-a827722cb21b" }
      ]
    },
    {
      "statement_column": "9cd9297c-6e1b-4197-87ad-0a0eb28ba7a4",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "6fbe168d-387b-4781-9308-ec3e337a193a",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "a325e2ba-a850-420a-85f9-a95e25f2b7bd",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "42a656c8-d996-4649-8c42-89a52ea670cf",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "001ad561-63f5-4346-a397-6cb20457812f",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "ab32e900-016a-40c5-9aee-94d8eee289fb",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "af6a934e-9128-46ef-94c6-e7b5aac9a165",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    }
  ]
}
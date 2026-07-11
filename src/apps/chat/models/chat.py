from django.core.validators import MaxLengthValidator
from django.db import models
from django.db.models import Q

from apps.base.models import AbstractBaseModel
from apps.users.models import CustomUser


class Conversation(AbstractBaseModel):
    """
    Support conversation between a single ERP user and a support administrator.

    Lifecycle: NEW -> TAKEN -> CLOSED

    MUHIM: Holat o'tishlari (take/close) va validatsiya qoidalari (kunlik limit,
    bitta faol chat cheklovi) ATAYLAB bu yerda yozilmagan. Ular
    `apps.chat.services.conversation_services` da, `select_for_update()` +
    `transaction.atomic()` bilan birga amalga oshiriladi — chunki holat
    o'tishlarini himoyasiz (lock'siz) model metodida yozish race condition'ga
    olib keladi (masalan ikkita admin bir chatni bir vaqtda "olib qolishi").
    """

    class Status(models.TextChoices):
        NEW = "new", "New"
        TAKEN = "taken", "Taken"
        CLOSED = "closed", "Closed"

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="support_conversations",
        help_text="User who created this support conversation.",
    )
    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_support_conversations",
        help_text="Support administrator responsible for this conversation.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status,
        default=Status.NEW,
        db_index=True,
    )
    taken_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ("-last_message_at", "-created_at")
        # user/assigned_to uchun alohida index kerak emas —
        # ForeignKey Django tomonidan avtomatik index qilinadi.
        permissions = [
            ("manage_support_chat", "Can manage support chat"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status__in=["new", "taken"]),
                name="unique_active_conversation_per_user",
            ),
        ]

    def __str__(self):
        return f"Conversation #{self.pk} ({self.user})"


class Message(AbstractBaseModel):
    """
    Immutable chat message.
    Xabarni tahrirlash/o'chirish uchun API/service atayin yozilmaydi —
    shu orqali "immutable" qoidasi ta'minlanadi.
    """

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="chat_messages",
    )
    text = models.TextField(
        validators=[
            MaxLengthValidator(5000)
        ]
    )
    is_read = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["conversation", "is_read"]),
        ]

    def __str__(self):
        return f"Message #{self.pk}"
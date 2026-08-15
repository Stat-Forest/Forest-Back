from django.core.validators import MaxLengthValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Coalesce

from apps.base.models import AbstractBaseModel
from apps.users.models import CustomUser

#: Xabar matnining maksimal uzunligi. Model validatori `objects.create()` da
#: ishlamagani uchun haqiqiy tekshiruv service qatlamida shu qiymat bo'yicha
#: bajariladi (`apps.chat.services.message_services`).
MAX_MESSAGE_LENGTH = 5000

#: Chatlarni saralash tartibi: xabar yozilgan bo'lsa — oxirgi xabar vaqti,
#: yozilmagan bo'lsa — yaratilgan vaqti. Oddiy `-last_message_at` Postgres'da
#: NULL larni BIRINCHI qo'yadi, ya'ni xabarsiz eski chatlar bugungi faol
#: chatlardan yuqorida chiqib ketardi.
CONVERSATION_ACTIVITY = Coalesce("last_message_at", "created_at")


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
        ordering = (CONVERSATION_ACTIVITY.desc(), "-created_at")
        # user/assigned_to uchun alohida index kerak emas —
        # ForeignKey Django tomonidan avtomatik index qilinadi.
        constraints = [
            # Bir vaqtda faqat BITTA chat admin qo'lida bo'lishi mumkin.
            #
            # Ilgari bu constraint NEW ni ham qamrab olardi. Natijada hech kim
            # olmagan chat foydalanuvchini abadiy bloklab turardi — u kunlik
            # 2 ta limitiga umuman yetib bora olmasdi. NEW chat esa hech kimni
            # band qilmaydi (u shunchaki navbatda turadi), shuning uchun
            # "ko'pi bilan 2 ta faol chat" qoidasi service qatlamida,
            # `create_conversation` dagi qulf ostida tekshiriladi
            # (partial UNIQUE bilan "ko'pi bilan 2 ta" ni ifodalab bo'lmaydi).
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status="taken"),
                name="unique_taken_conversation_per_user",
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
            MaxLengthValidator(MAX_MESSAGE_LENGTH)
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
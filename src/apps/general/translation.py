from apps.general.models import Organization
from apps.general.models import Announcement
from apps.general.models import Notification

from modeltranslation.translator import register, TranslationOptions


@register(Organization)
class OrganizationTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(Announcement)
class AnnouncementTranslationOptions(TranslationOptions):
    fields = ('title','desc')


@register(Notification)
class NotificationTranslationOptions(TranslationOptions):
    fields = ('text',)
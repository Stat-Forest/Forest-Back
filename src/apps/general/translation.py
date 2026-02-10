from apps.general.models import Organization, Announcement, Notification,LandManagement

from modeltranslation.translator import register, TranslationOptions


@register(Organization)
class OrganizationTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Announcement)
class AnnouncementTranslationOptions(TranslationOptions):
    fields = ('title', 'desc')


@register(Notification)
class NotificationTranslationOptions(TranslationOptions):
    fields = ('text',)


@register(LandManagement)
class LandManagementTranslationOptions(TranslationOptions):
    fields = ('name',)

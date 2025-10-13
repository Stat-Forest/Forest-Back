from apps.general.models import Organization
from apps.general.models import Announcement

from modeltranslation.translator import register, TranslationOptions


@register(Organization)
class OrganizationTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(Announcement)
class AnnouncementTranslationOptions(TranslationOptions):
    fields = ('title','desc')
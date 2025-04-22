from modeltranslation.translator import register, TranslationOptions
from apps.general.models import Organization

@register(Organization)
class OrganizationTranslationOptions(TranslationOptions):
    fields = ('name',)
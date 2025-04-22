from apps.general.models import Organization
from modeltranslation.translator import register, TranslationOptions

@register(Organization)
class OrganizationTranslationOptions(TranslationOptions):
    fields = ('name',)
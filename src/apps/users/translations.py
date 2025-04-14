from modeltranslation.translator import register, TranslationOptions

from apps.users.models.users import CustomUser


@register(CustomUser)
class CustomUserTranslationOptions(TranslationOptions):
    fields = (
        "first_name",
        "last_name",
        "father_name",
        "email",
        "address",
    )

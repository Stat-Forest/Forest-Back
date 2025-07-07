from modeltranslation.translator import register, TranslationOptions

from apps.reports.models import Statement, StatementColumn, Plant, Plan


@register(Statement)
class StatementTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(StatementColumn)
class StatementColumnTranslationOptions(TranslationOptions):
    fields = ("title",)


@register(Plant)
class PlantTranslationOptions(TranslationOptions):
    fields = ("name",)
from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from apps.general.models import Organization


@admin.register(Organization)
class OrganizationAdmin(TranslationAdmin):
    list_display = ('name',)
from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from django.utils.translation import gettext_lazy as _

from apps.general.models import LandManagement


@admin.register(LandManagement)
class LandManagementAdmin(TranslationAdmin):
    list_display = ('name', 'area', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'comment')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {
            'fields': ('name', 'area', 'comment')
        }),
        (_("Qo‘shimcha ma’lumot"), {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('created_at',)



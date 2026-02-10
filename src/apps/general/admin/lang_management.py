from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from django.utils.translation import gettext_lazy as _

from apps.general.models import LandManagement


@admin.register(LandManagement)
class LandManagementAdmin(TranslationAdmin):
    list_display = ('name_uz', 'name_ru', 'area_pretty', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name_uz', 'name_ru', 'comment')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {
            'fields': (
                'name_uz', 'name_ru',
                'area', 'comment'
            )
        }),
        (_("Qo‘shimcha ma’lumot"), {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('created_at',)

    def area_pretty(self, obj):
        # 3.050 -> 3.05, 881.000 -> 881
        return obj.area.normalize()

    area_pretty.short_description = _("Area (mln ga)")

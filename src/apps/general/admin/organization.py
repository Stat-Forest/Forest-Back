from django.contrib import admin, messages
from modeltranslation.admin import TranslationAdmin
from django.utils.translation import gettext_lazy as _

from apps.general.models import Organization


@admin.register(Organization)
class OrganizationAdmin(TranslationAdmin):
    list_display = ('name','name_uz','name_ru','region')
    list_filter = list_display
    search_fields = list_display

    def save_model(self, request, obj, form, change):
        if Organization.objects.exclude(pk=obj.pk).filter(name=obj.name).exists():
            self.message_user(request, _("An organization with this name already exists."), level=messages.ERROR)
            return
        super().save_model(request, obj, form, change)
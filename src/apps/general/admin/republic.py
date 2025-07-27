from django.contrib import admin
from django.contrib.admin import ModelAdmin

from apps.general.models import Republic


@admin.register(Republic)
class RepublicAdmin(ModelAdmin):
    list_display = ("id", "name")
    list_display_links = list_display
    list_filter = list_display
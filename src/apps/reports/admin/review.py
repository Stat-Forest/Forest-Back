from django.contrib import admin

from apps.reports.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    pass
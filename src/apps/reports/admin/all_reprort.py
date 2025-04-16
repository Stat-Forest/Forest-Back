from django.contrib import admin

from apps.reports.models.all_report import AllReport


@admin.register(AllReport)
class AllReportAdmin(admin.ModelAdmin):
    list_display = ('title','count')
    search_fields = ('title',)


from django.contrib import admin

from apps.reports.models.all_reviews import AllReview


@admin.register(AllReview)
class AllReportAdmin(admin.ModelAdmin):
    list_display = ('title','count')
    search_fields = ('title',)


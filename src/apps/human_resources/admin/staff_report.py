from django.contrib import admin
from ..models import StaffReport

@admin.register(StaffReport)
class StaffReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'report',
        'all_workers',
        'management_workers',
        'expert_workers',
        'production_workers',
        'technical_workers',
        'service_workers',
        'workers',
        'all_vacancies',
        'total_staff_positions',
        'higher_education',
        'secondary_education',
        'general_education',
        'females',
        'males',
        'retired_workers',
        'created_at',
    )

    list_filter = (
        'report__organization',
        'report__statement',
        'created_at',
        'updated_at',
    )

    search_fields = (
        'report__organization__name',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    fieldsets = (
        ('Report bilan bog‘lanish', {
            'fields': ('report',)
        }),
        ('Xodimlar', {
            'fields': (
                'all_workers',
                'management_workers',
                'expert_workers',
                'production_workers',
                'technical_workers',
                'service_workers',
                'workers',
            )
        }),
        ('Bo‘sh ish o‘rinlari', {
            'fields': (
                'all_vacancies',
                'management_vacancies',
                'expert_vacancies',
                'technical_vacancies',
                'service_vacancies',
                'vacancies',
            )
        }),
        ('Shtatlar va Ta’lim', {
            'fields': (
                'total_staff_positions',
                'total_number_employed_staff',
                'higher_education',
                'secondary_education',
                'general_education',
            )
        }),
        ('Jins va yosh', {
            'fields': (
                'females',
                'males',
                'girls',
                'boys',
                'girls_under_30',
                'boys_under_30',
            )
        }),
        ('Qo‘shimcha ko‘rsatkichlar', {
            'fields': (
                'retired_workers',
                'academic_degrees',
                'foreign_language_employees',
                'educated_and_trained_abroad',
                'total_number_new_jobs_created',
                'permanent_workers',
                'seasonal_workers',
                'included_iron_book_women_list',
                'from_low_income_families',
                'based_home_based_work',
            )
        }),
        ('Vaqt ma’lumotlari', {
            'fields': ('created_at', 'updated_at')
        }),
    )

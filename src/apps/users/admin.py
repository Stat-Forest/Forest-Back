from django.contrib import admin

from apps.users.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    model = CustomUser
    list_display = ('email', 'first_name', 'is_staff', 'is_superuser')
    ordering = ('email',)
    search_fields = ('email', 'first_name', 'last_name')
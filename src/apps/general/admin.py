from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Organization


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name','get_region_display', 'created_at', 'updated_at')
    list_filter = ('region',)
    search_fields = ('name',)

    def get_region_display(self, obj):
        return obj.get_region_display()

    get_region_display.admin_order_field = 'region'
    get_region_display.short_description = _('Region')

admin.site.register(Organization, OrganizationAdmin)

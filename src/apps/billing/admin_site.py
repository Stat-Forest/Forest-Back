"""
Ijara billing adminkasi — `/billing-admin/` (stat `admin_site`dan alohida).

Jazzmin brendi global `JAZZMIN_SETTINGS`dan olinadi (site_header/site_brand
sozlangan bo'lsa AdminSite qiymatlari e'tiborga olinmaydi), shuning uchun
`each_context` orqali `is_billing_admin` beriladi va `templates/admin/base_site.html`
hamda `templates/billing_admin/*.html` sarlavhani "Ijara billing boshqaruvi"ga almashtiradi.
"""
from urllib.parse import urlencode

from django.contrib import admin
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import redirect
from django.urls import reverse

BILLING_ADMIN_HEADER = "Ijara billing boshqaruvi"


class BillingAdminSite(admin.AdminSite):
    site_header = BILLING_ADMIN_HEADER
    site_title = "Ijara billing — boshqaruv paneli"
    index_title = "Ijara billing — boshqaruv paneli"
    index_template = "billing_admin/index.html"
    login_template = "billing_admin/login.html"

    def each_context(self, request):
        context = super().each_context(request)
        context["is_billing_admin"] = True
        context["billing_admin_header"] = BILLING_ADMIN_HEADER
        return context

    def login(self, request, extra_context=None):
        # Jazzmin login formasida `next` yashirin maydoni yo'q: login sahifasi
        # to'g'ridan ochilsa Django LOGIN_REDIRECT_URL (/accounts/profile/)ga
        # yuboradi. `next`ni URL'ga qo'shib, formaning action'iga o'tkazamiz.
        if request.method == "GET" and REDIRECT_FIELD_NAME not in request.GET:
            index_url = reverse(f"{self.name}:index", current_app=self.name)
            return redirect(f"{request.path}?{urlencode({REDIRECT_FIELD_NAME: index_url})}")
        return super().login(request, extra_context)


billing_admin_site = BillingAdminSite(name="billing_admin")

from django.conf import settings
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.contrib.admin.views.decorators import staff_member_required

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.base.admin import admin_site
from apps.general.protected_media import ProtectedMediaView

urlpatterns = [
    path("admin/", admin_site.urls),
    # API hujjatlari faqat admin uchun (SPECTACULAR_SETTINGS["SERVE_PERMISSIONS"]).
    # Sahifalar login'siz ochilsa admin login'ga yo'naltiradi.
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('', staff_member_required(SpectacularSwaggerView.as_view(url_name='schema'), login_url='forest_admin:login'), name='swagger-ui'),
    path('api/redoc/', staff_member_required(SpectacularRedocView.as_view(url_name='schema'), login_url='forest_admin:login'), name='redoc'),

    path("api/v1/authentications/", include("apps.authentications.urls")),
    path("api/v1/users/", include("apps.users.urls")),
    path("api/v1/e_imzo/", include("apps.e_imzo.urls")),


]

# Himoyalangan media: imzolangan ?t= token yoki admin sessiyasi bilan.
# static() dan oldin turishi shart (DEBUG'da static() hamma /media/ ni beradi).
urlpatterns += [
    re_path(r"^media/(?P<path>(documents|resumes|handbooks)/.+)$", ProtectedMediaView.as_view(), name="protected-media"),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ================ Oybek`s URLS ================

urlpatterns += [
    path('api/v1/reports/', include('apps.reports.urls')),
    path('api/v1/general/', include('apps.general.urls')),
    path('api/v1/report_admin_stat/', include('apps.report_admin_stat.urls')),
    path("api/v1/information-analytical/", include('apps.information_analytical.urls')),
    path('api/v1/sum/', include('apps.sum.urls')),
    path('api/v1/statistics/', include('apps.report_statistics.urls')),
    path('api/v1/chats/', include('apps.chat.urls')),
    path('api/v1/billing/', include('apps.billing.urls')),
    # path('api/v1/ai/', include('apps.ai.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

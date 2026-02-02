from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    path("api/v1/authentications/", include("apps.authentications.urls")),
    path("api/v1/users/", include("apps.users.urls")),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ================ Oybek`s URLS ================

urlpatterns += [
    path('api/v1/reports/', include('apps.reports.urls')),
    path('api/v1/general/', include('apps.general.urls')),
    path('api/v1/analysis/', include('apps.info_analysis.urls')),
    path('api/v1/sum/', include('apps.sum.urls')),
    path('api/v1/statistics/', include('apps.report_statistics.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

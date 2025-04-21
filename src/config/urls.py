import random

from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from . import settings
from .yasg import schema_view

urlpatterns = [
    path("admin/", admin.site.urls),

    path('', schema_view.with_ui('swagger', cache_timeout=0), name='yasg-swagger'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='yasg-redoc'),
    path("api/v1/authentications/", include("apps.authentications.urls"))

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ================ Oybek`s URLS ================


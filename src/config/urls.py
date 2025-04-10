from django.contrib import admin
from django.urls import path

from .yasg import schema_view

urlpatterns = [
    path("admin/", admin.site.urls),

    path('', schema_view.with_ui('swagger', cache_timeout=0), name='yasg-swagger'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='yasg-redoc'),

]

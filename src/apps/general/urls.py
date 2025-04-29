from django.urls import path

from apps.general.views.organization import OrganizationListAPIView

urlpatterns = [
    path('organization/', OrganizationListAPIView.as_view(), name='organization-list'),
]

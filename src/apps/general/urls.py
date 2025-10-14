from django.urls import path

from apps.general.views.organization import OrganizationListAPIView
from apps.general.views.announcement import AnnouncementListAPIView

urlpatterns = [
    path('organization/', OrganizationListAPIView.as_view(), name='organization-list'),
    path('announcements/', AnnouncementListAPIView.as_view(), name='announcement-list'),
]

from django.urls import path

from apps.general.views.organization import OrganizationListAPIView
from apps.general.views.announcement import AnnouncementListAPIView
from apps.general.views.notification  import NotificationListCreateAPIView

urlpatterns = [
    path('organization/', OrganizationListAPIView.as_view(), name='organization-list'),
    path('announcements/', AnnouncementListAPIView.as_view(), name='announcement-list'),
    path("notifications/", NotificationListCreateAPIView.as_view(), name="notification-list"),
]

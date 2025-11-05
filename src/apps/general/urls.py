from django.urls import path

from apps.general.views.organization import OrganizationListAPIView
from apps.general.views.announcement import AnnouncementListAPIView
from apps.general.views.notification  import NotificationListCreateAPIView
from apps.general.views.land_document import LandDocumentListCreateView

urlpatterns = [
    path('organization/', OrganizationListAPIView.as_view(), name='organization-list'),
    path('announcements/', AnnouncementListAPIView.as_view(), name='announcement-list'),
    path("notifications/", NotificationListCreateAPIView.as_view(), name="notification-list"),
    path("land-documents/", LandDocumentListCreateView.as_view(), name="land-document-list-create"),
]

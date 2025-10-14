from apps.general.models import Announcement
from apps.general.serializers import AnnouncementListSerializer
from django.utils import timezone
from rest_framework import generics

from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Announcement"])
class AnnouncementListAPIView(generics.ListAPIView):
    serializer_class = AnnouncementListSerializer
    filterset_fields=['title']

    def get_queryset(self):
        now = timezone.now()
        return Announcement.objects.filter(from_time__lte=now, to_time__gte=now).order_by('ordering')
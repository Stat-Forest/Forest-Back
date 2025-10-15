from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import generics
from django.utils import timezone
from apps.general.models import Announcement
from apps.general.serializers import AnnouncementListSerializer


@extend_schema(
    tags=["Announcement"],
    parameters=[
        OpenApiParameter(
            name='lang',
            description='Tilni tanlang (uz yoki ru)',
            required=False,
            type=str,
            enum=['uz', 'ru'],
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class AnnouncementListAPIView(generics.ListAPIView):
    serializer_class = AnnouncementListSerializer
    filterset_fields = ['title']

    def get_queryset(self):
        now = timezone.now()
        return Announcement.objects.filter(
            from_time__lte=now, to_time__gte=now
        ).order_by('ordering')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['lang'] = self.request.query_params.get('lang', 'uz')
        return context

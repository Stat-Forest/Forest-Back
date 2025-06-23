from rest_framework import generics

from drf_spectacular.utils import extend_schema
from django_filters import rest_framework as filters

from apps.users.models import CustomUser
from apps.general.models import Organization
from apps.reports.serializers import UserListSerializer
from apps.reports.filters import CustomUserFilter



@extend_schema(tags=["Users"])
class UserListAPIView(generics.ListAPIView):
    queryset = CustomUser.objects.prefetch_related("organization")
    serializer_class = UserListSerializer
    filterset_class = CustomUserFilter






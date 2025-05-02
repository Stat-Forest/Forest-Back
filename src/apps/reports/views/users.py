from rest_framework import generics
from drf_spectacular.utils import extend_schema

from apps.users.models import CustomUser
from apps.reports.serializers import UserListSerializer

@extend_schema(tags=["Users"])
class UserListAPIView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserListSerializer
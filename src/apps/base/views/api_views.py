from rest_framework import views
from rest_framework.permissions import IsAuthenticated

from apps.base.serializers import EmptySerializer


class BaseAPIView(views.APIView):
    """
    BaseAPIView permissions.

    Throttling note:
    Global throttle faqat AnonRateThrottle (noma'lum foydalanuvchilar).
    Xavfli endpointlar (login, AI) o'z throttle klasslari bilan himoyalangan.
    Report CRUD operatsiyalari uchun throttle qo'yilmagan,
    chunki authenticated foydalanuvchilar ko'p parallel so'rov yuboradi.
    """
    permission_classes = [IsAuthenticated]

    serializer_class = EmptySerializer
    queryset = []


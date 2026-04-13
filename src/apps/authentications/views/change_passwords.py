from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.authentications.serializers import ChangePasswordSerializer
from apps.base.views import CustomGenericAPIView


@extend_schema(tags=["authentications"])
class ChangePasswordAPIView(CustomGenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Parol muvaffaqiyatli o‘zgartirildi."},
            status=200
        )
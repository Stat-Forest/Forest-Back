import random

from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.general.models import Organization
from apps.users.models import CustomUser
from apps.e_imzo.serializers import EimzoLoginSerializer
from apps.e_imzo.services import verify_pkcs7
from apps.e_imzo.utils import split_full_name

User = get_user_model()


class EimzoJWTLoginView(APIView):

    def post(self, request):
        serializer = EimzoLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vo = serializer.validated_data.get("vo") or {}
        pkcs7 = serializer.validated_data["pkcs7"]

        if not verify_pkcs7(pkcs7, vo):
            return Response(
                {"detail": "Imzo noto‘g‘ri yoki noto‘liq."},
                status=status.HTTP_400_BAD_REQUEST
            )

        full_name = vo.get("CN", "")
        uid = vo.get("UID") or str(random.randint(100000, 999999))
        pinfl = vo.get("PINFL", "")
        legal_stir = vo.get("TIN", "")

        first_name, last_name, father_name = split_full_name(full_name)
        email = f"{uid}@example.com"

        organization = Organization.objects.filter(stir=legal_stir).first()
        if not organization:
            return Response(
                {"detail": "Tashkilot topilmadi"},
                status=status.HTTP_404_NOT_FOUND
            )

        user, _ = User.objects.update_or_create(
            email=email,
            defaults={
                "tin": legal_stir,
                "full_name": full_name,
                "first_name": first_name,
                "last_name": last_name,
                "father_name": father_name,
                "pinfl": pinfl,
                "organization": organization,
                "is_active": True,
                "role": CustomUser.Role.TASHKILOT_RAHBARI,
            }
        )

        user.set_password(uid)
        user.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "email": email,
                "role": user.role,
                "user_id": user.id,
            },
            status=status.HTTP_200_OK
        )

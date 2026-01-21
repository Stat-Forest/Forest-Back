import random
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import EimzoLoginSerializer
from .services import verify_pkcs7
from apps.general.models import Organization
from apps.users.models import CustomUser



User = get_user_model()


def split_full_name(full_name: str):
    """F.I.Sh bo‘lib ajratadi"""
    parts = full_name.strip().split()

    first_name, last_name, father_name = "", "", ""

    if len(parts) == 1:
        last_name = parts[0]
    elif len(parts) == 2:
        first_name, last_name = parts
    elif len(parts) >= 3:
        first_name, last_name, father_name = parts[:3]

    return first_name, last_name, father_name


class EimzoJWTLoginView(APIView):
    def post(self, request):
        serializer = EimzoLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pkcs7 = serializer.validated_data["pkcs7"]

        # 🔒 Faqat PKCS7 ga ishonamiz
        cert_data = verify_pkcs7(pkcs7)
        if not cert_data:
            return Response(
                {"detail": "Imzo noto‘g‘ri yoki bekor qilingan"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ❌ vo = serializer.validated_data["vo"] → IGNORE

        full_name = cert_data["CN"]
        first_name, last_name, father_name = split_full_name(full_name)

        uid = cert_data["UID"] or str(random.randint(100000, 999999))
        pinfl = cert_data["PINFL"]
        legal_stir = cert_data["TIN"]

        email = f"{uid}@eimzo.local"

        organization = None
        if legal_stir:
            organization = Organization.objects.filter(stir=legal_stir).first()
            if not organization:
                return Response(
                    {"detail": gettext_lazy("Tashkilot topilmadi")},
                    status=404
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

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "email": email,
            "role": user.role,
            "user_id": user.id
        })

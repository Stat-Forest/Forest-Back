# apps/e_imzo/views.py
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

        pkcs7 = serializer.validated_data["pkcs7"]
        frontend_vo = serializer.validated_data.get("vo") or {}

        # 1️⃣ Avval E-IMZO serverdan VO olishga harakat qilamiz
        vo = verify_pkcs7(pkcs7)

        # 2️⃣ Agar e-imzo ishlamasa → frontend VO
        if not vo:
            vo = frontend_vo

        # 3️⃣ Agar baribir VO bo‘lmasa → xato
        if not vo:
            return Response(
                {"detail": "VO olinmadi (pkcs7 ham, frontend vo ham yo‘q)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4️⃣ VO dan ma’lumotlar
        full_name = vo.get("CN", "")
        uid = vo.get("UID") or str(random.randint(100000, 999999))
        pinfl = vo.get("PINFL", "")
        legal_stir = vo.get("TIN", "")

        if not legal_stir:
            return Response(
                {"detail": "TIN topilmadi"},
                status=status.HTTP_400_BAD_REQUEST
            )

        first_name, last_name, father_name = split_full_name(full_name)
        email = f"{uid}@eimzo.local"

        # 5️⃣ Organization
        organization = Organization.objects.filter(stir=legal_stir).first()
        if not organization:
            return Response(
                {"detail": "Tashkilot topilmadi"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 6️⃣ User create/update
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

        # 7️⃣ JWT
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user_id": user.id,
                "email": user.email,
                "role": user.role,
            },
            status=status.HTTP_200_OK
        )

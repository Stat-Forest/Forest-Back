import random

from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction

from apps.general.models import Organization
from apps.users.models import CustomUser
from apps.e_imzo.serializers import EimzoLoginSerializer
from apps.e_imzo.services import verify_pkcs7
from apps.e_imzo.utils import split_full_name
from apps.logs.models import HistoryActionJournal

User = get_user_model()


class EimzoJWTLoginView(APIView):
    """
    E-imzo orqali kirish - PINFL asosida dublikat yaratilmaydi.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EimzoLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vo = serializer.validated_data.get("vo") or {}
        pkcs7 = serializer.validated_data["pkcs7"]

        # Imzoni tekshirish
        if not verify_pkcs7(pkcs7, vo):
            return Response(
                {"detail": "Imzo noto'g'ri yoki noto'liq."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # E-imzodan ma'lumotlar
        full_name = vo.get("CN", "")
        pinfl = vo.get("PINFL", "")
        legal_stir = vo.get("TIN", "")
        uid = vo.get("UID") or str(random.randint(100000, 999999))

        # PINFL majburiy
        if not pinfl:
            return Response(
                {"detail": "PINFL ma'lumoti topilmadi"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ism ajratish
        first_name, last_name, father_name = split_full_name(full_name)

        # Tashkilot topish
        organization = Organization.objects.filter(stir=legal_stir).first()
        if not organization:
            return Response(
                {"detail": f"STIR {legal_stir} bo'yicha tashkilot topilmadi"},
                status=status.HTTP_404_NOT_FOUND
            )

        # ========================================================================
        # ASOSIY LOGIKA: PINFL bo'yicha qidirish - DUBLIKAT YARATILMAYDI
        # ========================================================================
        with transaction.atomic():
            user = User.objects.filter(pinfl=pinfl).first()

            if user:
                # ============================================================
                # MAVJUD USER - faqat yangilaymiz
                # ============================================================
                created = False

                user.tin = legal_stir
                user.full_name = full_name
                user.first_name = first_name
                user.last_name = last_name
                if father_name:
                    user.father_name = father_name
                user.organization = organization
                user.is_active = True

                # Role yangilash (faqat agar hozirgi role past darajali bo'lsa)
                if user.role == CustomUser.Role.TASHKILOT_HODIMI or not user.role:
                    user.role = CustomUser.Role.TASHKILOT_RAHBARI

            else:
                # ============================================================
                # YANGI USER - yaratamiz
                # ============================================================
                created = True

                # Noyob email
                email = f"eimzo_{pinfl}@system.uz"

                # Majburiy fieldlar uchun default qiymatlar
                user_data = {
                    'email': email,
                    'pinfl': pinfl,
                    'tin': legal_stir,
                    'full_name': full_name,
                    'first_name': first_name,
                    'last_name': last_name,
                    'father_name': father_name or '',
                    'organization': organization,
                    'is_active': True,
                    'role': CustomUser.Role.TASHKILOT_RAHBARI,
                    # Majburiy fieldlar
                    'passport_number': 'AA0000000',  # Placeholder
                    'date_of_place': '',
                    'address': '',
                }

                # Agar gender majburiy bo'lsa
                try:
                    user = User(**user_data)
                except Exception as e:
                    # Gender yoki boshqa field majburiy bo'lsa
                    user_data['gender'] = CustomUser.Gender.MALE
                    user = User(**user_data)

            # Parol o'rnatish
            user.set_password(uid)
            user.save()

        # Log yozish
        if created:
            HistoryActionJournal.objects.create(
                user=user,
                action="add",
                model_name="CustomUser",
                object_repr=str(user),
                object_id=str(user.id),
                change_message=f"E-imzo: yangi user. PINFL: {pinfl}"
            )

        HistoryActionJournal.objects.create(
            user=user,
            action="login",
            model_name="CustomUser",
            object_repr=str(user),
            object_id=str(user.id),
            change_message=f"E-imzo login {'(birinchi marta)' if created else ''}"
        )

        # JWT token
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "email": user.email,
                "role": user.role,
                "user_id": user.id,
                "full_name": user.full_name,
                "organization": organization.name,
                "first_login": created,
            },
            status=status.HTTP_200_OK
        )
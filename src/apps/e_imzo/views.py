# src/apps/e_imzo/views.py
from rest_framework import views, permissions, exceptions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import CustomUser
from apps.general.models import Organization
from .services import EimzoServiceApi

eimzo_api = EimzoServiceApi()

from drf_spectacular.utils import extend_schema



@extend_schema(
    tags=["E-imzo"]
)
class EimzoChallengeView(views.APIView):
    """
    Frontend shu endpoint orqali challenge oladi,
    keyin uni E-Imzo kutubxonasi bilan imzolaydi.
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        ok, status_code, data = eimzo_api.eri_challenge(request)
        if not ok:
            raise exceptions.ValidationError({
                "success": False,
                "err_msg": data
            })
        return Response({"success": True, "challenge": data.get("challenge")})


@extend_schema(
    tags=["E-imzo"]
)
class EimzoLoginView(views.APIView):
    """
    Frontend imzolangan pkcs7 ni shu yerga yuboradi.
    Backend auth qiladi, user topadi, JWT qaytaradi.
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        pkcs7 = request.data.get("pkcs7")
        if not pkcs7:
            raise exceptions.ValidationError({
                "success": False,
                "err_msg": "pkcs7 field is required"
            })

        # 1. E-Imzo server orqali auth
        ok, status_code, data = eimzo_api.eri_backend_auth(request, pkcs7)
        if not ok:
            raise exceptions.ValidationError({
                "success": False,
                "err_msg": data
            })

        # 2. Sertifikat ma'lumotlarini olish
        # subjectName ichida PINFL yoki TIN bo'ladi
        subject_name = data.get("subjectName", {})
        pkcs7_info = data.get("pkcs7Info", {})

        # PINFL (jismoniy shaxs): 1.2.860.3.16.1.2
        # TIN   (yuridik shaxs):  1.2.860.3.16.1.1
        pinfl = subject_name.get("1.2.860.3.16.1.2")
        tin = subject_name.get("1.2.860.3.16.1.1")
        cn = subject_name.get("CN", "")  # To'liq FISh

        # 3. Userni topish
        user = None

        if pinfl:
            user = CustomUser.objects.filter(pinfl=pinfl).first()

        if user is None and tin:
            user = CustomUser.objects.filter(tin=tin).first()

        if user is None:
            raise exceptions.AuthenticationFailed({
                "success": False,
                "err_msg": "Bu sertifikat bilan ro'yxatdan o'tgan foydalanuvchi topilmadi."
            })

        if not user.is_active:
            raise exceptions.AuthenticationFailed({
                "success": False,
                "err_msg": "Foydalanuvchi bloklangan."
            })

        # 4. full_name ni yangilash (ixtiyoriy)
        if cn and not user.full_name:
            user.full_name = cn
            user.save(update_fields=["full_name"])

        # 5. JWT tokenlar yaratish
        refresh = RefreshToken.for_user(user)

        # 6. Organization nomi
        organization_name = ""
        if user.organization:
            organization_name = user.organization.name

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "email": user.email,
                "role": user.role,
                "user_id": user.id,
                "full_name": user.full_name or cn,
                "organization": organization_name,
            },
            status=status.HTTP_200_OK
        )


# ---- Mavjud view lar ----
@extend_schema(
    tags=["E-imzo"]
)
class SavePkcsView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        pkcs7 = request.data.get("pkcs7b64")
        if not pkcs7:
            raise exceptions.ValidationError({"success": False, "err_msg": "pkcs7b64 field is required"})

        status_code, resp = eimzo_api.timestamp_pkcs7(pkcs7, request)
        if status_code != 200:
            raise exceptions.ValidationError({"success": False, "err_msg": resp.text})

        pkcs7b64 = resp.json().get("pkcs7b64")
        if not pkcs7b64:
            return Response({"success": False, "err_msg": resp.json()}, status=406)

        return Response({"success": True, "pkcs7b64": pkcs7b64})

@extend_schema(
    tags=["E-imzo"]
)
class PkcsVerify(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        pkcs7b64 = request.data.get("pkcs7b64")
        if not pkcs7b64:
            raise exceptions.ValidationError({"success": False, "err_msg": "pkcs7b64 field is required"})

        status_code, resp = eimzo_api.eimzo_verify(pkcs7b64, request)
        if status_code != 200:
            raise exceptions.ValidationError({"success": False, "err_msg": resp.text})

        return Response(resp.json())
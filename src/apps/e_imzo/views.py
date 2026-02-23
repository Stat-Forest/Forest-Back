import logging
from rest_framework import views, permissions, exceptions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import CustomUser
from .services import EimzoServiceApi
from drf_spectacular.utils import extend_schema

logger = logging.getLogger(__name__)
eimzo_api = EimzoServiceApi()


@extend_schema(tags=["E-imzo"])
class EimzoChallengeView(views.APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        ok, status_code, data = eimzo_api.eri_challenge(request)
        logger.warning(f"=== CHALLENGE === ok={ok}, status={status_code}, data={data}")
        if not ok:
            raise exceptions.ValidationError({"success": False, "err_msg": data})
        return Response({"success": True, "challenge": data.get("challenge")})


@extend_schema(tags=["E-imzo"])
class EimzoLoginView(views.APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        pkcs7 = request.data.get("pkcs7")
        logger.warning(f"=== LOGIN START === pkcs7 keldi: {bool(pkcs7)}")

        if not pkcs7:
            raise exceptions.ValidationError({"success": False, "err_msg": "pkcs7 field is required"})

        # 1. E-Imzo server orqali auth
        ok, status_code, data = eimzo_api.eri_backend_auth(request, pkcs7)
        logger.warning(f"=== BACKEND AUTH === ok={ok}, status={status_code}, data={data}")

        if not ok:
            raise exceptions.ValidationError({"success": False, "err_msg": data})

        # 2. subjectName olish — bo'sh bo'lsa pkcs7/info dan olamiz
        subject_name = data.get("subjectName", {})
        logger.warning(f"=== SUBJECT NAME (auth dan) === {subject_name}")

        if not subject_name:
            logger.warning("=== subjectName bo'sh — pkcs7/info ga murojaat ===")
            info_status, info_resp = eimzo_api.pkcs7_info(pkcs7, request)
            logger.warning(f"=== PKCS7 INFO === status={info_status}, data={info_resp.text}")
            if info_status == 200:
                subject_name = info_resp.json().get("subjectName", {})
                logger.warning(f"=== SUBJECT NAME (info dan) === {subject_name}")

        pinfl = subject_name.get("1.2.860.3.16.1.2")
        tin = subject_name.get("1.2.860.3.16.1.1")
        cn = subject_name.get("CN", "")
        logger.warning(f"=== PINFL={pinfl}, TIN={tin}, CN={cn} ===")

        # 3. Userni topish
        user = None
        if pinfl:
            user = CustomUser.objects.filter(pinfl=pinfl).first()
            logger.warning(f"=== PINFL bo'yicha user === {user}")

        if user is None and tin:
            user = CustomUser.objects.filter(tin=tin).first()
            logger.warning(f"=== TIN bo'yicha user === {user}")

        logger.warning(f"=== FINAL USER === {user}")

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

        # 4. full_name yangilash
        if cn and not user.full_name:
            user.full_name = cn
            user.save(update_fields=["full_name"])

        # 5. JWT
        refresh = RefreshToken.for_user(user)
        organization_name = user.organization.name if user.organization else ""
        logger.warning(f"=== LOGIN MUVAFFAQIYATLI === {user.email}")

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


@extend_schema(tags=["E-imzo"])
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


@extend_schema(tags=["E-imzo"])
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
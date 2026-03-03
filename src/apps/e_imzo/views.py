import logging
from rest_framework import views, permissions, exceptions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import CustomUser
from apps.logs.models import HistoryActionJournal
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

        # 2. subjectName olish
        subject_name = data.get("subjectName", {})
        logger.warning(f"=== SUBJECT NAME (auth dan) === {subject_name}")

        # OCSP ishlamasa subjectName bo'sh keladi — pkcs7/info dan olamiz
        if not subject_name:
            logger.warning("=== subjectName bo'sh — pkcs7/info ga murojaat ===")
            info_status, info_resp = eimzo_api.pkcs7_info(pkcs7, request)
            logger.warning(f"=== PKCS7 INFO status={info_status} ===")
            if info_status == 200:
                try:
                    info_data = info_resp.json()
                    subject_name = info_data["signers"][0]["certificate"][0]["subjectInfo"]
                    logger.warning(f"=== SUBJECT NAME (info dan) === {subject_name}")
                except (KeyError, IndexError) as e:
                    logger.warning(f"=== subjectInfo olishda xato === {e}")

        pinfl = subject_name.get("1.2.860.3.16.1.2")
        tin = subject_name.get("1.2.860.3.16.1.1")
        cn = subject_name.get("CN", "")
        logger.warning(f"=== PINFL={pinfl}, TIN={tin}, CN={cn} ===")

        if not pinfl and not tin:
            raise exceptions.AuthenticationFailed({
                "success": False,
                "err_msg": "Sertifikatda PINFL yoki TIN mavjud emas."
            })

        # 3. Userni topish — PINFL ustunlik qiladi, keyin TIN
        user = None
        created = False

        if pinfl:
            user = CustomUser.objects.filter(pinfl=pinfl).first()
            logger.warning(f"=== PINFL bo'yicha user === {user}")

        if user is None and tin:
            user = CustomUser.objects.filter(tin=tin).first()
            logger.warning(f"=== TIN bo'yicha user === {user}")

        # 4. Topilmasa — yangi user yaratish (qayta create bo'lmasligi uchun get_or_create ishlatiladi)
        # 4. Topilmasa — yangi user yaratish (qayta create bo'lmasligi uchun get_or_create ishlatiladi)
        if user is None:
            logger.warning("=== User topilmadi — yangi yaratilmoqda ===")

            # ----------------------------
            # 1. Organization topish
            # ----------------------------
            organization = None

            if tin:
                try:
                    from apps.general.models import Organization

                    # AGAR stir CharField bo‘lsa int() QILMANG
                    organization = Organization.objects.filter(stir=tin.strip()).first()

                    logger.warning(
                        f"=== TIN={tin} bo'yicha Organization === {organization}"
                    )
                except Exception as e:
                    logger.warning(f"=== Organization qidirishda xato === {e}")

            # ----------------------------
            # 2. Lookup tayyorlash
            # ----------------------------
            lookup = {}

            if pinfl:
                lookup["pinfl"] = pinfl.strip()
            elif tin:
                lookup["tin"] = tin.strip()
            else:
                raise ValueError("PINFL yoki TIN mavjud emas")

            # ----------------------------
            # 3. Email generatsiya (USERNAME_FIELD = email)
            # ----------------------------
            generated_email = f"{pinfl or tin}@eimzo.local"

            # ----------------------------
            # 4. get_or_create (majburiy fieldlar bilan)
            # ----------------------------
            user, created = CustomUser.objects.get_or_create(
                **lookup,
                defaults={
                    "email": generated_email,
                    "first_name": subject_name.get("Name", ""),
                    "last_name": subject_name.get("SURNAME", ""),
                    "father_name": "",
                    "passport_number": "AA0000000",
                    "date_of_place": "",
                    "address": "",
                    "gender": CustomUser.Gender.MALE,
                    "role": CustomUser.Role.TASHKILOT_RAHBARI,
                    "organization": organization,
                    "pinfl": pinfl,
                    "tin": tin,
                    "is_active": True,
                    "full_name": cn,
                },
            )

            logger.warning(
                f"=== {'YANGI USER YARATILDI' if created else 'MAVJUD USER (race condition)'} === {user}"
            )

        logger.warning(f"=== FINAL USER === {user}")

        if not user.is_active:
            raise exceptions.AuthenticationFailed({
                "success": False,
                "err_msg": "Foydalanuvchi bloklangan."
            })

        # 5. full_name yangilash (agar bo'sh bo'lsa)
        if cn and not user.full_name:
            user.full_name = cn
            user.save(update_fields=["full_name"])

        # 6. PINFL yoki TIN yangilash (agar bitta bo'lib ikkinchisi bo'sh bo'lsa)
        update_fields = []
        if pinfl and not user.pinfl:
            user.pinfl = pinfl
            update_fields.append("pinfl")
        if tin and not user.tin:
            user.tin = tin
            update_fields.append("tin")
        if update_fields:
            user.save(update_fields=update_fields)

        # 7. JWT
        refresh = RefreshToken.for_user(user)
        organization_name = user.organization.name if user.organization else ""

        # 8. Journal
        HistoryActionJournal.objects.create(
            user=user,
            action='add' if created else 'login',
            model_name='CustomUser',
            object_repr=str(user),
            object_id=str(user.id),
            change_message="E-imzo orqali ro'yxatdan o'tdi" if created else "E-imzo orqali tizimga kirdi"
        )

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
                "is_new_user": created,
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
import base64
import binascii
import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from rest_framework import views, permissions, exceptions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import CustomUser
from apps.logs.models import HistoryActionJournal
from apps.authentications.service.refresh_cookie import set_refresh_cookie
from .services import EimzoServiceApi
from drf_spectacular.utils import extend_schema

logger = logging.getLogger(__name__)
eimzo_api = EimzoServiceApi()

# Login challenge'lari: server bergan, bir martalik (audit B1). Ilgari frontend
# tasodifiy matn imzolardi va backend uni hech narsaga bog'lamasdi — istalgan
# eski PKCS#7 (masalan hisobot imzosi) bilan login qilish mumkin edi.
LOGIN_CHALLENGE_TTL = 180
EIMZO_GENERIC_ERROR = "E-imzo serveri bilan ishlashda xatolik. Keyinroq urinib ko'ring."


def _challenge_key(challenge: str) -> str:
    return "eimzo:login_challenge:" + hashlib.sha256(challenge.encode("utf-8")).hexdigest()


def consume_login_challenge(challenge: str, pkcs7: str) -> None:
    """Challenge biz bergan va ishlatilmagan ekanini, pkcs7 ichida aynan shu matn
    borligini tekshiradi; muvaffaqiyatda challenge bir martalik bo'lib o'chiriladi."""
    if not challenge or not isinstance(challenge, str):
        raise exceptions.AuthenticationFailed({"success": False, "err_msg": "Login challenge yuborilmadi."})
    key = _challenge_key(challenge)
    if not cache.get(key):
        raise exceptions.AuthenticationFailed({
            "success": False, "err_msg": "Challenge topilmadi yoki muddati o'tdi. Qaytadan urinib ko'ring."})
    try:
        raw = base64.b64decode(pkcs7)
    except (ValueError, binascii.Error):
        raise exceptions.AuthenticationFailed({"success": False, "err_msg": "pkcs7 formati noto'g'ri."})
    if challenge.encode("utf-8") not in raw:
        raise exceptions.AuthenticationFailed({
            "success": False, "err_msg": "Imzolangan matn berilgan challenge'ga mos emas."})
    cache.delete(key)


@extend_schema(tags=["E-imzo"])
class EimzoChallengeView(views.APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        ok, status_code, data = eimzo_api.eri_challenge(request)
        logger.debug("E-imzo challenge: ok=%s status=%s", ok, status_code)
        if not ok:
            raise exceptions.ValidationError({"success": False, "err_msg": data})
        challenge = data.get("challenge")
        if challenge:
            cache.set(_challenge_key(str(challenge)), 1, LOGIN_CHALLENGE_TTL)
        return Response({"success": True, "challenge": challenge})


@extend_schema(tags=["E-imzo"])
class EimzoLoginView(views.APIView):
    permission_classes = (permissions.AllowAny,)

    @staticmethod
    def _find_organization_by_tin(tin: str):
        """
        TIN/STIR bo'yicha tashkilotni xavfsiz qidiradi.
        Sertifikatdan kelgan qiymat har doim string bo'ladi, shuning uchun
        PositiveBigIntegerField bilan solishtirishdan oldin tozalab/cast qilamiz.
        """
        from apps.general.models import Organization

        if not tin:
            return None

        tin_clean = str(tin).strip()
        if not tin_clean.isdigit():
            logger.warning("E-imzo: TIN noto'g'ri formatda")
            return None

        return Organization.objects.filter(stir=int(tin_clean)).first()

    def post(self, request):
        pkcs7 = request.data.get("pkcs7")
        logger.debug("E-imzo login: pkcs7 keldi=%s", bool(pkcs7))

        if not pkcs7:
            raise exceptions.ValidationError({"success": False, "err_msg": "pkcs7 field is required"})

        # 0. Imzolangan matn — biz bergan bir martalik challenge (audit B1).
        #    EIMZO_LOGIN_REQUIRE_CHALLENGE=False faqat eski frontend bilan
        #    vaqtinchalik moslik uchun.
        if getattr(settings, "EIMZO_LOGIN_REQUIRE_CHALLENGE", True):
            consume_login_challenge(request.data.get("challenge"), pkcs7)

        # 1. E-Imzo server orqali auth
        ok, status_code, data = eimzo_api.eri_backend_auth(request, pkcs7)
        logger.debug("E-imzo backend auth: ok=%s status=%s", ok, status_code)

        if not ok:
            raise exceptions.ValidationError({"success": False, "err_msg": data})

        # 2. subjectName olish
        subject_name = data.get("subjectName", {})

        # OCSP ishlamasa subjectName bo'sh keladi — pkcs7/info dan olamiz
        if not subject_name:
            logger.debug("E-imzo: subjectName bo'sh — pkcs7/info ga murojaat")
            info_status, info_resp = eimzo_api.pkcs7_info(pkcs7, request)
            logger.debug("E-imzo pkcs7/info status=%s", info_status)
            if info_status == 200:
                try:
                    info_data = info_resp.json()
                    subject_name = info_data["signers"][0]["certificate"][0]["subjectInfo"]
                except (KeyError, IndexError) as e:
                    logger.warning("E-imzo: subjectInfo olishda xato: %s", e)
                except ValueError as e:
                    # info_resp.json() JSON bo'lmasa
                    logger.warning("E-imzo: pkcs7/info javobi JSON emas: %s", e)

        pinfl = subject_name.get("1.2.860.3.16.1.2")
        tin = subject_name.get("1.2.860.3.16.1.1")
        cn = subject_name.get("CN", "")

        # PINFL majburiy: foydalanuvchi faqat PINFL bilan aniqlanadi. TIN yuridik
        # shaxs sertifikatida tashkilot STIR'i bo'lib, bir tashkilotdagi hamma
        # xodimda bir xil — u bilan akkaunt topib bo'lmaydi (audit A1).
        if not pinfl:
            raise exceptions.AuthenticationFailed({
                "success": False,
                "err_msg": "Sertifikatda PINFL mavjud emas. Kirish rad etildi."
            })

        # ----------------------------------------------------------
        # 3. TIN bo'yicha Organization majburiy tekshiruvi
        #    (login ham, ro'yxatdan o'tish ham shu qoidaga bo'ysunadi)
        # ----------------------------------------------------------
        if not tin:
            raise exceptions.AuthenticationFailed({
                "success": False,
                "err_msg": "Sertifikatda TIN mavjud emas, tashkilotni aniqlab bo'lmadi."
            })

        cert_organization = self._find_organization_by_tin(tin)
        logger.debug("E-imzo: TIN=%s bo'yicha tashkilot=%s", tin, cert_organization)

        if cert_organization is None:
            raise exceptions.AuthenticationFailed({
                "success": False,
                "err_msg": f"TIN={tin} bo'yicha tizimda tashkilot topilmadi. Kirish rad etildi."
            })

        # 4. Userni topish — faqat PINFL bo'yicha (TIN fallback yo'q)
        pinfl = pinfl.strip()
        user = CustomUser.objects.filter(pinfl=pinfl).first()
        created = False

        # ----------------------------------------------------------
        # 5. Mavjud user uchun — organization TENGLIK tekshiruvi
        # ----------------------------------------------------------
        if user is not None:
            if user.organization_id != cert_organization.id:
                logger.warning(
                    "E-imzo login rad etildi: tashkilot mos emas user_id=%s eski=%s sertifikatdan=%s",
                    user.id, user.organization_id, cert_organization.id,
                )
                raise exceptions.AuthenticationFailed({
                    "success": False,
                    "err_msg": (
                        f"Sertifikatdagi tashkilot ({cert_organization.name}) "
                        f"tizimdagi tashkilotingiz bilan mos kelmadi. Kirish rad etildi."
                    )
                })
            # mos kelsa — hech narsa qilmaymiz, davom etamiz

        # 6. Topilmasa — yangi user yaratish (qayta create bo'lmasligi uchun get_or_create ishlatiladi).
        #    Tashkilot kalitiga ega har kim avtomatik rahbar bo'lib qolmasligi uchun
        #    (audit A2) user FAOL EMAS va oddiy xodim rolida yaratiladi — admin
        #    tekshirib faollashtiradi va kerak bo'lsa rolni ko'taradi.
        if user is None:
            logger.info("E-imzo: yangi foydalanuvchi yaratilmoqda (TIN=%s)", tin)

            user, created = CustomUser.objects.get_or_create(
                pinfl=pinfl,
                defaults={
                    "email": f"{pinfl}@eimzo.local",
                    "first_name": subject_name.get("Name", ""),
                    "last_name": subject_name.get("SURNAME", ""),
                    "father_name": "",
                    "passport_number": "",
                    "date_of_place": "",
                    "address": "",
                    "gender": CustomUser.Gender.MALE,
                    "role": CustomUser.Role.TASHKILOT_HODIMI,
                    "organization": cert_organization,  # <-- majburiy, TIN orqali tasdiqlangan
                    "tin": tin,
                    "is_active": False,
                    "full_name": cn,
                },
            )
            if created:
                HistoryActionJournal.objects.create(
                    user=user,
                    action='add',
                    model_name='CustomUser',
                    object_repr=str(user),
                    object_id=str(user.id),
                    change_message="E-imzo orqali ro'yxatdan o'tdi (faollashtirish kutilmoqda)",
                )

            logger.info(
                "E-imzo: %s user_id=%s",
                "yangi foydalanuvchi yaratildi" if created else "mavjud foydalanuvchi (race condition)",
                user.id,
            )

            # Race condition: get_or_create paytida boshqa so'rov user yaratgan bo'lsa,
            # uning organization'i sertifikatdagi bilan mos kelishini yana tekshiramiz
            if not created and user.organization_id != cert_organization.id:
                logger.warning(
                    "E-imzo race condition: tashkilot mos emas user_id=%s eski=%s sertifikatdan=%s",
                    user.id, user.organization_id, cert_organization.id,
                )
                raise exceptions.AuthenticationFailed({
                    "success": False,
                    "err_msg": "Tashkilot mos kelmadi. Qaytadan urinib ko'ring."
                })


        if not user.is_active:
            raise exceptions.PermissionDenied({
                "success": False,
                "err_msg": (
                    "Hisobingiz yaratildi, administrator tasdig'i kutilmoqda."
                    if created else
                    "Foydalanuvchi faol emas. Administratorga murojaat qiling."
                ),
            })

        # 7. full_name yangilash (agar bo'sh bo'lsa)
        if cn and not user.full_name:
            user.full_name = cn
            user.save(update_fields=["full_name"])

        # 8. PINFL yoki TIN yangilash (agar bitta bo'lib ikkinchisi bo'sh bo'lsa)
        update_fields = []
        if pinfl and not user.pinfl:
            user.pinfl = pinfl
            update_fields.append("pinfl")
        if tin and not user.tin:
            user.tin = tin
            update_fields.append("tin")
        if update_fields:
            user.save(update_fields=update_fields)

        # 9. JWT
        refresh = RefreshToken.for_user(user)
        organization_name = user.organization.name if user.organization else ""

        # 10. Journal
        HistoryActionJournal.objects.create(
            user=user,
            action='login',
            model_name='CustomUser',
            object_repr=str(user),
            object_id=str(user.id),
            change_message="E-imzo orqali tizimga kirdi",
        )

        logger.info("E-imzo login muvaffaqiyatli: user_id=%s", user.id)
        from django.utils import timezone
        user.last_activity = timezone.now()
        user.save(update_fields=["last_activity"])

        response_data = {
            "access": str(refresh.access_token),
            "email": user.email,
            "role": user.role,
            "user_id": user.id,
            "full_name": user.full_name or cn,
            "organization": organization_name,
            "is_new_user": created,
        }

        # Refresh token faqat HttpOnly cookie'da (audit A5)
        return set_refresh_cookie(Response(response_data, status=status.HTTP_200_OK), str(refresh))


@extend_schema(tags=["E-imzo"])
class SavePkcsView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        pkcs7 = request.data.get("pkcs7b64")
        if not pkcs7:
            raise exceptions.ValidationError({"success": False, "err_msg": "pkcs7b64 field is required"})

        status_code, resp = eimzo_api.timestamp_pkcs7(pkcs7, request)
        if status_code != 200:
            # Ichki server javobi mijozga qaytarilmaydi (audit C15) — log'da
            logger.warning("E-imzo timestamp xatosi: status=%s body=%.300s", status_code, getattr(resp, "text", ""))
            raise exceptions.ValidationError({"success": False, "err_msg": EIMZO_GENERIC_ERROR})

        pkcs7b64 = resp.json().get("pkcs7b64")
        if not pkcs7b64:
            logger.warning("E-imzo timestamp: pkcs7b64 yo'q: %.300s", getattr(resp, "text", ""))
            return Response({"success": False, "err_msg": EIMZO_GENERIC_ERROR}, status=406)

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
            logger.warning("E-imzo verify xatosi: status=%s body=%.300s", status_code, getattr(resp, "text", ""))
            raise exceptions.ValidationError({"success": False, "err_msg": EIMZO_GENERIC_ERROR})

        return Response(resp.json())
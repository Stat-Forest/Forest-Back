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
            logger.warning(f"=== TIN noto'g'ri formatda === {tin}")
            return None

        return Organization.objects.filter(stir=int(tin_clean)).first()

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
                except ValueError as e:
                    # info_resp.json() JSON bo'lmasa
                    logger.warning(f"=== pkcs7/info javobi JSON emas === {e}")

        pinfl = subject_name.get("1.2.860.3.16.1.2")
        tin = subject_name.get("1.2.860.3.16.1.1")
        cn = subject_name.get("CN", "")
        logger.warning(f"=== PINFL={pinfl}, TIN={tin}, CN={cn} ===")

        if not pinfl and not tin:
            raise exceptions.AuthenticationFailed({
                "success": False,
                "err_msg": "Sertifikatda PINFL yoki TIN mavjud emas."
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
        logger.warning(f"=== TIN={tin} bo'yicha topilgan Organization === {cert_organization}")

        if cert_organization is None:
            raise exceptions.AuthenticationFailed({
                "success": False,
                "err_msg": f"TIN={tin} bo'yicha tizimda tashkilot topilmadi. Kirish rad etildi."
            })

        # 4. Userni topish — PINFL ustunlik qiladi, keyin TIN
        user = None
        created = False

        if pinfl:
            user = CustomUser.objects.filter(pinfl=pinfl).first()
            logger.warning(f"=== PINFL bo'yicha user === {user}")

        if user is None and tin:
            user = CustomUser.objects.filter(tin=tin).first()
            logger.warning(f"=== TIN bo'yicha user === {user}")

        # ----------------------------------------------------------
        # 5. Mavjud user uchun — organization TENGLIK tekshiruvi
        # ----------------------------------------------------------
        if user is not None:
            if user.organization_id != cert_organization.id:
                logger.warning(
                    f"=== ORGANIZATION MOS KELMADI, KIRISH RAD ETILDI === "
                    f"user={user.email}, eski={user.organization}, sertifikatdan={cert_organization}"
                )
                raise exceptions.AuthenticationFailed({
                    "success": False,
                    "err_msg": (
                        f"Sertifikatdagi tashkilot ({cert_organization.name}) "
                        f"tizimdagi tashkilotingiz bilan mos kelmadi. Kirish rad etildi."
                    )
                })
            # mos kelsa — hech narsa qilmaymiz, davom etamiz

        # 6. Topilmasa — yangi user yaratish (qayta create bo'lmasligi uchun get_or_create ishlatiladi)
        if user is None:
            logger.warning("=== User topilmadi — yangi yaratilmoqda ===")

            lookup = {}
            if pinfl:
                lookup["pinfl"] = pinfl.strip()
            elif tin:
                lookup["tin"] = tin.strip()
            else:
                raise ValueError("PINFL yoki TIN mavjud emas")

            generated_email = f"{pinfl or tin}@eimzo.local"

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
                    "organization": cert_organization,  # <-- majburiy, TIN orqali tasdiqlangan
                    "pinfl": pinfl,
                    "tin": tin,
                    "is_active": True,
                    "full_name": cn,
                },
            )

            logger.warning(
                f"=== {'YANGI USER YARATILDI' if created else 'MAVJUD USER (race condition)'} === {user}"
            )

            # Race condition: get_or_create paytida boshqa so'rov user yaratgan bo'lsa,
            # uning organization'i sertifikatdagi bilan mos kelishini yana tekshiramiz
            if not created and user.organization_id != cert_organization.id:
                logger.warning(
                    f"=== RACE CONDITION: ORGANIZATION MOS KELMADI === "
                    f"user={user.email}, eski={user.organization}, sertifikatdan={cert_organization}"
                )
                raise exceptions.AuthenticationFailed({
                    "success": False,
                    "err_msg": "Tashkilot mos kelmadi. Qaytadan urinib ko'ring."
                })

        logger.warning(f"=== FINAL USER === {user}")

        if not user.is_active:
            raise exceptions.AuthenticationFailed({
                "success": False,
                "err_msg": "Foydalanuvchi bloklangan."
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
            action='add' if created else 'login',
            model_name='CustomUser',
            object_repr=str(user),
            object_id=str(user.id),
            change_message="E-imzo orqali ro'yxatdan o'tdi" if created else "E-imzo orqali tizimga kirdi"
        )

        logger.warning(f"=== LOGIN MUVAFFAQIYATLI === {user.email}")
        from django.utils import timezone
        user.last_activity = timezone.now()
        user.save(update_fields=["last_activity"])

        response_data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "email": user.email,
            "role": user.role,
            "user_id": user.id,
            "full_name": user.full_name or cn,
            "organization": organization_name,
            "is_new_user": created,
        }
        logger.warning(f"=== FINAL RESPONSE === {response_data}")

        return Response(response_data, status=status.HTTP_200_OK)

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
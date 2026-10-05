"""
Hisobotni yuborishda E-imzo bilan imzolash.

Oqim:
    1. build_signing_document() — hisobot uchun imzolanadigan matn (JSON) va
       nonce yaratadi; matn hash'i 15 daqiqaga cache'ga yoziladi.
    2. Frontend matnni E-imzo (PFX yoki USB-token) bilan attached PKCS#7 ga
       imzolaydi va /reports/send/ ga pkcs7 bilan yuboradi.
    3. verify_and_store_signature() — e-imzo-server orqali vaqt tamg'asi
       qo'yadi va imzoni tekshiradi, imzolangan matn aynan biz bergan matn
       ekanini (cache'dagi hash), hisobot o'zgarmaganini (items_hash) va
       sertifikat STIR'i hisobot tashkilotiga tegishli ekanini tekshiradi,
       so'ng ReportSignature yaratadi.

Ikki rejim:
    document  — VPN ishlaganda: rahbar bizning JSON hujjatni imzolaydi, TSA
                tamg'asi qo'yiladi, /backend/pkcs7/verify/attached tekshiradi.
    challenge — VPN ishlamaganda (masalan VPN kalit muddati tugagan): e-imzo-
                server TSA ham, verify/attached ham bera olmaydi ("timestamp is
                required"). Rahbar e-imzo-server challenge'ini imzolaydi,
                /backend/auth imzo va sertifikat zanjirini tekshiradi (OCSP'siz,
                login bilan bir xil darajada), hujjat esa challenge'ga server
                tomonida (cache) bog'lanadi. Rejim har challenge'da avtomatik
                tanlanadi (/ping, 5 daqiqa cache).
"""
import base64
import hashlib
import json
import secrets
from datetime import datetime

import logging

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.e_imzo.services import EIMZO_UNAVAILABLE_MESSAGE, EimzoServiceApi
from apps.reports.models import Report, ReportItem, ReportSignature
from apps.reports.services.quarter_validator import DaromadQuarterService

DOCUMENT_TYPE = "stat-urmon.report.send"
MODE_DOCUMENT = "document"
MODE_CHALLENGE = "challenge"
VPN_STATUS_CACHE_KEY = "eimzo_vpn_available"
VPN_STATUS_TTL = 5 * 60
DOCUMENT_VERSION = 1
CHALLENGE_TTL = 15 * 60  # soniya

OID_PINFL = "1.2.860.3.16.1.2"
OID_TIN = "1.2.860.3.16.1.1"

eimzo_api = EimzoServiceApi()
logger = logging.getLogger(__name__)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cache_key(report_id, nonce: str) -> str:
    return f"report_sign:{report_id}:{nonce}"


def _fail(detail, code=400):
    raise CustomExceptionError(code=code, detail=detail)


def signing_quarter(report: Report):
    """Daromad hisobotida imzo joriy chorakka tegishli, boshqalarida None."""
    if DaromadQuarterService.is_daromad_report(report):
        return report.current_quarter or None
    return None


def compute_items_hash(report: Report) -> str:
    """
    Hisobot qiymatlarining deterministik hash'i. Imzolangandan keyin
    hisobot o'zgartirilgan-o'zgartirilmaganini shu orqali bilamiz.
    """
    rows = []
    items = (
        ReportItem.objects.filter(report=report)
        .prefetch_related("inners")
        .order_by("statement_column_id")
    )
    for item in items:
        inners = sorted(
            (str(inner.plant_id or ""), inner.value or "")
            for inner in item.inners.all()
        )
        rows.append([str(item.statement_column_id), item.value or "", inners])
    return _sha256(json.dumps(rows, ensure_ascii=False, separators=(",", ":")))


def vpn_available(request) -> bool:
    cached = cache.get(VPN_STATUS_CACHE_KEY)
    if cached is not None:
        return cached
    ok = eimzo_api.vpn_available(request)
    cache.set(VPN_STATUS_CACHE_KEY, ok, VPN_STATUS_TTL)
    return ok


def build_signing_challenge(report: Report, user, request) -> dict:
    """
    Frontend uchun imzolash topshirig'i. Qaytaradi:
        document  — hisobot hujjati (JSON matn, har ikki rejimda yoziladi)
        sign_text — rahbar aynan nimani imzolaydi (document yoki e-imzo challenge)
        mode, nonce, expires_in
    """
    document, nonce = build_signing_document(report, user)
    if vpn_available(request):
        return {"document": document, "sign_text": document, "mode": MODE_DOCUMENT,
                "nonce": nonce, "expires_in": CHALLENGE_TTL}

    ok, _status, data = _call_eimzo(eimzo_api.eri_challenge, request)
    if not ok:
        _fail(_("E-imzo server challenge bermadi: ") + str(data), code=503)
    challenge = data.get("challenge")
    if not challenge:
        _fail(_("E-imzo server challenge bermadi."), code=503)
    ttl = min(CHALLENGE_TTL, int(data.get("ttl") or 120))
    cache.set(_cache_key(report.id, nonce), {
        "mode": MODE_CHALLENGE, "challenge": challenge, "document": document,
        "document_hash": _sha256(document),
    }, ttl)
    return {"document": document, "sign_text": challenge, "mode": MODE_CHALLENGE,
            "nonce": nonce, "expires_in": ttl}


def build_signing_document(report: Report, user) -> tuple[str, str]:
    """Imzolanadigan matn va nonce. Matn hash'i cache'da CHALLENGE_TTL saqlanadi."""
    org = report.organization
    nonce = secrets.token_hex(16)
    payload = {
        "v": DOCUMENT_VERSION,
        "type": DOCUMENT_TYPE,
        "report_id": str(report.id),
        "organization": {
            "id": str(org.id) if org else None,
            "name": getattr(org, "name", None),
            "stir": str(org.stir) if org and org.stir else None,
        },
        "statement": {
            "id": str(report.statement_id) if report.statement_id else None,
            "name": getattr(report.statement, "name", None),
        },
        "deadline": {
            "id": str(report.deadline_id) if report.deadline_id else None,
            "submit_at": str(getattr(report.deadline, "submit_at", "") or ""),
        },
        "quarter": signing_quarter(report),
        "items_hash": compute_items_hash(report),
        "signer_user_id": str(user.id),
        "generated_at": timezone.now().isoformat(timespec="seconds"),
        "nonce": nonce,
    }
    document = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    cache.set(_cache_key(report.id, nonce), _sha256(document), CHALLENGE_TTL)
    return document, nonce


def _parse_eimzo_dt(value):
    """e-imzo-server sanasi: 'YYYY-MM-DD HH:MM:SS' (server vaqt zonasida)."""
    if not value:
        return None
    try:
        naive = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return timezone.make_aware(naive, timezone.get_current_timezone())


def _trim_verify_result(info: dict) -> dict:
    """OCSP javobi va ochiq kalitlarsiz (ular katta) saqlash uchun nusxa."""
    signers = []
    for signer in info.get("signers") or []:
        cert0 = (signer.get("certificate") or [{}])[0] or {}
        tst = signer.get("timeStampInfo") or {}
        signers.append({
            "signingTime": signer.get("signingTime"),
            "verified": signer.get("verified"),
            "certificateVerified": signer.get("certificateVerified"),
            "certificateValidAtSigningTime": signer.get("certificateValidAtSigningTime"),
            "revokedStatusInfo": signer.get("revokedStatusInfo"),
            "exception": signer.get("exception"),
            "timeStamp": {
                "time": tst.get("time"),
                "verified": tst.get("verified"),
                "tsa": tst.get("tsa"),
                "serialNumber": tst.get("serialNumber"),
            },
            "certificate": {
                key: cert0.get(key)
                for key in ("subjectInfo", "issuerName", "serialNumber", "validFrom", "validTo")
            },
        })
    return {"signers": signers}


def _call_eimzo(func, *args):
    try:
        return func(*args)
    except requests.RequestException:
        _fail(EIMZO_UNAVAILABLE_MESSAGE, code=503)


def _attach_timestamp(pkcs7: str, request) -> tuple[str, bool]:
    """
    Imzoga TSA vaqt tamg'asini qo'shadi. TSA xizmati e-imzo VPN orqali
    ishlaydi va vaqti-vaqti bilan ulanmaydi ("TimeStampTokenProvider
    UNAVAILABLE"). EIMZO_REQUIRE_TIMESTAMP=False (standart) bo'lsa bunday
    holatda imzo tamg'asiz qabul qilinadi va signed_at sifatida server
    qabul qilgan vaqt yoziladi; True bo'lsa yuborish rad etiladi.
    """
    require = getattr(settings, "EIMZO_REQUIRE_TIMESTAMP", False)
    last_error = ""
    for _attempt in range(2):  # tarmoq uzilishi uchun bitta qayta urinish
        try:
            ts_status, ts_resp = eimzo_api.timestamp_pkcs7(pkcs7, request)
        except requests.RequestException as exc:
            last_error = str(exc)
            continue
        if ts_status == 200:
            try:
                ts_data = ts_resp.json()
            except ValueError:
                last_error = "javob JSON emas"
                continue
            if ts_data.get("status") == 1 and ts_data.get("pkcs7b64"):
                return ts_data["pkcs7b64"], True
            last_error = str(ts_data.get("message") or ts_data)
        else:
            last_error = (ts_resp.text or "")[:300]
    logger.warning("E-imzo timestamp olinmadi: %s", last_error)
    if require:
        _fail(_("Imzoga vaqt tamg'asi qo'yib bo'lmadi: ") + last_error)
    return pkcs7, False


def _check_signer_matches(report: Report, user, subject: dict) -> tuple[str, str, str]:
    """Sertifikat STIR'i hisobot tashkilotiga, PINFL foydalanuvchiga mosmi. (tin, pinfl, cn)"""
    tin = str(subject.get(OID_TIN) or "").strip()
    pinfl = str(subject.get(OID_PINFL) or "").strip()
    cn = str(subject.get("CN") or "")
    if not tin:
        _fail(_("Sertifikatda tashkilot STIR'i yo'q. Yuridik shaxs kaliti bilan imzolang."))
    org = report.organization
    if not org or not org.stir:
        _fail(_("Tashkilotning STIR raqami tizimda kiritilmagan. Administratorga murojaat qiling."))
    if str(org.stir) != tin:
        _fail(_("Sertifikat STIR'i hisobot tashkilotiga mos kelmaydi."))
    user_pinfl = str(getattr(user, "pinfl", "") or "").strip()
    if user_pinfl and pinfl and user_pinfl != pinfl:
        _fail(_("Sertifikat tizimga kirgan foydalanuvchiga tegishli emas."))
    return tin, pinfl, cn


def _verify_challenge_mode(*, report, user, pkcs7, request, entry, nonce) -> ReportSignature:
    """VPN'siz rejim: pkcs7 = imzolangan e-imzo challenge; /backend/auth tekshiradi."""
    ok, _status, data = _call_eimzo(eimzo_api.eri_backend_auth, request, pkcs7)
    if not ok:
        _fail(_("Imzoni tekshirib bo'lmadi: ") + str(data))
    auth_status = data.get("status")

    cert = data.get("subjectCertificateInfo") or {}
    subject = cert.get("subjectName") or {}
    # OCSP ishlamaganda (status -1) subjectName bo'sh kelishi mumkin — pkcs7/info dan olamiz
    if not subject:
        info_status, info_resp = _call_eimzo(eimzo_api.pkcs7_info, pkcs7, request)
        if info_status == 200:
            try:
                cert = (info_resp.json()["signers"][0]["certificate"] or [{}])[0]
                subject = cert.get("subjectInfo") or {}
            except (KeyError, IndexError, ValueError, TypeError):
                subject = {}
    if not subject:
        _fail(_("Imzolovchi sertifikatini aniqlab bo'lmadi."))

    document = entry["document"]
    payload = json.loads(document)
    items_hash = compute_items_hash(report)
    if payload.get("items_hash") != items_hash:
        _fail(_("Hisobot imzolangandan keyin o'zgartirilgan. Qaytadan imzolang."))
    quarter = signing_quarter(report)
    if (payload.get("quarter") or None) != quarter:
        _fail(_("Imzo boshqa chorakka tegishli."))

    tin, pinfl, cn = _check_signer_matches(report, user, subject)

    signature = ReportSignature.objects.create(
        report=report,
        quarter=quarter,
        signer=user,
        signer_cn=cn[:255],
        signer_tin=tin[:20],
        signer_pinfl=pinfl[:20],
        cert_serial=str(cert.get("serialNumber") or "")[:64],
        cert_valid_from=str(cert.get("validFrom") or "")[:32],
        cert_valid_to=str(cert.get("validTo") or "")[:32],
        signed_at=timezone.now(),
        document=document,
        document_hash=entry["document_hash"],
        items_hash=items_hash,
        pkcs7=pkcs7,
        verify_status=auth_status,
        verify_result={
            "mode": MODE_CHALLENGE,
            "challenge": entry["challenge"],
            "timestamped": False,
            "ocsp_checked": auth_status == 1,
            "certificate": {k: cert.get(k) for k in ("serialNumber", "validFrom", "validTo")},
            "subjectInfo": subject,
        },
        is_valid=True,
        created_by=user,
    )
    cache.delete(_cache_key(report.id, nonce))
    return signature


def verify_and_store_signature(*, report: Report, user, pkcs7: str, request, nonce: str = "") -> ReportSignature:
    """
    PKCS#7 ni tekshirib, hisobot uchun ReportSignature yaratadi.
    Har qanday nomuvofiqlikda CustomExceptionError(400) ko'taradi.
    """
    if not pkcs7 or not isinstance(pkcs7, str):
        _fail(_("E-imzo imzosi (pkcs7) yuborilmadi."))

    # Challenge rejimi: nonce bo'yicha cache'da challenge yozuvi bo'lsa
    if nonce:
        entry = cache.get(_cache_key(report.id, nonce))
        if isinstance(entry, dict) and entry.get("mode") == MODE_CHALLENGE:
            return _verify_challenge_mode(
                report=report, user=user, pkcs7=pkcs7, request=request, entry=entry, nonce=nonce,
            )

    # 1) Vaqt tamg'asi (TSA ulanmasa — tamg'asiz davom etiladi, pastga qarang)
    pkcs7_ts, timestamped = _attach_timestamp(pkcs7, request)

    # 2) Imzoni tekshirish
    v_status, v_resp = _call_eimzo(eimzo_api.eimzo_verify, pkcs7_ts, request)
    if v_status != 200:
        _fail(_("Imzoni tekshirib bo'lmadi: ") + (v_resp.text or "")[:300])
    try:
        v_data = v_resp.json()
    except ValueError:
        _fail(_("E-imzo server javobi noto'g'ri (verify)."))
    status = v_data.get("status")
    info = v_data.get("pkcs7Info") or {}
    if status != 1:
        _fail(_("Imzo haqiqiy emas") + f" (status {status}). " + str(v_data.get("message") or ""))

    signers = info.get("signers") or []
    if len(signers) != 1:
        _fail(_("Hujjatda aynan bitta imzo bo'lishi kerak."))
    signer = signers[0]
    if not (
        signer.get("verified")
        and signer.get("certificateVerified")
        and signer.get("certificateValidAtSigningTime")
    ):
        _fail(_("Imzo yoki sertifikat haqiqiy emas: ") + str(signer.get("exception") or ""))

    # 3) Imzolangan hujjat biz bergan matn ekanini tekshirish
    try:
        document = base64.b64decode(info.get("documentBase64") or "").decode("utf-8")
        payload = json.loads(document)
    except (ValueError, UnicodeDecodeError):
        _fail(_("Imzolangan hujjatni o'qib bo'lmadi."))
    if not isinstance(payload, dict) or payload.get("type") != DOCUMENT_TYPE:
        _fail(_("Imzolangan hujjat hisobot yuborish hujjati emas."))
    if payload.get("report_id") != str(report.id):
        _fail(_("Imzo boshqa hisobotga tegishli."))

    nonce = payload.get("nonce")
    key = _cache_key(report.id, nonce) if nonce else None
    document_hash = _sha256(document)
    cached = cache.get(key) if key else None
    if isinstance(cached, dict):
        cached = cached.get("document_hash")
    if not key or cached != document_hash:
        _fail(_("Imzolash so'rovi topilmadi yoki muddati o'tgan. Qaytadan imzolang."))

    items_hash = compute_items_hash(report)
    if payload.get("items_hash") != items_hash:
        _fail(_("Hisobot imzolangandan keyin o'zgartirilgan. Qaytadan imzolang."))

    quarter = signing_quarter(report)
    if (payload.get("quarter") or None) != quarter:
        _fail(_("Imzo boshqa chorakka tegishli."))

    # 4) Imzolovchi sertifikati hisobot tashkilotiga tegishlimi
    cert0 = (signer.get("certificate") or [{}])[0] or {}
    subject = cert0.get("subjectInfo") or {}
    tin, pinfl, cn = _check_signer_matches(report, user, subject)

    # Ishonchli vaqt: TSA tamg'asi; u bo'lmasa server qabul qilgan vaqt
    # (foydalanuvchi kompyuteridagi signingTime ga ishonib bo'lmaydi).
    tst = signer.get("timeStampInfo") or {}
    signed_at = (_parse_eimzo_dt(tst.get("time")) if timestamped else None) or timezone.now()
    verify_result = _trim_verify_result(info)
    verify_result["mode"] = MODE_DOCUMENT
    verify_result["timestamped"] = timestamped
    verify_result["ocsp_checked"] = True

    signature = ReportSignature.objects.create(
        report=report,
        quarter=quarter,
        signer=user,
        signer_cn=cn[:255],
        signer_tin=tin[:20],
        signer_pinfl=pinfl[:20],
        cert_serial=str(cert0.get("serialNumber") or "")[:64],
        cert_valid_from=str(cert0.get("validFrom") or "")[:32],
        cert_valid_to=str(cert0.get("validTo") or "")[:32],
        signed_at=signed_at,
        document=document,
        document_hash=document_hash,
        items_hash=items_hash,
        pkcs7=pkcs7_ts,
        verify_status=status,
        verify_result=verify_result,
        is_valid=True,
        created_by=user,
    )
    cache.delete(key)
    return signature

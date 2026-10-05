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
"""
import base64
import hashlib
import json
import secrets
from datetime import datetime

import requests
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.base.exceptions.exception_files import CustomExceptionError
from apps.e_imzo.services import EIMZO_UNAVAILABLE_MESSAGE, EimzoServiceApi
from apps.reports.models import Report, ReportItem, ReportSignature
from apps.reports.services.quarter_validator import DaromadQuarterService

DOCUMENT_TYPE = "stat-urmon.report.send"
DOCUMENT_VERSION = 1
CHALLENGE_TTL = 15 * 60  # soniya

OID_PINFL = "1.2.860.3.16.1.2"
OID_TIN = "1.2.860.3.16.1.1"

eimzo_api = EimzoServiceApi()


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


def verify_and_store_signature(*, report: Report, user, pkcs7: str, request) -> ReportSignature:
    """
    PKCS#7 ni tekshirib, hisobot uchun ReportSignature yaratadi.
    Har qanday nomuvofiqlikda CustomExceptionError(400) ko'taradi.
    """
    if not pkcs7 or not isinstance(pkcs7, str):
        _fail(_("E-imzo imzosi (pkcs7) yuborilmadi."))

    # 1) Vaqt tamg'asi
    ts_status, ts_resp = _call_eimzo(eimzo_api.timestamp_pkcs7, pkcs7, request)
    if ts_status != 200:
        _fail(_("Imzoga vaqt tamg'asi qo'yib bo'lmadi: ") + (ts_resp.text or "")[:300])
    try:
        ts_data = ts_resp.json()
    except ValueError:
        _fail(_("E-imzo server javobi noto'g'ri (timestamp)."))
    if ts_data.get("status") != 1:
        _fail(_("Imzoga vaqt tamg'asi qo'yib bo'lmadi: ") + str(ts_data.get("message") or ""))
    pkcs7_ts = ts_data.get("pkcs7b64") or pkcs7

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
    if not key or cache.get(key) != document_hash:
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

    tst = signer.get("timeStampInfo") or {}
    signed_at = (
        _parse_eimzo_dt(tst.get("time"))
        or _parse_eimzo_dt(signer.get("signingTime"))
        or timezone.now()
    )

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
        verify_result=_trim_verify_result(info),
        is_valid=True,
        created_by=user,
    )
    cache.delete(key)
    return signature

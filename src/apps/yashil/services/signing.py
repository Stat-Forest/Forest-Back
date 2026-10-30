"""
Hujjat versiyasini E-IMZO bilan imzolash (TZ §13.1) — hisobot imzolash
(`reports/services/report_signing.py`) bilan bir xil ikki rejim, lekin ixtiyoriy
`DocumentVersion` uchun:

    document  — VPN bor: imzolovchi bizning JSON (content_hash, nonce, signer) ni imzolaydi,
                TSA tamg'asi, /backend/pkcs7/verify/attached.
    challenge — VPN yo'q: e-imzo-server challenge'i imzolanadi, /backend/auth tekshiradi,
                hujjat challenge'ga server tomonida (cache) bog'lanadi.

Imzolovchi: `can_sign` a'zolik, profil PINFL = sertifikat PINFL; yetkazib beruvchi
roli uchun tashkilot STIR'i bo'lsa sertifikat TIN'iga mos bo'lishi kerak.
"""
import base64
import binascii
import json
import logging
import secrets

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.e_imzo.services import EIMZO_UNAVAILABLE_MESSAGE, EimzoServiceApi
from apps.yashil.models import DocumentVersion, Signature

DOCUMENT_TYPE = "stat-urmon.yashil.document"
MODE_DOCUMENT = "document"
MODE_CHALLENGE = "challenge"
VPN_STATUS_CACHE_KEY = "eimzo_vpn_available"
VPN_STATUS_TTL = 5 * 60
CHALLENGE_TTL = 15 * 60
OID_PINFL = "1.2.860.3.16.1.2"
OID_TIN = "1.2.860.3.16.1.1"

eimzo_api = EimzoServiceApi()
logger = logging.getLogger(__name__)


class SigningError(Exception):
    def __init__(self, message: str, *, code: str = "signature_invalid", status: int = 422):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


def _cache_key(version_id, nonce: str) -> str:
    return f"yashil:sign:{version_id}:{nonce}"


def _call(func, *args):
    try:
        return func(*args)
    except requests.RequestException:
        raise SigningError(EIMZO_UNAVAILABLE_MESSAGE, code="eimzo_unavailable", status=503)


def vpn_available(request) -> bool:
    cached = cache.get(VPN_STATUS_CACHE_KEY)
    if cached is not None:
        return cached
    try:
        ok = eimzo_api.vpn_available(request)
    except requests.RequestException:
        ok = False
    cache.set(VPN_STATUS_CACHE_KEY, ok, VPN_STATUS_TTL)
    return ok


def _check_signer_profile(user, membership):
    if membership is None or not membership.can_sign:
        raise SigningError("Бу кабинетда имзолаш ҳуқуқи йўқ", code="cannot_sign", status=403)
    if not str(getattr(user, "pinfl", "") or getattr(user, "jshshr", "") or "").strip():
        raise SigningError("Профилингизда ПИНФЛ (ЖШШИР) киритилмаган. Администраторга мурожаат қилинг.", code="signer_profile")


def _check_open_for_role(version: DocumentVersion, role: str):
    """Versiya imzolash uchun ochiq va shu tomon hali imzolamagan bo'lishi kerak (akt — ikki imzo)."""
    if not version.is_open_for_signing:
        raise SigningError("Ҳужжатнинг бу версияси имзолаш учун очиқ эмас (имзоланган ёки алмаштирилган)", code="state_conflict", status=409)
    if version.signatures.filter(role=role).exists():
        raise SigningError("Бу тараф ҳужжатни аллақачон имзолаган", code="state_conflict", status=409)


def _signing_payload(version: DocumentVersion, user, role: str, nonce: str) -> str:
    payload = {
        "v": 1, "type": DOCUMENT_TYPE, "doc_kind": version.document.kind,
        "document_version_id": str(version.id), "number": version.content.get("number"),
        "version_no": version.version_no, "content_hash": version.content_hash,
        "signer_user_id": str(user.id), "role": role,
        "generated_at": timezone.now().isoformat(timespec="seconds"), "nonce": nonce,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def prepare_signing(version: DocumentVersion, user, membership, role: str, request) -> dict:
    """Frontend uchun imzolash topshirig'i: sign_text, mode, nonce, expires_in."""
    _check_signer_profile(user, membership)
    _check_open_for_role(version, role)
    nonce = secrets.token_hex(16)
    document = _signing_payload(version, user, role, nonce)
    entry = {"document": document, "content_hash": version.content_hash, "user_id": str(user.id), "role": role}
    if vpn_available(request):
        entry["mode"] = MODE_DOCUMENT
        cache.set(_cache_key(version.id, nonce), entry, CHALLENGE_TTL)
        return {"document": document, "sign_text": document, "mode": MODE_DOCUMENT, "nonce": nonce, "expires_in": CHALLENGE_TTL}
    ok, _status, data = _call(eimzo_api.eri_challenge, request)
    challenge = (data or {}).get("challenge") if ok and isinstance(data, dict) else None
    if not challenge:
        raise SigningError("E-imzo server challenge бермади: " + str(data), code="eimzo_unavailable", status=503)
    ttl = min(CHALLENGE_TTL, int(data.get("ttl") or 120))
    entry.update(mode=MODE_CHALLENGE, challenge=challenge)
    cache.set(_cache_key(version.id, nonce), entry, ttl)
    return {"document": document, "sign_text": challenge, "mode": MODE_CHALLENGE, "nonce": nonce, "expires_in": ttl}


def _subject_identity(subject: dict, user, membership, role: str):
    tin = str(subject.get(OID_TIN) or "").strip()
    pinfl = str(subject.get(OID_PINFL) or "").strip()
    cn = str(subject.get("CN") or "")
    user_pinfl = str(getattr(user, "pinfl", "") or getattr(user, "jshshr", "") or "").strip()
    if not pinfl:
        raise SigningError("Сертификатда ПИНФЛ йўқ. Шахсий калит билан имзоланг.", code="signer_mismatch")
    if pinfl != user_pinfl:
        raise SigningError("Сертификат тизимга кирган фойдаланувчига тегишли эмас.", code="signer_mismatch")
    if role == Signature.Role.SUPPLIER and membership is not None and membership.organization_id:
        org = membership.organization
        profile = getattr(org, "supplier_profile", None)
        org_stir = (profile.stir if profile and profile.stir else (str(org.stir) if org.stir else ""))
        if org_stir and tin and tin != org_stir:
            raise SigningError("Сертификат СТИРи етказиб берувчи ташкилотга мос эмас.", code="signer_mismatch")
    return tin, pinfl, cn


def _store(version, user, membership, role, *, mode, pkcs7, cert, subject, verify_result) -> Signature:
    tin, pinfl, cn = _subject_identity(subject, user, membership, role)
    verify_result = dict(verify_result or {})
    verify_result.update(content_hash=version.content_hash, subjectInfo=subject)
    signature = Signature.objects.create(
        document_version=version, signer_user=user, signer_membership=membership, role=role,
        signer_cn=cn[:255], signer_tin=tin[:20], signer_pinfl=pinfl[:20],
        cert_serial=str(cert.get("serialNumber") or "")[:64],
        cert_valid_from=str(cert.get("validFrom") or "")[:32], cert_valid_to=str(cert.get("validTo") or "")[:32],
        mode=mode, pkcs7=pkcs7, verify_result=verify_result, is_valid=True, created_by=user,
    )
    from apps.yashil.services.documents import after_signature

    after_signature(version)
    return signature


def verify_and_store(version: DocumentVersion, user, membership, role: str, pkcs7: str, nonce: str, request) -> Signature:
    _check_signer_profile(user, membership)
    if not pkcs7 or not isinstance(pkcs7, str):
        raise SigningError("E-imzo имзоси (pkcs7) юборилмади.")
    if not nonce:
        raise SigningError("Имзолаш сўрови (nonce) йўқ. Қайтадан имзоланг.")
    key = _cache_key(version.id, nonce)
    entry = cache.get(key)
    if not isinstance(entry, dict):
        raise SigningError("Имзолаш сўрови топилмади ёки муддати ўтган. Қайтадан имзоланг.", code="challenge_expired")
    if entry.get("user_id") != str(user.id) or entry.get("role") != role:
        raise SigningError("Имзолаш сўрови бошқа фойдаланувчи учун берилган.")
    version.refresh_from_db()
    _check_open_for_role(version, role)
    if version.content_hash != entry.get("content_hash"):
        raise SigningError("Ҳужжат имзолаш сўровидан кейин ўзгартирилган. Қайтадан имзоланг.", code="content_changed")

    if entry.get("mode") == MODE_CHALLENGE:
        signature = _verify_challenge(version, user, membership, role, pkcs7, request, entry)
    else:
        signature = _verify_document(version, user, membership, role, pkcs7, request, entry)
    cache.delete(key)
    return signature


def _verify_challenge(version, user, membership, role, pkcs7, request, entry) -> Signature:
    challenge = str(entry.get("challenge") or "")
    try:
        raw = base64.b64decode(pkcs7)
    except (ValueError, binascii.Error):
        raise SigningError("Имзо (pkcs7) формати нотўғри.")
    if not challenge or challenge.encode("utf-8") not in raw:
        raise SigningError("Challenge мос эмас: имзоланган матн шу сўров учун берилган challenge эмас. Қайтадан имзоланг.")
    ok, _status, data = _call(eimzo_api.eri_backend_auth, request, pkcs7)
    if not ok:
        raise SigningError("Имзони текшириб бўлмади: " + str(data))
    cert = data.get("subjectCertificateInfo") or {}
    subject = cert.get("subjectName") or {}
    if not subject:
        info_status, info_resp = _call(eimzo_api.pkcs7_info, pkcs7, request)
        if info_status == 200:
            try:
                cert = (info_resp.json()["signers"][0]["certificate"] or [{}])[0]
                subject = cert.get("subjectInfo") or {}
            except (KeyError, IndexError, ValueError, TypeError):
                subject = {}
    if not subject:
        raise SigningError("Имзоловчи сертификатини аниқлаб бўлмади.")
    verify_result = {"mode": MODE_CHALLENGE, "challenge": challenge, "timestamped": False,
                     "ocsp_checked": data.get("status") == 1, "auth_status": data.get("status"),
                     "certificate": {k: cert.get(k) for k in ("serialNumber", "validFrom", "validTo")}}
    return _store(version, user, membership, role, mode=MODE_CHALLENGE, pkcs7=pkcs7, cert=cert, subject=subject, verify_result=verify_result)


def _attach_timestamp(pkcs7: str, request) -> tuple[str, bool]:
    require = getattr(settings, "EIMZO_REQUIRE_TIMESTAMP", False)
    last_error = ""
    for _attempt in range(2):
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
    logger.warning("E-imzo timestamp olinmadi (yashil): %s", last_error)
    if require:
        raise SigningError("Имзога вақт тамғаси қўйиб бўлмади: " + last_error, code="eimzo_unavailable", status=503)
    return pkcs7, False


def _verify_document(version, user, membership, role, pkcs7, request, entry) -> Signature:
    pkcs7_ts, timestamped = _attach_timestamp(pkcs7, request)
    v_status, v_resp = _call(eimzo_api.eimzo_verify, pkcs7_ts, request)
    if v_status != 200:
        raise SigningError("Имзони текшириб бўлмади: " + (v_resp.text or "")[:300])
    try:
        v_data = v_resp.json()
    except ValueError:
        raise SigningError("E-imzo server жавоби нотўғри (verify).")
    info = v_data.get("pkcs7Info") or {}
    if v_data.get("status") != 1:
        raise SigningError(f"Имзо ҳақиқий эмас (status {v_data.get('status')}). {v_data.get('message') or ''}")
    signers = info.get("signers") or []
    if len(signers) != 1:
        raise SigningError("Ҳужжатда айнан битта имзо бўлиши керак.")
    signer = signers[0]
    if not (signer.get("verified") and signer.get("certificateVerified") and signer.get("certificateValidAtSigningTime")):
        raise SigningError("Имзо ёки сертификат ҳақиқий эмас: " + str(signer.get("exception") or ""))
    try:
        signed_text = base64.b64decode(info.get("documentBase64") or "").decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        raise SigningError("Имзоланган ҳужжатни ўқиб бўлмади.")
    if signed_text != entry.get("document"):
        raise SigningError("Имзоланган матн шу сўров учун берилган ҳужжат эмас. Қайтадан имзоланг.")
    cert0 = (signer.get("certificate") or [{}])[0] or {}
    subject = cert0.get("subjectInfo") or {}
    tst = signer.get("timeStampInfo") or {}
    verify_result = {"mode": MODE_DOCUMENT, "timestamped": timestamped, "ocsp_checked": True,
                     "signingTime": signer.get("signingTime"), "timeStamp": {"time": tst.get("time"), "tsa": tst.get("tsa")},
                     "certificate": {k: cert0.get(k) for k in ("serialNumber", "validFrom", "validTo", "issuerName")}}
    return _store(version, user, membership, role, mode=MODE_DOCUMENT, pkcs7=pkcs7_ts, cert=cert0, subject=subject, verify_result=verify_result)

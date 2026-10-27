"""
MIB Push Service (pushservice.egov.uz) integratsiyasi — billing-urmon.uz dagi
`apps.push_service` + `apps.billing.push_signals` porti.

Shartnoma (yoki uning yer/faoliyat/imtiyoz turlari, ijarachisi, holati, yillik
summalari) o'zgarganda `schedule_contract_push` tranzaksiya commit bo'lgach Celery
vazifasini navbatga qo'yadi; vazifa `push_contract` ni chaqiradi.

Payload formati eski billing bilan aynan bir xil (MIB tomonida o'zgarish yo'q).
Autentifikatsiya: JWT RS512, `sub` = `MIB_PUSH["SYSTEM_NAME"]`.
"""
import hashlib
import json
import logging
import time
from datetime import timedelta

import jwt
import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.billing.models import Contract, MibPushLog

logger = logging.getLogger(__name__)

RECEIVE_PATH = "/v3/app/mq/receive"


def config() -> dict:
    return settings.MIB_PUSH


def is_enabled() -> bool:
    return bool(config().get("ENABLED"))


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------
def _date(value):
    return value.strftime("%Y-%m-%d") if value else None


def _type_path(type_obj) -> str:
    parts = []
    current = type_obj
    while current is not None:
        parts.append(current.name)
        current = current.parent
    return " / ".join(reversed(parts))


def _rental_period(contract: Contract) -> str:
    if contract.expired_date and contract.contract_date:
        years = contract.expired_date.year - contract.contract_date.year
        return f"{years} yil" if years > 0 else ""
    return ""


def contract_queryset():
    return Contract.objects.select_related(
        "xojalik", "xojalik__region", "region", "district", "bolim", "renter",
    ).prefetch_related(
        "activities__type", "lands__type__parent__parent", "privileges__type",
    )


def build_payload(contract: Contract) -> dict:
    """Eski billing'dagi `ContractDataPreparer.prepare_contract_data` bilan bir xil kalitlar."""
    renter = contract.renter
    region = contract.region or contract.xojalik.region
    if renter.is_legal_entity:
        renter_inn = renter.stir or renter.pinfl
    else:
        renter_inn = renter.pinfl or renter.stir
    return {
        "department_inn": contract.xojalik.inn or "",
        "department_name": contract.xojalik.name,
        "cadastral_number": contract.cadastral_number or "",
        "auction_date": _date(contract.auction_date),
        "contract_date": _date(contract.contract_date),
        "expired_date": _date(contract.expired_date),
        "rental_period": _rental_period(contract),
        "contract_number": contract.contract_number or "",
        "rent_user_type": "Yuridik" if contract.is_entity else "Jismoniy",
        "rent_user_inn": renter_inn or "",
        "rent_user_full_name": renter.full_name or "",
        "rent_user_address": renter.per_adr or "",
        "rent_user_passport": renter.passport or "",
        "rent_user_phone": renter.phone or "",
        "region_name": region.name if region else "",
        "region_code": region.code if region else "",
        "district_name": contract.district.name if contract.district else "",
        "district_code": contract.district.code if contract.district else "",
        "rent_area": str(contract.rent_area) if contract.rent_area else "0",
        "branch_name": contract.bolim.name if contract.bolim else "",
        "circle_number": contract.circle or "",
        "section_number": contract.section or "",
        "counter_number": contract.counter or "",
        "massive_number": contract.massive or "",
        "activities": {item.type.name: str(item.area) for item in contract.activities.all()},
        "lands": {_type_path(item.type): str(item.area) for item in contract.lands.all()},
        "privileges": {item.type.name: str(item.area) for item in contract.privileges.all()},
        "rent_amount": str(contract.rent_amount) if contract.rent_amount else "0",
        "canceled_date": _date(contract.canceled_date),
        "cancellation_reason": contract.cancel_reason or None,
    }


# Payload'dagi shaxsiy ma'lumot kalitlari — saqlash muddati o'tgach maskalanadi
PII_PAYLOAD_KEYS = ("rent_user_inn", "rent_user_full_name", "rent_user_address", "rent_user_passport", "rent_user_phone")


def redact_old_payloads(days: int | None = None) -> int:
    """
    Yuborilgan/muddati o'tgan loglarda (N kundan eski) payload'dagi PII maydonlari
    "***" ga almashtiriladi — hash va texnik maydonlar qoladi (audit M1/F5: ijarachi
    pasporti/JSHSHIR'i alohida jadvalda abadiy saqlanmasin). Qaytaradi: o'zgargan soni.
    """
    from django.utils import timezone
    from datetime import timedelta

    if days is None:
        days = int(settings.MIB_PUSH.get("LOG_RETENTION_DAYS", 90))
    cutoff = timezone.now() - timedelta(days=days)
    qs = MibPushLog.objects.filter(
        created_at__lt=cutoff,
        status__in=[MibPushLog.Status.SENT, MibPushLog.Status.EXPIRED, MibPushLog.Status.FAILED],
    ).exclude(payload__has_key="redacted_at")
    changed = 0
    for log in qs.iterator(chunk_size=500):
        payload = dict(log.payload or {})
        for key in PII_PAYLOAD_KEYS:
            if key in payload:
                payload[key] = "***"
        payload["redacted_at"] = timezone.now().isoformat()
        log.payload = payload
        log.save(update_fields=["payload"])
        changed += 1
    return changed


def payload_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def make_token() -> str:
    cfg = config()
    with open(cfg["PRIVATE_KEY_PATH"], "rb") as key_file:
        private_key = key_file.read()
    now = int(time.time())
    claims = {"sub": cfg["SYSTEM_NAME"], "iat": now, "exp": now + cfg["TOKEN_EXPIRY"]}
    return jwt.encode(claims, private_key, algorithm="RS512")


def _send(log: MibPushLog) -> None:
    """Bitta urinish; natija log'ga yoziladi (saqlash chaqiruvchida emas — shu yerda)."""
    cfg = config()
    log.attempts += 1
    body = {
        "correlationId": str(log.correlation_id),
        "data": log.payload,
        "dtl": _date(log.dtl),
    }
    if log.destination_subscribers:
        body["destinationSubscribers"] = log.destination_subscribers
    try:
        headers = {"Authorization": f"Bearer {make_token()}", "Content-Type": "application/json"}
        response = requests.post(cfg["BASE_URL"].rstrip("/") + RECEIVE_PATH, json=body, headers=headers, timeout=cfg["TIMEOUT"])
    except (OSError, ValueError, jwt.PyJWTError, requests.RequestException) as exc:
        # OSError: kalit fayli yo'q/o'qib bo'lmaydi; ValueError: kalit formati noto'g'ri
        log.status = MibPushLog.Status.FAILED
        log.error = f"{type(exc).__name__}: {exc}"[:2000]
        log.save(update_fields=["attempts", "status", "error", "updated_at"])
        logger.error("MIB push xatolik (%s): %s", log.contract_number, log.error)
        return

    log.http_status = response.status_code
    try:
        log.response = response.json() if response.text.strip() else None
    except ValueError:
        log.response = {"text": response.text[:2000]}
    if response.status_code in (200, 204):
        log.status = MibPushLog.Status.SENT
        log.sent_at = timezone.now()
        log.error = ""
    else:
        log.status = MibPushLog.Status.FAILED
        log.error = f"HTTP {response.status_code}: {response.text[:2000]}"
        logger.error("MIB push xatolik (%s): %s", log.contract_number, log.error)
    log.save(update_fields=["attempts", "status", "http_status", "response", "error", "sent_at", "updated_at"])


# ---------------------------------------------------------------------------
# Asosiy
# ---------------------------------------------------------------------------
def push_contract(contract_id, *, force: bool = False) -> MibPushLog | None:
    """
    Shartnomaning joriy holatini yuboradi. Oxirgi muvaffaqiyatli yuborilgan
    ma'lumot bilan bir xil bo'lsa (va `force` bo'lmasa) — yubormaydi (None).
    """
    contract = contract_queryset().filter(id=contract_id).first()
    if contract is None:
        logger.warning("MIB push: shartnoma %s topilmadi", contract_id)
        return None
    payload = build_payload(contract)
    digest = payload_hash(payload)
    if not force:
        last_sent = contract.mib_push_logs.filter(status=MibPushLog.Status.SENT).order_by("-created_at").first()
        if last_sent is not None and last_sent.payload_hash == digest:
            return None
    # Shu ma'lumotning hali yuborilmagan nusxalari — yangisi o'rnini bosadi
    contract.mib_push_logs.filter(status__in=[MibPushLog.Status.PENDING, MibPushLog.Status.FAILED]).update(
        status=MibPushLog.Status.EXPIRED, updated_at=timezone.now(),
    )
    log = MibPushLog.objects.create(
        contract=contract,
        contract_number=contract.contract_number or contract.number,
        payload=payload,
        payload_hash=digest,
        destination_subscribers=list(config()["SUBSCRIBERS"]),
        dtl=timezone.localdate() + timedelta(days=config()["DTL_DAYS"]),
    )
    _send(log)
    return log


def retry_failed() -> int:
    """Xato bilan tugagan (urinishlari tugamagan, dtl o'tmagan) yozuvlarni qayta yuboradi."""
    today = timezone.localdate()
    MibPushLog.objects.filter(status=MibPushLog.Status.FAILED, dtl__lt=today).update(
        status=MibPushLog.Status.EXPIRED, updated_at=timezone.now(),
    )
    sent = 0
    for log in MibPushLog.objects.filter(status=MibPushLog.Status.FAILED, attempts__lt=config()["MAX_ATTEMPTS"]).order_by("created_at"):
        _send(log)
        sent += log.status == MibPushLog.Status.SENT
    return sent


def schedule_contract_push(contract_id) -> None:
    """Tranzaksiya commit bo'lgach Celery vazifasini navbatga qo'yadi (o'chirilgan bo'lsa — hech narsa)."""
    if not is_enabled() or contract_id is None:
        return

    def _enqueue():
        from apps.billing.tasks import push_contract_to_mib

        try:
            push_contract_to_mib.delay(str(contract_id))
        except Exception:  # noqa: BLE001 — broker ishlamasa ham foydalanuvchi so'rovi buzilmasin
            logger.exception("MIB push navbatga qo'yilmadi: %s", contract_id)

    transaction.on_commit(_enqueue)

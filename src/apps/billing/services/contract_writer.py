"""
Shartnomani barcha bo'limlari bilan atomik saqlash (billing'dagi
ContractClass.save_contract + ContractViewSet.update/validate_and_update porti).

    save_contract(payload, user, *, instance=None, from_import=False) -> Contract

Xato: `BillingValidationError` — `{"<bo'lim>": {"<maydon>": "xabar"}}`.
Bo'limlar: contract, renter, lands, activities, privileges, action,
action_products, yearly_amounts.
"""
import uuid

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.billing.models import (
    ActivityType,
    Bolim,
    Contract,
    ContractAction,
    ContractActionProduct,
    ContractActivity,
    ContractHistory,
    ContractLand,
    ContractPrivilege,
    ContractYearlyAmount,
    District,
    LandType,
    PrivilegeType,
    Region,
    Renter,
    Xojalik,
    sync_contract_totals,
)
from apps.billing.serializers.write import (
    ActionProductWriteSerializer,
    ActionWriteSerializer,
    ActivityItemSerializer,
    BillingDateField,
    ContractWriteSerializer,
    LandItemSerializer,
    PrivilegeItemSerializer,
    RenterWriteSerializer,
    YearlyAmountWriteSerializer,
)
from apps.billing.scope import NOT_ASSIGNED_MESSAGE, billing_xojalik_ids, can_write_xojalik
from apps.billing.services import history, mib_push
from apps.billing.services.boundary import validate_contract_boundary
from apps.billing.services.errors import BillingValidationError, uz_errors
from apps.billing.services.numbering import generate_contract_number
from apps.billing.services.territory import resolve_district_code, resolve_region_code

TYPE_SECTIONS = (
    ("lands", ContractLand, LandType, LandItemSerializer),
    ("activities", ContractActivity, ActivityType, ActivityItemSerializer),
    ("privileges", ContractPrivilege, PrivilegeType, PrivilegeItemSerializer),
)
PRODUCT_FIELDS = ("product_export", "product_amount", "export_amount")
YEARLY_FIELDS = ("contract_amount", "calculated_amount", "paid_amount", "penalty_amount")


def is_uuid(value) -> bool:
    if isinstance(value, uuid.UUID):
        return True
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _clean(value):
    return str(value).strip() if value is not None else ""


def _truthy(value) -> bool:
    return value is True or str(value).strip().lower() in ("1", "true", "yes")


def find_type_by_name(type_model, name: str):
    """Tur nomi bo'yicha (katta-kichik harf va ortiqcha bo'sh joylarsiz) qidirish."""
    wanted = " ".join(_clean(name).casefold().split())
    if not wanted:
        return None
    for obj in type_model.objects.all():
        if " ".join(obj.name.casefold().split()) == wanted:
            return obj
    return None


def find_renter(pinfl, stir, exclude_id=None):
    lookup = Q()
    if pinfl:
        lookup |= Q(pinfl=pinfl)
    if stir:
        lookup |= Q(stir=stir)
    if not lookup:
        return None
    qs = Renter.objects.filter(lookup)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    if pinfl:
        by_pinfl = qs.filter(pinfl=pinfl).first()
        if by_pinfl:
            return by_pinfl
    return qs.first()


def _validate(serializer_class, section, data, instance=None, partial=False):
    serializer = serializer_class(instance=instance, data=data, partial=partial)
    if not serializer.is_valid():
        raise BillingValidationError.for_section(section, uz_errors(serializer.errors))
    return serializer


# ---------------------------------------------------------------------------
# Import: nom/kod -> ID
# ---------------------------------------------------------------------------
def ensure_xojalik_allowed(user, xojalik_id) -> None:
    """billing_user faqat o'ziga biriktirilgan xo'jalik bilan yozadi."""
    if user is not None and xojalik_id and not can_write_xojalik(user, xojalik_id):
        raise BillingValidationError.field("contract", "xojalik", NOT_ASSIGNED_MESSAGE)


def resolve_import_references(contract_data: dict, user=None) -> None:
    """Excel importdagi `xojalik_inn`/`xojalik` (nom), `bolim` (nom), `region_code`, `district_code` -> UUID."""
    errors = {}
    xojalik = None
    inn = _clean(contract_data.pop("xojalik_inn", None))
    raw_xojalik = contract_data.get("xojalik")
    has_name = raw_xojalik not in (None, "")
    if inn:
        xojalik = Xojalik.objects.filter(inn=inn).first()
    # INN topilmasa (ma'lumotnomada INN hali to'ldirilmagan bo'lishi mumkin) — nomi bo'yicha
    if xojalik is None and has_name:
        if is_uuid(raw_xojalik):
            xojalik = Xojalik.objects.filter(id=raw_xojalik).first()
        else:
            xojalik = Xojalik.objects.filter(name__iexact=_clean(raw_xojalik)).first()
    if xojalik is None:
        if inn and has_name:
            errors["xojalik_inn"] = f"INN '{inn}' yoki '{raw_xojalik}' nomi bilan xo'jalik topilmadi"
        elif inn:
            errors["xojalik_inn"] = f"INN '{inn}' bilan xo'jalik topilmadi"
        elif has_name:
            errors["xojalik"] = f"'{raw_xojalik}' nomli xo'jalik topilmadi"
        else:
            errors["xojalik_inn"] = "Xo'jalik INN yoki nomi to'ldirilishi shart"
    if xojalik is not None:
        # Doiradan tashqari xo'jalik — bo'lim yaratilmasidan oldin to'xtatiladi
        ensure_xojalik_allowed(user, xojalik.id)
        contract_data["xojalik"] = xojalik.id

    bolim = contract_data.get("bolim")
    if bolim not in (None, "") and not is_uuid(bolim):
        bolim_name = _clean(bolim)
        if xojalik is None:
            contract_data["bolim"] = None  # xo'jalik xatosi allaqachon qaytariladi
        else:
            # Ma'lumotnomada hali yo'q bo'lim (billing'da ko'proq bo'lim bor) — shu
            # xo'jalik ostida yaratiladi, shartnoma ma'lumoti yo'qolmaydi.
            found = Bolim.objects.filter(name__iexact=bolim_name, xojalik=xojalik).first()
            if found is None:
                found = Bolim.objects.create(name=bolim_name, xojalik=xojalik)
            contract_data["bolim"] = found.id
    elif bolim == "":
        contract_data["bolim"] = None

    region = None
    region_code = _clean(contract_data.pop("region_code", None))
    if region_code:
        region = resolve_region_code(region_code)
        if region is None:
            errors["region_code"] = f"'{region_code}' kodli viloyat mavjud emas"
        else:
            contract_data["region"] = region.id
    elif contract_data.get("region") and is_uuid(contract_data["region"]):
        region = Region.objects.filter(id=contract_data["region"]).first()

    district_code = _clean(contract_data.pop("district_code", None))
    if district_code:
        if region is None and xojalik is not None and not region_code:
            region = xojalik.region
        district = resolve_district_code(district_code, region)
        if district is None:
            errors["district_code"] = f"'{district_code}' kodli tuman mavjud emas yoki viloyatga mos kelmaydi"
        else:
            contract_data["district"] = district.id

    for key in ("region", "district", "bolim"):
        if contract_data.get(key) == "":
            contract_data[key] = None
    if errors:
        raise BillingValidationError.for_section("contract", errors)


# ---------------------------------------------------------------------------
# Ijarachi
# ---------------------------------------------------------------------------
def renter_in_scope(renter: Renter, instance: Contract | None, user) -> bool:
    return _renter_in_scope(renter, instance, user)


def _renter_in_scope(renter: Renter, instance: Contract | None, user) -> bool:
    """billing_user faqat o'z xo'jaliklaridagi (yoki shartnomasiz) ijarachini tahrirlaydi."""
    ids = billing_xojalik_ids(user)
    if ids is None or (instance is not None and instance.renter_id == renter.id):
        return True
    contracts = Contract.objects.filter(renter=renter)
    return not contracts.exists() or contracts.filter(xojalik_id__in=ids).exists()


def resolve_renter(data, instance: Contract | None, user) -> Renter | None:
    """
    `id` berilsa — shu ijarachi yangilanadi; yaratishda pinfl/stir bo'yicha
    mavjud topiladi (yoki yaratiladi); tahrirlashda joriy ijarachi yangilanadi,
    JSHSHIR/INN boshqa shaxsnikiga o'zgarsa va ijarachi boshqa shartnomalarda
    ham bo'lsa — faqat shu shartnoma yangi (yoki mavjud) ijarachiga ko'chadi.
    """
    if data is None:
        if instance is None:
            raise BillingValidationError.field("renter", "pinfl", "Ijarachi ma'lumotlari to'ldirilishi shart")
        return None
    if not isinstance(data, dict):
        raise BillingValidationError.field("renter", "non_field_errors", "Ijarachi obyekt bo'lishi kerak")

    data = dict(data)
    renter_id = data.pop("id", None)
    pinfl = _clean(data.get("pinfl")) or None
    stir = _clean(data.get("stir")) or None

    def _save(serializer, target=None):
        obj = serializer.save()
        if target is None:
            obj.created_by = user
        obj.updated_by = user
        obj.save(update_fields=["created_by", "updated_by"] if target is None else ["updated_by"])
        return obj

    if renter_id:
        renter = Renter.objects.filter(id=renter_id).first() if is_uuid(renter_id) else None
        if renter is None or not _renter_in_scope(renter, instance, user):
            raise BillingValidationError.field("renter", "id", "Ijarachi topilmadi")
        serializer = _validate(RenterWriteSerializer, "renter", data, instance=renter, partial=True)
        return _save(serializer, renter)

    if instance is None:
        existing = find_renter(pinfl, stir)
        if existing:
            return existing
        serializer = _validate(RenterWriteSerializer, "renter", data)
        return _save(serializer)

    current = instance.renter
    identity_changed = ("pinfl" in data and pinfl != current.pinfl) or ("stir" in data and stir != current.stir)
    is_shared = Contract.objects.filter(renter=current).exclude(id=instance.id).exists()
    target = current
    if identity_changed and is_shared and (pinfl or stir):
        target = find_renter(pinfl, stir, exclude_id=current.id)
        if target is None:
            serializer = _validate(RenterWriteSerializer, "renter", data)
            return _save(serializer)
    serializer = _validate(RenterWriteSerializer, "renter", data, instance=target, partial=True)
    return _save(serializer, target)


# ---------------------------------------------------------------------------
# Bo'limlar
# ---------------------------------------------------------------------------
def _ensure_list(section, items):
    if items is None:
        return None
    if not isinstance(items, list):
        raise BillingValidationError.field(section, "non_field_errors", "Ro'yxat bo'lishi kerak")
    return items


def save_type_items(section, model, type_model, serializer_class, contract: Contract, items, is_create: bool):
    items = _ensure_list(section, items)
    if items is None:
        return
    errors = {}
    for index, raw in enumerate(items):
        item = dict(raw or {})
        label = f"{index + 1}-yozuv"
        if _truthy(item.get("delete")):
            if is_create:
                continue
            obj = model.objects.filter(id=item["id"], contract=contract).first() if is_uuid(item.get("id")) else None
            if obj is None:
                errors[label] = "Berilgan ID raqamli yozuv bu shartnomada topilmadi"
                continue
            obj.delete()
            continue
        type_value = item.get("type")
        if isinstance(type_value, str) and not is_uuid(type_value):
            label = type_value
            found = find_type_by_name(type_model, type_value)
            if found is None:
                errors[label] = f"'{type_value}' nomli tur tizimda mavjud emas"
                continue
            item["type"] = found.id
        serializer = serializer_class(data=item)
        if not serializer.is_valid():
            errors[label] = "; ".join(f"{k}: {v}" for k, v in uz_errors(serializer.errors).items())
            continue
        validated = serializer.validated_data
        item_id = None if is_create else validated.get("id")
        if not item_id:
            model.objects.create(contract=contract, type=validated["type"], area=validated["area"])
            continue
        obj = model.objects.filter(id=item_id, contract=contract).first()
        if obj is None:
            errors[label] = "Berilgan ID raqamli yozuv bu shartnomada topilmadi"
            continue
        obj.type = validated["type"]
        obj.area = validated["area"]
        obj.save(update_fields=["type", "area", "updated_at"])
    if errors:
        raise BillingValidationError.for_section(section, errors)


def save_action(contract: Contract, action_data, products, is_create: bool):
    """Bajarilgan ishlar (bitta yozuv) va eksport mahsulotlari."""
    products = _ensure_list("action_products", products)
    if action_data is None and products is None:
        return
    action = contract.actions.first()
    if action_data is not None:
        if not isinstance(action_data, dict):
            raise BillingValidationError.field("action", "non_field_errors", "Obyekt bo'lishi kerak")
        payload = {k: v for k, v in action_data.items() if k in ("vacancy", "own_investment")}
        serializer = _validate(ActionWriteSerializer, "action", payload, instance=action, partial=action is not None)
        action = serializer.save(contract=contract) if action is None else serializer.save()
    if products is None:
        return
    if action is None:
        action = ContractAction.objects.create(contract=contract)

    errors = {}
    for index, raw in enumerate(products):
        item = dict(raw or {})
        label = _clean(item.get("product_export")) or f"{index + 1}-yozuv"
        has_value = any(_clean(item.get(f)) for f in PRODUCT_FIELDS)
        if not has_value and not item.get("id"):
            continue
        serializer = ActionProductWriteSerializer(data=item)
        if not serializer.is_valid():
            errors[label] = "; ".join(f"{k}: {v}" for k, v in uz_errors(serializer.errors).items())
            continue
        validated = dict(serializer.validated_data)
        item_id = validated.pop("id", None)
        delete = validated.pop("delete", False)
        if is_create or not item_id:
            if not delete and has_value:
                ContractActionProduct.objects.create(action=action, **validated)
            continue
        obj = ContractActionProduct.objects.filter(id=item_id, action__contract=contract).first()
        if obj is None:
            errors[label] = "Berilgan ID raqamli yozuv bu shartnomada topilmadi"
            continue
        if delete or not has_value:
            obj.delete()
            continue
        for key, value in validated.items():
            setattr(obj, key, value)
        obj.save()
    if errors:
        raise BillingValidationError.for_section("action_products", errors)


def save_yearly_amounts(contract: Contract, rows) -> bool:
    """`yearly_amounts` -> yil bo'yicha update_or_create. Qator bo'lsa True."""
    rows = _ensure_list("yearly_amounts", rows)
    if rows is None:
        return False
    errors = {}
    validated_rows = []
    for index, raw in enumerate(rows):
        serializer = YearlyAmountWriteSerializer(data=dict(raw or {}))
        if not serializer.is_valid():
            year = (raw or {}).get("year") if isinstance(raw, dict) else None
            for field, message in uz_errors(serializer.errors).items():
                errors[f"{year}_{field}" if year else f"{index + 1}-yozuv"] = message
            continue
        validated_rows.append(serializer.validated_data)
    if errors:
        raise BillingValidationError.for_section("yearly_amounts", errors)
    for row in validated_rows:
        ContractYearlyAmount.objects.update_or_create(
            contract=contract, year=row["year"], defaults={f: row[f] for f in YEARLY_FIELDS},
        )
    return bool(validated_rows)


# ---------------------------------------------------------------------------
# Asosiy
# ---------------------------------------------------------------------------
def save_contract(payload, user, *, instance: Contract | None = None, from_import: bool = False) -> Contract:
    if not isinstance(payload, dict):
        raise BillingValidationError.field("contract", "non_field_errors", "So'rov tanasi obyekt bo'lishi kerak")
    is_create = instance is None
    contract_data = payload.get("contract")
    if contract_data is None:
        contract_data = {} if is_create else None
    if contract_data is not None and not isinstance(contract_data, dict):
        raise BillingValidationError.field("contract", "non_field_errors", "Obyekt bo'lishi kerak")

    with transaction.atomic():
        import_status = None
        if contract_data is not None:
            contract_data = dict(contract_data)
            contract_data.pop("status", None)
            canceled_date = contract_data.pop("canceled_date", None)
            cancel_reason = contract_data.pop("cancel_reason", None)
            if from_import:
                resolve_import_references(contract_data, user)
                if canceled_date or _clean(cancel_reason):
                    import_status = (canceled_date, _clean(cancel_reason) or None)
            # Doira tekshiruvi boshqa validatsiyadan oldin (masalan, bo'lim boshqa xo'jalikka tegishli xatosi)
            if is_uuid(contract_data.get("xojalik")):
                ensure_xojalik_allowed(user, contract_data["xojalik"])

        renter = resolve_renter(payload.get("renter"), instance, user)

        old_snapshot = history.snapshot(instance) if instance else None
        contract = instance
        if contract_data is not None:
            serializer = _validate(ContractWriteSerializer, "contract", contract_data, instance=instance, partial=not is_create)
            validated = serializer.validated_data
            xojalik = validated.get("xojalik") or (instance.xojalik if instance else None)
            if xojalik is not None:
                ensure_xojalik_allowed(user, xojalik.id)
            if validated.get("boundary_geojson"):
                error = validate_contract_boundary(instance, xojalik, validated["boundary_geojson"])
                if error:
                    raise BillingValidationError.field("contract", "boundary_geojson", error)
            if is_create:
                contract = Contract(**validated)
                contract.renter = renter
                contract.number = generate_contract_number(xojalik)
                contract.created_by = user
                if not contract.expired_date:
                    contract.expired_date = contract.contract_date + relativedelta(years=1)
            else:
                for key, value in validated.items():
                    setattr(contract, key, value)

        if import_status:
            canceled_date, cancel_reason = import_status
            parsed_date = None
            if canceled_date:
                try:
                    parsed_date = BillingDateField().run_validation(canceled_date)
                except DRFValidationError as exc:
                    raise BillingValidationError.field("contract", "canceled_date", uz_errors(exc.detail, "canceled_date")) from exc
            contract.status = Contract.Status.INACTIVE
            contract.canceled_date = parsed_date
            contract.cancel_reason = cancel_reason

        if renter is not None:
            contract.renter = renter
        contract.is_entity = contract.renter.is_legal_entity
        contract.updated_by = user
        contract._history_user = user
        contract.save()

        for section, model, type_model, serializer_class in TYPE_SECTIONS:
            save_type_items(section, model, type_model, serializer_class, contract, payload.get(section), is_create)
        save_action(contract, payload.get("action"), payload.get("action_products"), is_create)
        save_yearly_amounts(contract, payload.get("yearly_amounts"))
        if sync_contract_totals(contract.id):
            contract.refresh_from_db()

        new_snapshot = history.snapshot(contract)
        if from_import:
            reason, data = ContractHistory.Reason.IMPORTED, {"new": new_snapshot}
        elif is_create:
            reason, data = ContractHistory.Reason.CREATED, {"new": new_snapshot}
        else:
            reason, data = ContractHistory.Reason.UPDATED, {"changes": history.diff(old_snapshot, new_snapshot)}
        history.record(contract, user, reason, data)
        mib_push.schedule_contract_push(contract.id)
    return contract


def change_status(contract: Contract, user, status: str, cancel_reason: str | None) -> Contract:
    """Holatni o'zgartirish: inactive -> sabab + bugungi sana; active -> cancel maydonlari tozalanadi."""
    from django.utils import timezone

    old = history.snapshot(contract)
    contract.status = status
    if status == Contract.Status.INACTIVE:
        contract.cancel_reason = (cancel_reason or "").strip()
        contract.canceled_date = timezone.localdate()
    else:
        contract.cancel_reason = None
        contract.canceled_date = None
    contract.updated_by = user
    contract._history_user = user
    contract.save(update_fields=["status", "cancel_reason", "canceled_date", "updated_by", "updated_at"])
    history.record(contract, user, ContractHistory.Reason.STATUS_CHANGED, {"changes": history.diff(old, history.snapshot(contract))})
    mib_push.schedule_contract_push(contract.id)
    return contract


def change_renter(contract: Contract, user, renter: Renter) -> Contract:
    old = history.snapshot(contract)
    contract.renter = renter
    contract.is_entity = renter.is_legal_entity
    contract.updated_by = user
    contract._history_user = user
    contract.save(update_fields=["renter", "is_entity", "updated_by", "updated_at"])
    history.record(contract, user, ContractHistory.Reason.RENTER_CHANGED, {"changes": history.diff(old, history.snapshot(contract))})
    mib_push.schedule_contract_push(contract.id)
    return contract


def update_yearly_amounts(contract: Contract, user, rows) -> Contract:
    with transaction.atomic():
        old = history.snapshot(contract)
        save_yearly_amounts(contract, rows if rows is not None else [])
        sync_contract_totals(contract.id)
        contract.refresh_from_db()
        history.record(contract, user, ContractHistory.Reason.YEARLY_UPDATED, {"changes": history.diff(old, history.snapshot(contract))})
        mib_push.schedule_contract_push(contract.id)
    return contract

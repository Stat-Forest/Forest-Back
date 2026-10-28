"""Buyurtmaning o'zgarmas nusxasi — versiya va hujjat uchun (TZ §11.2)."""
from decimal import Decimal

from apps.yashil.models import STATE_LABELS_CYR
from apps.yashil.services.units import UNIT_LABELS


def _dec(value):
    if value is None:
        return None
    return format(Decimal(value).normalize(), "f")


def build_snapshot(order, membership=None) -> dict:
    mahalla = order.mahalla
    supplier = getattr(order.supplier_org, "supplier_profile", None)
    user = membership.user if membership else None
    lines = []
    for idx, line in enumerate(order.lines.select_related("catalog_item").order_by("position", "created_at"), start=1):
        item = line.catalog_item
        lines.append({
            "n": idx,
            "catalog_id": str(item.id),
            "code": item.code,
            "name_cyr": item.name_cyr,
            "name_lat": item.name_lat,
            "attributes": item.attributes or {},
            "attrs_note": line.attrs_note,
            "item_type": item.item_type,
            "category": item.category,
            "qty": _dec(line.qty),
            "unit": item.unit,
            "unit_cyr": UNIT_LABELS.get(item.unit, (item.unit, item.unit))[0],
        })
    return {
        "order_id": str(order.id),
        "number": order.number,
        "version_no": order.version_no,
        "state": order.state,
        "state_cyr": STATE_LABELS_CYR.get(order.state, order.state),
        "route": order.route,
        "title": order.title,
        "mahalla": {
            "id": str(mahalla.id), "name": mahalla.name, "source_code": mahalla.source_code,
            "region": mahalla.region.name, "district": mahalla.district.name, "address": mahalla.address,
        },
        "supplier": {
            "id": str(order.supplier_org_id),
            "name": supplier.display_name if supplier else order.supplier_org.name,
            "supplier_type": supplier.supplier_type if supplier else order.route,
            "stir": (supplier.stir if supplier and supplier.stir else (str(order.supplier_org.stir) if order.supplier_org.stir else "")),
        },
        "union_unit": {"id": str(order.union_unit_id), "name": order.union_unit.name} if order.union_unit_id else None,
        "object_type": {"code": order.object_type.code, "name_cyr": order.object_type.name_cyr} if order.object_type_id else None,
        "object_note": order.object_note,
        "season": {"year": order.season.year, "kind": order.season.kind, "label_cyr": order.season.label_cyr} if order.season_id else None,
        "address": order.address,
        "lat": _dec(order.lat),
        "lon": _dec(order.lon),
        "area_ha": _dec(order.area_ha),
        "area_calc_ha": _dec(order.area_calc_ha),
        "area_note": order.area_note,
        "polygon": order.polygon,
        "water_source": order.water_source,
        "contact_person": order.contact_person,
        "extra_info": order.extra_info,
        "base_seedlings": order.base_seedlings,
        "problem_note": order.problem_note,
        "linked_order": order.linked_order.display_number if order.linked_order_id else None,
        "repeat_reason": order.repeat_reason,
        "lines": lines,
        "attachments": [
            {"id": str(a.id), "name": a.original_name, "size": a.size, "kind": a.kind}
            for a in order.attachments.all()
        ],
        "signer": {
            "user_id": str(user.id) if user else None,
            "full_name": f"{user.last_name} {user.first_name} {user.father_name}".strip() if user else "",
            "position": membership.position_title if membership else "",
            "phone": membership.phone if membership else "",
            "authority": f"{membership.authority_doc_number} {membership.authority_doc_date or ''}".strip() if membership else "",
        },
    }

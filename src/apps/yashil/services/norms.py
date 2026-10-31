"""
Buyurtma validatsiyasi (TZ §4, §5.1, §5.3; javoblar В2–В4, Г4):
- qatorlar: kamida bitta, katalog faol va yo'nalishga mos, takror yo'q, miqdor birlik aniqligida;
- o'g'it/mulcha: asos ko'chatlar soni majburiy, NormRule `max_per_tup` (5 / 4 kg);
- xizmat: muammo tavsifi majburiy;
- yuborishda: nom, manzil, xarita nuqtasi, maydon; poligon maydoni 5% dan ko'p farq qilsa izoh;
- takroriy buyurtma: sabab majburiy.
Qoidalar jadvali bo'sh bo'lsa (NormRule yo'q) — meyor tekshiruvi o'tkazilmaydi (javob В2).
"""
from datetime import date
from decimal import Decimal

from apps.billing.models import XojalikLocation
from apps.yashil.models import CatalogItem, NormRule
from apps.yashil.services.units import quantity_error

AREA_TOLERANCE_PERCENT = Decimal("5")
NORM_CATEGORIES = {CatalogItem.Category.FERTILIZER, CatalogItem.Category.MULCH}
# O'zbekistonni o'rab turgan to'rtburchak [[janub, g'arb], [shimol, sharq]] — aniq chegara emas,
# xaritada adashib boshqa davlat yoki 0/0 bosilganini ushlaydi
UZ_BOUNDS = [[37.1, 55.9], [45.6, 73.2]]


def inside_uzbekistan(lat, lon) -> bool:
    (south, west), (north, east) = UZ_BOUNDS
    return south <= float(lat) <= north and west <= float(lon) <= east


def region_bounds(region_id):
    """Viloyatdagi o'rmon xo'jaliklari hududlarini qamrovchi to'rtburchak (buyurtma xaritasini ochish uchun)."""
    boxes = []
    for b in XojalikLocation.objects.filter(region_id=region_id).values_list("bounds", flat=True):
        try:
            (s, w), (n, e) = b
            boxes.append((float(s), float(w), float(n), float(e)))
        except (TypeError, ValueError):
            continue
    if not boxes:
        return None
    (south, west), (north, east) = UZ_BOUNDS
    return [[max(min(x[0] for x in boxes), south), max(min(x[1] for x in boxes), west)],
            [min(max(x[2] for x in boxes), north), min(max(x[3] for x in boxes), east)]]


class OrderValidationError(Exception):
    def __init__(self, message: str, *, code: str = "validation", field: str | None = None, index: int | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.field = field
        self.index = index


def active_norm(category: str, item: CatalogItem | None = None, on: date | None = None) -> NormRule | None:
    on = on or date.today()
    qs = NormRule.objects.filter(effective_from__lte=on).exclude(effective_to__lt=on)
    if item is not None:
        rule = qs.filter(applies_to_item=item).order_by("-version").first()
        if rule:
            return rule
    return qs.filter(applies_to_category=category, applies_to_item__isnull=True).order_by("-version").first()


def validate_lines(lines, *, supplier_type: str, base_seedlings: int | None = None, problem_note: str = "", on: date | None = None):
    """`lines`: [{"catalog_item": CatalogItem, "qty": Decimal}, ...]. Xato bo'lsa OrderValidationError."""
    if not lines:
        raise OrderValidationError("Камида битта маҳсулот ёки хизмат сатри бўлиши керак", code="lines_required", field="lines")
    seen = set()
    for idx, line in enumerate(lines):
        item: CatalogItem = line["catalog_item"]
        qty = Decimal(str(line["qty"]))
        if not item.is_active:
            raise OrderValidationError(f"{item.name_cyr}: каталогда фаол эмас", code="line_inactive", field="lines", index=idx)
        if item.supplier_type != supplier_type:
            raise OrderValidationError(f"{item.name_cyr}: танланган етказиб берувчи йўналишига кирмайди", code="line_supplier_mismatch", field="lines", index=idx)
        if item.pk in seen:
            raise OrderValidationError(f"{item.name_cyr}: такрор сатр — бирлаштиринг", code="line_duplicate", field="lines", index=idx)
        seen.add(item.pk)
        err = quantity_error(qty, item.unit)
        if err:
            raise OrderValidationError(f"{item.name_cyr}: {err}", code="line_qty", field="lines", index=idx)
        if item.category in NORM_CATEGORIES:
            if not base_seedlings:
                raise OrderValidationError("Ўғит/мульча учун асос бўладиган кўчатлар сони мажбурий", code="base_seedlings_required", field="base_seedlings")
            rule = active_norm(item.category, item, on)
            max_per_tup = (rule.params or {}).get("max_per_tup") if rule else None
            if max_per_tup is not None:
                limit = Decimal(str(max_per_tup)) * Decimal(base_seedlings)
                if qty > limit:
                    raise OrderValidationError(
                        f"{item.name_cyr}: {base_seedlings} туп учун кўпи билан {limit.normalize()} {item.unit} ({max_per_tup} {item.unit}/туп)",
                        code="norm_violation", field="lines", index=idx,
                    )
        if item.item_type == CatalogItem.ItemType.SERVICE and not (problem_note or "").strip():
            raise OrderValidationError("Хизмат учун муаммо тавсифи мажбурий", code="problem_note_required", field="problem_note")


def validate_for_submit(order) -> None:
    """Imzolab yuborishdan oldingi to'liq tekshiruv (serverda, TZ §6.1-2)."""
    if not (order.title or "").strip():
        raise OrderValidationError("Буюртма номи мажбурий", code="required", field="title")
    if not (order.address or "").strip():
        raise OrderValidationError("Ҳудуд манзили мажбурий", code="required", field="address")
    if order.lat is None or order.lon is None:
        raise OrderValidationError("Харитада жойлашув нуқтаси тасдиқланмаган", code="map_required", field="lat")
    if not inside_uzbekistan(order.lat, order.lon):
        raise OrderValidationError("Жойлашув нуқтаси Ўзбекистон ҳудудидан ташқарида — харитада қайта белгиланг",
                                   code="map_outside", field="lat")
    if order.area_ha is None or order.area_ha <= 0:
        raise OrderValidationError("Майдон (га) мусбат сон бўлиши керак", code="required", field="area_ha")
    if order.object_type_id and order.object_type.requires_note and not (order.object_note or "").strip():
        raise OrderValidationError("Объект тури «Бошқа» учун изоҳ мажбурий", code="required", field="object_note")
    if order.area_calc_ha and order.area_calc_ha > 0:
        diff = abs(order.area_ha - order.area_calc_ha) / order.area_calc_ha * Decimal(100)
        if diff > AREA_TOLERANCE_PERCENT and not (order.area_note or "").strip():
            raise OrderValidationError(
                f"Киритилган майдон полигондан {diff.quantize(Decimal('0.1'))}% фарқ қилади — асосни ёзинг",
                code="area_mismatch", field="area_note",
            )
    if order.linked_order_id and not (order.repeat_reason or "").strip():
        raise OrderValidationError("Такрорий буюртма учун сабаб мажбурий", code="required", field="repeat_reason")
    lines = [{"catalog_item": l.catalog_item, "qty": l.qty} for l in order.lines.select_related("catalog_item")]
    validate_lines(lines, supplier_type=order.route, base_seedlings=order.base_seedlings, problem_note=order.problem_note)

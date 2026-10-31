"""
Import uchun namuna .xlsx: sarlavha (import qabul qiladigan ustun nomlari) va namuna qator.
Matnlar xabar emas — Excel ustun nomlari va namuna qiymatlar (tarjima katalogiga kirmaydi).
"""
import io

from openpyxl import Workbook
from openpyxl.styles import Font


def _template_rows(kind: str, supplier_type: str | None = None) -> tuple[list[str], list[list]]:
    """Sarlavha (import qabul qiladigan nomlar) va namuna qator — iloji bo'lsa bazadagi haqiqiy kodlar bilan."""
    from apps.billing.models import District
    from apps.yashil.models import CatalogItem, Mahalla, SupplierProfile, UnionUnit

    if kind == "mahallas":
        d = District.objects.select_related("region").order_by("code").first()
        return (["Маҳалла коди", "Вилоят коди", "Туман коди", "Маҳалла номи", "Манзил", "Фаол", "Амал бошланиши", "Амал тугаши"],
                [["", d.region.code if d else "1703", d.code if d else "1703203", "Намуна маҳалласи", "Марказий кўча, 1",
                  "ҳа", "2026-01-01", ""]])
    mahalla = Mahalla.objects.filter(is_active=True).order_by("source_code").first()
    mahalla_code = mahalla.source_code if mahalla and mahalla.source_code else "1703203-001"
    if kind == "assignments":
        forest = SupplierProfile.objects.filter(supplier_type=SupplierProfile.SupplierType.FOREST).select_related("organization").first()
        return (["Маҳалла коди", "Хўжалик", "Амал бошланиши", "Амал тугаши"],
                [[mahalla_code, forest.organization.name if forest else "Андижон давлат ўрмон хўжалиги", "2026-01-01", ""]])
    if kind == "routes":
        unit = UnionUnit.objects.filter(is_active=True).order_by("name").first()
        return (["Маҳалла коди", "Уюшма бўлинмаси", "Амал бошланиши", "Амал тугаши"],
                [[mahalla_code, unit.name if unit else "Андижон тумани маҳаллалар уюшмаси", "2026-01-01", ""]])
    if kind == "calendar":
        return (["Сана", "Тури", "Изоҳ"],
                [["2027-03-21", "байрам", "Наврўз"], ["2027-03-27", "иш куни", "Кўчирилган иш куни"]])
    if kind == "opening":
        items = CatalogItem.objects.filter(is_active=True).order_by("supplier_type", "order", "code")
        item = (items.filter(supplier_type=supplier_type) if supplier_type else items).first()
        return (["Каталог коди", "Миқдор", "Ҳужжат рақами", "Ҳужжат санаси", "Изоҳ"],
                [[item.code if item else "ASH", 100, "1-сон далолатнома", "2026-10-01", ""]])
    raise ValueError(kind)


def template_xlsx(kind: str, supplier_type: str | None = None) -> bytes:
    headers, rows = _template_rows(kind, supplier_type)
    wb = Workbook()
    ws = wb.active
    ws.title = "Import"
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for r in rows:
        ws.append(r)
    for col, title in zip(ws.columns, headers):
        ws.column_dimensions[col[0].column_letter].width = max(14, len(title) + 4)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

"""
Hujjat PDF'i (TZ §11, §12, §13.3) — reportlab platypus, repo ichidagi DejaVu shrifti
(kirill; Docker image'da tizim shriftlari yo'q), QR — reportlab'ning o'z barcode moduli.

    render_pdf(version) -> bytes
    ensure_pdf(version) -> FieldFile     (yo'q bo'lsa yaratib `pdf_file` ga saqlaydi)

Imzodan keyin `documents.after_signature` `pdf_file` ni o'chiradi — keyingi so'rovda
imzo bloki bilan qayta yaratiladi. Imzolanmagan/qisman imzolangan nusxada
«ИМЗОЛАНМАГАН НУСХА» belgisi bo'ladi.
"""
import io
from pathlib import Path

from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.yashil.models import Document, DocumentVersion, Signature
from apps.yashil.services.documents import ROLE_LABELS_CYR, missing_roles, verify_url

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
FONT = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"
_registered = False


def _register_fonts():
    global _registered
    if _registered:
        return
    pdfmetrics.registerFont(TTFont(FONT, str(FONT_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONT_DIR / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_BOLD, italic=FONT, boldItalic=FONT_BOLD)
    _registered = True


def _styles():
    base = ParagraphStyle("base", fontName=FONT, fontSize=10, leading=14)
    return {
        "base": base,
        "small": ParagraphStyle("small", parent=base, fontSize=8, leading=10, textColor=colors.HexColor("#555555")),
        "right": ParagraphStyle("right", parent=base, alignment=TA_RIGHT),
        "center": ParagraphStyle("center", parent=base, alignment=TA_CENTER),
        "title": ParagraphStyle("title", parent=base, fontName=FONT_BOLD, fontSize=15, leading=19, alignment=TA_CENTER, spaceBefore=6, spaceAfter=4),
        "h": ParagraphStyle("h", parent=base, fontName=FONT_BOLD),
        "cell": ParagraphStyle("cell", parent=base, fontSize=9, leading=11),
        "cellh": ParagraphStyle("cellh", parent=base, fontName=FONT_BOLD, fontSize=9, leading=11),
        "warn": ParagraphStyle("warn", parent=base, fontName=FONT_BOLD, textColor=colors.HexColor("#b45309"), alignment=TA_CENTER),
    }


def _esc(value) -> str:
    return str(value if value not in (None, "") else "—").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _lines_table(header, rows, widths):
    st = _styles()
    data = [[Paragraph(h, st["cellh"]) for h in header]] + [[Paragraph(_esc(c), st["cell"]) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef2")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
    ]))
    return t


def _qr_drawing(url: str, size=26 * mm):
    widget = qr.QrCodeWidget(url, barLevel="M")
    x0, y0, x1, y1 = widget.getBounds()
    d = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    d.add(widget)
    return d


def _sig_text(sig) -> str:
    if sig is None:
        return "<b>Имзо кутилмоқда</b>"
    when = timezone.localtime(sig.signed_at).strftime("%d.%m.%Y %H:%M")
    return f"{_esc(sig.signer_cn)} · {when} · E-IMZO ({sig.mode}) · <b>Ҳақиқий</b>"


def _signature_block(version: DocumentVersion, roles):
    st = _styles()
    sigs = {s.role: s for s in version.signatures.filter(is_valid=True)}
    rows = [[Paragraph("<b>Электрон тасдиқ</b>", st["cell"]), ""]]
    for role in roles:
        rows.append([Paragraph(f"{ROLE_LABELS_CYR[role]}:", st["cell"]), Paragraph(_sig_text(sigs.get(role)), st["cell"])])
    status = "Тўлиқ имзоланган" if not missing_roles(version) else "Тўлиқ тасдиқланмаган"
    rows.append([Paragraph("Ҳолат:", st["cell"]), Paragraph(f"<b>{status}</b>", st["cell"])])
    rows.append([Paragraph("Ҳужжат IDси:", st["cell"]), Paragraph(_esc(version.qr_token), st["cell"])])
    rows.append([Paragraph("Текшириш:", st["cell"]), Paragraph(_esc(verify_url(version.qr_token)), st["small"])])
    inner = Table(rows, colWidths=[32 * mm, 108 * mm])
    inner.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("SPAN", (0, 0), (1, 0))]))
    outer = Table([[inner, _qr_drawing(verify_url(version.qr_token))]], colWidths=[142 * mm, 30 * mm])
    outer.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#bbbbbb")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return KeepTogether([outer])


def _unsigned_banner(version: DocumentVersion, story):
    if version.status != DocumentVersion.Status.SIGNED:
        story.append(Paragraph("ИМЗОЛАНМАГАН НУСХА — ҳужжат тўлиқ тасдиқланмаган", _styles()["warn"]))
        story.append(Spacer(1, 4))


def _order_form_story(version: DocumentVersion):
    c, st, story = version.content, _styles(), []
    _unsigned_banner(version, story)
    story.append(Paragraph(f"{_esc(c.get('supplier_name'))}га<br/>{_esc(c.get('region'))}, {_esc(c.get('district'))}даги<br/>{_esc(c.get('mahalla_name'))} номидан", st["right"]))
    story.append(Paragraph("БУЮРТМАНОМА", st["title"]))
    story.append(Paragraph(f"Рақами: <b>{_esc(c.get('number'))}</b> &nbsp;&nbsp; Сана: <b>{_esc(c.get('date'))}</b> &nbsp;&nbsp; Версия: <b>{_esc(c.get('version_no'))}</b>", st["center"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Ўзбекистон Республикаси Президентининг 2026 йил 23 сентябрдаги ПФ-206-сон Фармонига асосан {_esc(c.get('full_address'))} манзилида, "
        f"{_esc(c.get('point'))} жойлашув нуқтасидаги {_esc(c.get('area_ha'))} гектар ҳудудда «Яшил маҳалла» ташкил этиш учун қуйидаги "
        f"{_esc(c.get('subject_phrase'))} бўйича буюртма берилмоқда.", st["base"]))
    extra = []
    if c.get("object_type"):
        extra.append(f"Объект тури: {_esc(c['object_type'])}.")
    if c.get("season"):
        extra.append(f"Мавсум: {_esc(c['season'])}.")
    story.append(Paragraph(f"Объект номи: {_esc(c.get('title'))}. {' '.join(extra)}<br/>Жойлашув нуқтаси: {_esc(c.get('point'))} (WGS84).<br/>Етказиб берувчи: {_esc(c.get('supplier_name'))}.", st["base"]))
    story.append(Spacer(1, 4))
    rows = [[l["n"], f"{l['name']}" + (f" ({l['attrs']})" if l.get("attrs") else ""), l["qty"], l["unit"]] for l in c.get("lines", [])]
    story.append(_lines_table(["Т/р", "Маҳсулот ёки хизмат номи ва хусусияти", "Миқдор", "Ўлчов бирлиги"], rows, [12 * mm, 108 * mm, 24 * mm, 28 * mm]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Қўшимча маълумот: {_esc(c.get('extra_info'))}.<br/>Иловалар: {_esc(c.get('attachments_text'))}.", st["base"]))
    s = c.get("signer") or {}
    authority = f", {_esc(s['authority'])}" if s.get("authority") else ""
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Буюртма берувчи</b><br/>Маҳалла: {_esc(c.get('mahalla_name'))}.<br/>Ваколатли шахс: {_esc(s.get('full_name'))}.<br/>"
                           f"Лавозими ва ваколат асоси: {_esc(s.get('position'))}{authority}.<br/>Алоқа рақами: {_esc(s.get('phone'))}.", st["base"]))
    story.append(Spacer(1, 8))
    story.append(_signature_block(version, [Signature.Role.MAHALLA]))
    return story


def _act_story(version: DocumentVersion):
    c, st, story = version.content, _styles(), []
    _unsigned_banner(version, story)
    story.append(Paragraph("ТОПШИРИШ-ҚАБУЛ ҚИЛИШ ДАЛОЛАТНОМАСИ", st["title"]))
    partial = " &nbsp;&nbsp; <b>Қисман</b>" if c.get("is_partial") else ""
    story.append(Paragraph(f"Рақами: <b>{_esc(c.get('number'))}</b> &nbsp;&nbsp; Сана: <b>{_esc(c.get('date'))}</b> &nbsp;&nbsp; Версия: <b>{_esc(c.get('version_no'))}</b>{partial}", st["center"]))
    story.append(Paragraph(f"Жой: {_esc(c.get('place'))}", st["base"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Ўзбекистон Республикаси Президентининг 2026 йил 23 сентябрдаги ПФ-206-сон Фармони ва {_esc(c.get('order_date'))}даги "
        f"{_esc(c.get('order_number'))} сонли буюртманомага асосан {_esc(c.get('supplier_name'))} томонидан {_esc(c.get('mahalla_name'))}га "
        f"{_esc(c.get('object_text'))} учун қуйидаги маҳсулотлар етказиб берилди ва (ёки) хизматлар кўрсатилди.", st["base"]))
    story.append(Spacer(1, 4))
    rows = [[l["n"], f"{l['name']}" + (f" ({l['attrs']})" if l.get("attrs") else ""), l["qty"], l["unit"]] for l in c.get("lines", [])]
    story.append(_lines_table(["Т/р", "Маҳсулот ёки хизмат номи", "Ушбу акт бўйича миқдор", "Бирлик"], rows, [12 * mm, 100 * mm, 36 * mm, 24 * mm]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Ҳақиқий етказилган ёки хизмат кўрсатилган сана: {_esc(c.get('delivery_date'))}.<br/>"
                           f"Қўшимча маълумот ва қайдлар: {_esc(c.get('note'))}.<br/>Иловалар: {_esc(c.get('attachments_text'))}.", st["base"]))
    d, r = c.get("deliverer") or {}, c.get("receiver") or {}
    parties = Table([[
        Paragraph(f"<b>Топширувчи</b><br/>{_esc(d.get('name'))}<br/>{_esc(d.get('full_name'))}{', ' + _esc(d['position']) if d.get('position') else ''}", st["cell"]),
        Paragraph(f"<b>Қабул қилувчи</b><br/>{_esc(r.get('name'))}<br/>{_esc(r.get('full_name'))}{', ' + _esc(r['position']) if r.get('position') else ''}", st["cell"]),
    ]], colWidths=[86 * mm, 86 * mm])
    parties.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(Spacer(1, 6))
    story.append(parties)
    story.append(Spacer(1, 4))
    story.append(Paragraph("Етказиб берувчи юқоридаги миқдорларни топширганини электрон имзоси билан тасдиқлайди. Маҳалла ушбу ҳужжатни "
                           "электрон имзолаш орқали айнан кўрсатилган маҳсулотлар ёки хизматларни қабул қилганини тасдиқлайди.", st["small"]))
    story.append(Spacer(1, 8))
    story.append(_signature_block(version, [Signature.Role.SUPPLIER, Signature.Role.MAHALLA]))
    return story


def _cancellation_story(version: DocumentVersion):
    c, st, story = version.content, _styles(), []
    story.append(Paragraph("БУЮРТМАНИ БЕКОР ҚИЛИШ ҲУЖЖАТИ", st["title"]))
    story.append(Paragraph(f"Буюртма: <b>{_esc(c.get('order_number'))}</b> &nbsp;&nbsp; Сана: <b>{_esc(c.get('date'))}</b>", st["center"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Маҳалла: {_esc(c.get('mahalla_name'))}. Етказиб берувчи: {_esc(c.get('supplier_name'))}.<br/>"
                           f"Сўровчи: {_esc(c.get('requested_by'))}. Келишган: {_esc(c.get('agreed_by'))}. Тасдиқлаган (уюшма): {_esc(c.get('approved_by'))}.", st["base"]))
    story.append(Paragraph(f"Сабаб: {_esc(c.get('reason'))}", st["base"]))
    story.append(Spacer(1, 4))
    rows = [[l["n"], l["name"], l["ordered_qty"], l["accepted_qty"], l["cancelled_qty"], l["unit"]] for l in c.get("lines", [])]
    story.append(_lines_table(["Т/р", "Маҳсулот ёки хизмат", "Буюртма", "Қабул қилинган", "Бекор қилинган", "Бирлик"], rows,
                              [12 * mm, 72 * mm, 22 * mm, 26 * mm, 26 * mm, 14 * mm]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Якуний ҳолат: <b>{_esc(c.get('result_cyr'))}</b>. Ҳужжат IDси: {_esc(version.qr_token)}. Текшириш: {_esc(verify_url(version.qr_token))}", st["small"]))
    return story


def _footer(version: DocumentVersion):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(18 * mm, 10 * mm, f"STAT-URMON · Яшил маҳалла · {version.document.number} v{version.version_no} · {version.qr_token}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"{doc.page}-бет")
        canvas.restoreState()
    return draw


def render_pdf(version: DocumentVersion) -> bytes:
    _register_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                            title=f"{version.document.number} v{version.version_no}", author="STAT-URMON")
    kind = version.document.kind
    if kind == Document.Kind.ACT:
        story = _act_story(version)
    elif kind == Document.Kind.CANCELLATION:
        story = _cancellation_story(version)
    else:
        story = _order_form_story(version)
    footer = _footer(version)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


def pdf_filename(version: DocumentVersion) -> str:
    number = (version.document.number or "hujjat").replace("/", "-")
    return f"{number}-v{version.version_no}.pdf"


def ensure_pdf(version: DocumentVersion):
    """`pdf_file` bo'lsa o'sha; bo'lmasa yaratib saqlaydi (imzodan keyin after_signature uni tozalaydi)."""
    if version.pdf_file and version.pdf_file.name:
        return version.pdf_file
    data = render_pdf(version)
    # Nomda holat bor: imzodan keyin qayta yaratilgan fayl eski nomni takrorlamaydi (kesh/CDN chalkashmasin)
    version.pdf_file.save(f"{version.qr_token}-{version.status}-{pdf_filename(version)}", ContentFile(data), save=False)
    version.save(update_fields=["pdf_file", "updated_at"])
    return version.pdf_file

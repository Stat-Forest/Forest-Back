"""
Hujjat PDF'i (TZ §11, §12, §13.3) — reportlab platypus, repo ichidagi DejaVu shrifti
(kirill; Docker image'da tizim shriftlari yo'q), QR — reportlab'ning o'z barcode moduli.

    render_pdf(version) -> bytes
    ensure_pdf(version) -> FieldFile     (yo'q bo'lsa yaratib `pdf_file` ga saqlaydi)

Imzodan keyin `documents.after_signature` `pdf_file` ni o'chiradi — keyingi so'rovda
imzo bloki bilan qayta yaratiladi. Imzolanmagan/qisman imzolangan nusxada
«ИМЗОЛАНМАГАН НУСХА» belgisi bo'ladi. Matn hujjat tilida (`content.lang`, D-28).
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
from apps.yashil.services.lang import doc_text

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


def _t(content):
    """Hujjat tilidagi matn: `t("Жой: {0}", qiymat)`; qiymatlar oldindan `_esc` qilinadi."""
    doc_lang = (content or {}).get("lang")
    return lambda text, *values: doc_text(text, doc_lang, *values)


def _sig_text(sig, t) -> str:
    if sig is None:
        return f"<b>{t('Имзо кутилмоқда')}</b>"
    when = timezone.localtime(sig.signed_at).strftime("%d.%m.%Y %H:%M")
    return f"{_esc(sig.signer_cn)} · {when} · E-IMZO ({sig.mode}) · <b>{t('Ҳақиқий')}</b>"


def _signature_block(version: DocumentVersion, roles):
    st, t = _styles(), _t(version.content)
    sigs = {s.role: s for s in version.signatures.filter(is_valid=True)}
    rows = [[Paragraph(f"<b>{t('Электрон тасдиқ')}</b>", st["cell"]), ""]]
    for role in roles:
        rows.append([Paragraph(f"{t(ROLE_LABELS_CYR[role])}:", st["cell"]), Paragraph(_sig_text(sigs.get(role), t), st["cell"])])
    status = t("Тўлиқ имзоланган") if not missing_roles(version) else t("Тўлиқ тасдиқланмаган")
    rows.append([Paragraph(f"{t('Ҳолат')}:", st["cell"]), Paragraph(f"<b>{status}</b>", st["cell"])])
    rows.append([Paragraph(f"{t('Ҳужжат IDси')}:", st["cell"]), Paragraph(_esc(version.qr_token), st["cell"])])
    rows.append([Paragraph(f"{t('Текшириш')}:", st["cell"]), Paragraph(_esc(verify_url(version.qr_token)), st["small"])])
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
        story.append(Paragraph(_t(version.content)("ИМЗОЛАНМАГАН НУСХА — ҳужжат тўлиқ тасдиқланмаган"), _styles()["warn"]))
        story.append(Spacer(1, 4))


def _number_line(t, c, *, partial=""):
    return (f"{t('Рақами')}: <b>{_esc(c.get('number'))}</b> &nbsp;&nbsp; {t('Сана')}: <b>{_esc(c.get('date'))}</b> &nbsp;&nbsp; "
            f"{t('Версия')}: <b>{_esc(c.get('version_no'))}</b>{partial}")


def _line_rows(c):
    return [[l["n"], f"{l['name']}" + (f" ({l['attrs']})" if l.get("attrs") else ""), l["qty"], l["unit"]] for l in c.get("lines", [])]


def _order_form_story(version: DocumentVersion):
    c, st, story, t = version.content, _styles(), [], _t(version.content)
    _unsigned_banner(version, story)
    story.append(Paragraph(f"{t('{0}га', _esc(c.get('supplier_name')))}<br/>{t('{0}, {1}даги', _esc(c.get('region')), _esc(c.get('district')))}<br/>"
                           f"{t('{0} номидан', _esc(c.get('mahalla_name')))}", st["right"]))
    story.append(Paragraph(t("Буюртманома").upper(), st["title"]))
    story.append(Paragraph(_number_line(t, c), st["center"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(t(
        "Ўзбекистон Республикаси Президентининг 2026 йил 23 сентябрдаги ПФ-206-сон Фармонига асосан {0} манзилида, {1} жойлашув "
        "нуқтасидаги {2} гектар ҳудудда «Яшил маҳалла» ташкил этиш учун қуйидаги {3} бўйича буюртма берилмоқда.",
        _esc(c.get("full_address")), _esc(c.get("point")), _esc(c.get("area_ha")), _esc(c.get("subject_phrase"))), st["base"]))
    head = [t("Объект номи: {0}.", _esc(c.get("title")))]
    if c.get("object_type"):
        head.append(t("Объект тури: {0}.", _esc(c["object_type"])))
    if c.get("season"):
        head.append(t("Мавсум: {0}.", _esc(c["season"])))
    story.append(Paragraph(f"{' '.join(head)}<br/>{t('Жойлашув нуқтаси: {0} (WGS84).', _esc(c.get('point')))}<br/>"
                           f"{t('Етказиб берувчи: {0}.', _esc(c.get('supplier_name')))}", st["base"]))
    story.append(Spacer(1, 4))
    story.append(_lines_table([t("Т/р"), t("Маҳсулот ёки хизмат номи ва хусусияти"), t("Миқдор"), t("Ўлчов бирлиги")], _line_rows(c),
                              [12 * mm, 104 * mm, 28 * mm, 28 * mm]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"{t('Қўшимча маълумот: {0}.', _esc(c.get('extra_info')))}<br/>{t('Иловалар: {0}.', _esc(c.get('attachments_text')))}", st["base"]))
    s = c.get("signer") or {}
    authority = f", {_esc(s['authority'])}" if s.get("authority") else ""
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>{t('Буюртма берувчи')}</b><br/>{t('Маҳалла: {0}.', _esc(c.get('mahalla_name')))}<br/>"
                           f"{t('Ваколатли шахс: {0}.', _esc(s.get('full_name')))}<br/>"
                           f"{t('Лавозими ва ваколат асоси: {0}.', _esc(s.get('position')) + authority)}<br/>"
                           f"{t('Алоқа рақами: {0}.', _esc(s.get('phone')))}", st["base"]))
    story.append(Spacer(1, 8))
    story.append(_signature_block(version, [Signature.Role.MAHALLA]))
    return story


def _party(title, p):
    position = f", {_esc(p['position'])}" if p.get("position") else ""
    return f"<b>{title}</b><br/>{_esc(p.get('name'))}<br/>{_esc(p.get('full_name'))}{position}"


def _act_story(version: DocumentVersion):
    c, st, story, t = version.content, _styles(), [], _t(version.content)
    _unsigned_banner(version, story)
    story.append(Paragraph(t("ТОПШИРИШ-ҚАБУЛ ҚИЛИШ ДАЛОЛАТНОМАСИ"), st["title"]))
    partial = f" &nbsp;&nbsp; <b>{t('Қисман')}</b>" if c.get("is_partial") else ""
    story.append(Paragraph(_number_line(t, c, partial=partial), st["center"]))
    story.append(Paragraph(t("Жой: {0}", _esc(c.get("place"))), st["base"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(t(
        "Ўзбекистон Республикаси Президентининг 2026 йил 23 сентябрдаги ПФ-206-сон Фармони ва {0}даги {1} сонли буюртманомага асосан "
        "{2} томонидан {3}га {4} учун қуйидаги маҳсулотлар етказиб берилди ва (ёки) хизматлар кўрсатилди.",
        _esc(c.get("order_date")), _esc(c.get("order_number")), _esc(c.get("supplier_name")), _esc(c.get("mahalla_name")),
        _esc(c.get("object_text"))), st["base"]))
    story.append(Spacer(1, 4))
    story.append(_lines_table([t("Т/р"), t("Маҳсулот ёки хизмат номи"), t("Ушбу акт бўйича миқдор"), t("Бирлик")], _line_rows(c),
                              [12 * mm, 100 * mm, 36 * mm, 24 * mm]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"{t('Ҳақиқий етказилган ёки хизмат кўрсатилган сана: {0}.', _esc(c.get('delivery_date')))}<br/>"
                           f"{t('Қўшимча маълумот ва қайдлар: {0}.', _esc(c.get('note')))}<br/>{t('Иловалар: {0}.', _esc(c.get('attachments_text')))}",
                           st["base"]))
    parties = Table([[
        Paragraph(_party(t("Топширувчи"), c.get("deliverer") or {}), st["cell"]),
        Paragraph(_party(t("Қабул қилувчи"), c.get("receiver") or {}), st["cell"]),
    ]], colWidths=[86 * mm, 86 * mm])
    parties.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(Spacer(1, 6))
    story.append(parties)
    story.append(Spacer(1, 4))
    story.append(Paragraph(t("Етказиб берувчи юқоридаги миқдорларни топширганини электрон имзоси билан тасдиқлайди. Маҳалла ушбу ҳужжатни "
                             "электрон имзолаш орқали айнан кўрсатилган маҳсулотлар ёки хизматларни қабул қилганини тасдиқлайди."), st["small"]))
    story.append(Spacer(1, 8))
    story.append(_signature_block(version, [Signature.Role.SUPPLIER, Signature.Role.MAHALLA]))
    return story


def _cancellation_story(version: DocumentVersion):
    c, st, story, t = version.content, _styles(), [], _t(version.content)
    story.append(Paragraph(t("БУЮРТМАНИ БЕКОР ҚИЛИШ ҲУЖЖАТИ"), st["title"]))
    story.append(Paragraph(f"{t('Буюртма')}: <b>{_esc(c.get('order_number'))}</b> &nbsp;&nbsp; {t('Сана')}: <b>{_esc(c.get('date'))}</b>", st["center"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"{t('Маҳалла: {0}.', _esc(c.get('mahalla_name')))} {t('Етказиб берувчи: {0}.', _esc(c.get('supplier_name')))}<br/>"
                           f"{t('Сўровчи: {0}.', _esc(c.get('requested_by')))} {t('Келишган: {0}.', _esc(c.get('agreed_by')))} "
                           f"{t('Тасдиқлаган (уюшма): {0}.', _esc(c.get('approved_by')))}", st["base"]))
    story.append(Paragraph(t("Сабаб: {0}", _esc(c.get("reason"))), st["base"]))
    story.append(Spacer(1, 4))
    rows = [[l["n"], l["name"], l["ordered_qty"], l["accepted_qty"], l["cancelled_qty"], l["unit"]] for l in c.get("lines", [])]
    story.append(_lines_table([t("Т/р"), t("Маҳсулот ёки хизмат"), t("Буюртма"), t("Қабул қилинган"), t("Бекор қилинган"), t("Бирлик")], rows,
                              [12 * mm, 72 * mm, 22 * mm, 26 * mm, 26 * mm, 14 * mm]))
    story.append(Spacer(1, 6))
    result = c.get("result_label") or c.get("result_cyr")
    story.append(Paragraph(f"{t('Якуний ҳолат')}: <b>{_esc(result)}</b>. {t('Ҳужжат IDси')}: {_esc(version.qr_token)}. "
                           f"{t('Текшириш')}: {_esc(verify_url(version.qr_token))}", st["small"]))
    return story


def _footer(version: DocumentVersion):
    t = _t(version.content)

    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(18 * mm, 10 * mm, f"STAT-URMON · {t('Яшил маҳалла')} · {version.document.number} v{version.version_no} · {version.qr_token}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, t("{0}-бет", doc.page))
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

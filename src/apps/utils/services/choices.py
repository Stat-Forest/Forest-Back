from django.db import models
from django.utils.translation import gettext_lazy as _


class AllReviews(models.TextChoices):
    JONATILGAN = 'sent', _('Jo‘natilgan hisobotlar')
    QAYTARILGAN = 'rejected', _('Qaytarilgan hisobotlar')
    QABUL_QILINGAN = 'accepted', _('Qabul qilingan hisobotlar')
    MASUL_VAKILLAR = 'responsible', _('Mas’ul vakillar')
    QORALAMA = 'draft', _('Qoralama')
    HABARNOMALAR = 'notifications', _('Habarnomalar')

class RegionChoices(models.TextChoices):
    TASHKENT = 'TASH', _('Tashkent')
    NAMANGAN = 'NAM', _('Namangan')
    ANDIJON = 'AND', _('Andijon')
    FARGONA = 'FAR', _('Fergana')
    BUXORO = 'BUX', _('Bukhara')
    SAMARQAND = 'SAM', _('Samarkand')
    NAVOIY = 'NAV', _('Navoi')
    QASHQADARYO = 'QASH', _('Qashqadarya')
    SURXONDARYO = 'SUR', _('Surxondaryo')
    XORAZM = 'XOR', _('Khorezm')
    SIRDARYO = 'SIR', _('Sirdaryo')
    JIZZAX = 'JIZ', _('Jizzakh')
    QORAQALPAQSTAN = 'QRP', _('Karakalpakstan')

class StatementChoices(models.TextChoices):
    HODIMLAR_HISOBI = "hodimlar_hisobi", _("Hodimlar hisobi")
    HODIMLAR_TAHLILI = "hodimlar_tahlili", _("Hodimlar hisobi taxlili")
    DAROMAD = "daromad", _("Daromad")
    JAMGARMA = "jamgarma", _("Jamg’arma")
    NIHOLXONA = "niholxona", _("Niholxona-ko’chatxona")
    YOPIQ_ILDIZ = "yopiq_ildiz", _("Yopik ildiz yirik hajmli")
    SOTISH_UCHUN = "sotish_uchun", _("Sotish uchun yaroqli ko’chatlar")
    QALAMCHA = "qalamcha", _("Qalamcha tayyorlash")
    NIH_KUCH_1 = "nih_kuch_1", _("Nih kuch jamlanmasi")
    KOCHAT_QOLDIQ = "kochat_qoldiq", _("Ko’chat qoldiq (ko’chat turi bo’yicha)")
    NIHOL_HARAKATI = "nihol_harakati", _("Nihol harakati")
    NIHOL_QOLDIQ = "nihol_qoldiq", _("Nihol qoldiq (nihol turi bo’yicha)")
    KOCHAT_YETKAZIB = "kochat_yetkazib", _("Ko’chat yetkazib berish")
    URMON_BARPO = "urmon_barpo", _("Urmon barpo kilish")
    URUG_HARAKATI = "urug_harakati", _("Urug’ harakati")
    URUG_TURI = "urug_turi", _("Urug’ turi bo’yicha")
    URUG_JAMG = "urug_jamg", _("Urug’larni jamg’arish")
    YAYLOV_HISOBI = "yaylov_hisobi", _("Yaylov hisobi")
    CHORVACHILIK = "chorvachilik", _("Chorvachilik")
    MEXANIZATSIYA = "mexanizatsiya", _("Mexanizatsiya hisobi")
    QISHLOQ_XOJALIGI = "qishloq_xojaligi", _("Qishloq xo’jaligi")
    PICHAN_URISH = "pichan_urish", _("Pichan urish")
    IJARAGA_YERLAR = "ijaraga_yerlar", _("Ijaraga berilgan yerlar hisobi")
    YER_OZLASHTIRISH = "yer_ozlashtirish", _("Yer o’zlashtirish")
    URMON_QOPLANGAN = "urmon_qoplangan", _("Urmon bilan qoplangan yerlar")
    YOGIN_OLDINI_OLISH = "yogin_oldini_olish", _("Yo’g’inlarni oldini olish")
    ZARARKUNANDA = "zararkunanda", _("Zararkunanda va kasalliklarga qarshi kurashish")
    XUQUQBUZARLIK = "xuquqbuzarlik", _("Xuquqbuzarlik")


class PeriodChoices(models.TextChoices):
    KUNLIK = 'daily', _('Kunlik')
    HAFTALIK = 'weekly', _('Haftalik')
    OYLIK = 'monthly', _('Oylik')
    CHORAKLIK = 'quarterly', _('Choraklik (3 oy)')
    YILLIK = 'yearly', _('Yillik')

class ReportType(models.TextChoices):
    NEW = 'new', _('New')
    SENT = 'sent', _('Sent')
    CANCELLED = 'cancelled', _('Cancelled')
    ACCEPTED = 'accepted', _('Accepted')
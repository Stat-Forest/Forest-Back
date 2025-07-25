from django.db import models
from django.utils.translation import gettext_lazy as _

class RegionChoices(models.TextChoices):
    TASHKENT = 'tashkent', _('Tashkent')
    NAMANGAN = 'namangan', _('Namangan')
    ANDIJON = 'andijon', _('Andijon')
    FARGONA = 'fargona', _('Fergana')
    BUXORO = 'buxoro', _('Bukhara')
    SAMARQAND = 'samarqand', _('Samarkand')
    NAVOIY = 'navoiy', _('Navoi')
    QASHQADARYO = 'qashqadaryo', _('Qashqadarya')
    SURXONDARYO = 'surxondaryo', _('Surxondaryo')
    XORAZM = 'xorazm', _('Khorezm')
    SIRDARYO = 'sirdaryo', _('Sirdaryo')
    JIZZAX = 'jizzax', _('Jizzakh')
    QORAQALPAQSTAN = 'qoraqalpog‘iston', _('Karakalpakstan')

    REPUBLIC = 'republic', _('Respublika tashkilotlari')

from django.utils.translation import gettext_lazy as _
from django.db import models

class StatementChoices(models.TextChoices):
    HODIMLAR_HISOBI = "hodimlar_hisobi", _("Hodimlar hisobi")
    HODIMLAR_TAHLILI = "hodimlar_tahlili", _("Hodimlar hisobi tahlili")
    DAROMAD = "daromad", _("Daromad")
    JAMGARMA = "jamgarma", _("Jamg'arma")
    NIHOLXONA = "niholxona", _("Niholxona-ko'chatxona")
    YOPIQ_ILDIZ = "yopiq_ildiz", _("Yopiq ildiz yirik hajmli")
    SOTISH_UCHUN = "sotish_uchun", _("Sotish uchun yaroqli ko'chatlar")
    QALAMCHA = "qalamcha", _("Qalamcha tayyorlash")
    NIH_KUCH_JAMLANMA = "nih_kuch_jamlanma", _("Nih kuch jamlanma")
    KOCHAT_HARAKATI = "kochat_harakati", _("Ko'chat harakati")
    KOCHAT_QOLDIQ = "kochat_qoldiq", _("Ko'chat qoldiq (ko'chat turi bo'yicha)")
    NIHOL_HARAKATI = "nihol_harakati", _("Nihol harakati")
    NIHOL_QOLDIQ = "nihol_qoldiq", _("Nihol qoldiq (nihol turi bo'yicha)")
    KOCHAT_YETKAZIB = "kochat_yetkazib", _("Ko'chat yetkazib berish")
    URMON_BARPO = "urmon_barpo", _("Urmon barpo qilish")
    URUG_HARAKATI = "urug_harakati", _("Urug' harakati")
    URUG_TURI = "urug_turi", _("Urug' turi bo'yicha")
    URUG_JAMGARISH = "urug_jamgarish", _("Urug'larni jamg'arish")
    YAYLOV_HISOBI = "yaylov_hisobi", _("Yaylov hisobi")
    CHORVACHILIK = "chorvachilik", _("Chorvachilik")
    MEXANIZATSIYA = "mexanizatsiya", _("Mexanizatsiya hisobi")
    QISHLOQ_XOJALIGI = "qishloq_xojaligi", _("Qishloq xo'jaligi")
    PICHAN_URISH = "pichan_urish", _("Pichan o'rish")
    IJARAGA_YERLAR = "ijaraga_yerlar", _("Ijaraga berilgan yerlar hisobi")
    YER_OZLASHTIRISH = "yer_ozlashtirish", _("Yer o'zlashtirish")
    URMON_QOPLANGAN = "urmon_qoplangan", _("Urmon bilan qoplangan yerlar")
    YONGIN_OLDINI_OLISH = "yongin_oldini_olish", _("Yong'inlarni oldini olish")
    ZARARKUNANDA = "zararkunanda", _("Zararkunanda va kasalliklarga qarshi kurashish")
    XUQUQBUZARLIK = "xuquqbuzarlik", _("Huquqbuzarlik")



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


DAILY_STATEMENTS = [  # kunlik
    "urug_harakati",
    "yaylov_hisobi",
    "chorvachilik",
    "pichan_urish",
    "xuquqbuzarlik",
]

WEEKLY_STATEMENTS = [  # haftalik
    "jamgarma",
]

MONTHLY_STATEMENTS = [  # oylik
    "daromad",
    "ijaraga_yerlar",
    "zararkunanda",
    "yer_ozlashtirish",
]

QUARTERLY_STATEMENTS = [  # choraklik
    "hodimlar_hisobi",
    "sotish_uchun",
    "qalamcha",
    "nih_kuch_1",
    "kochat_harakati",
    "kochat_qoldiq",
    "nihol_harakati",
    "nihol_qoldiq",
    "kochat_yetkazib",
    "urmon_barpo",
    "urug_turi",
    "urug_jamg",
    "mexanizatsiya",
    "qishloq_xojaligi",
    "yopiq_ildiz",
    "niholxona",
    "epik_ildiz",
    "engillash",
]

YEARLY_STATEMENTS = [  # yillik
    "hodimlar_tahlili",
    "urmon_qoplangan",
]

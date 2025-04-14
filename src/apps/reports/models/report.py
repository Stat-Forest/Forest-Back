from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.general.models import Organization

class SectionChoices(models.TextChoices):
    HODIMLAR_HISOBI = 'HH', _('Hodimlar hisobi')
    HODIMLAR_TAHLIL = 'HT', _('Hodimlar hisobi taxlili')
    DAROMAD = 'DR', _('Daromad')
    JAMGARMA = 'JG', _('Jamg’arma')
    NIHOLXONA = 'NX', _('Niholxona-ko’chatxona')
    YIRIK_HAJMLI = 'YH', _('Yopik ildiz yirik hajmli')
    YAROQLI_KOCHAT = 'YK', _('Sotish uchun yaroqli ko’chatlar')
    QALAMCHA = 'QT', _('Qalamcha tayyorlash')
    NIH_KUCH_JAMLANMASI_1 = 'NKJ1', _('Nih kuch jamlanmasi')
    NIH_KUCH_JAMLANMASI_2 = 'NKJ2', _('Nih kuch jamlanmasi')
    KOCHAT_QOLDIQ = 'KQ', _('Ko’chat qoldiq (ko’chat turi bo’yicha)')
    NIHOL_HARAKATI = 'NH', _('Nihol harakati')
    NIHOL_QOLDIQ = 'NQ', _('Nihol qoldiq (nihol turi bo’yicha)')
    KOCHAT_YETKAZIB_BERISH = 'KYB', _('Ko’chat yetkazib berish')
    URMON_BARPO = 'UBK', _('Urmon barpo kilish')
    URUG_HARAKATI = 'UH', _('Urug’ harakati')
    URUG_TURI = 'UT', _('Urug’ turi bo’yicha')
    URUG_JAMGARISH = 'UJ', _('Urug’larni jamg’arish')
    YAYLOV_HISOBI = 'YYH', _('Yaylov hisobi')
    CHORVACHILIK = 'CH', _('Chorvachilik')
    MEXANIZATSIYA = 'MX', _('Mexanizatsiya hisobi')
    QISHLOQ_XOJALIGI = 'QX', _('Qishloq xo’jaligi')
    PICHAN_URISH = 'PU', _('Pichan urish')
    IJARA_YERLAR = 'IYH', _('Ijaraga berilgan yerlar hisobi')
    YER_OZLASHTIRISH = 'YO', _('Yer o’zlashtirish')
    URMON_QOPLAMA = 'UQY', _('Urmon bilan qoplangan yerlar')
    YOGIN_OLDINI_OLISH = 'YOO', _('Yo’g’inlarni oldini olish')
    ZARARKUNANDA = 'ZK', _('Zararkunanda va kasalliklarga qarshi kurashish')
    XUQUQBHUZARLIK = 'XQ', _('Xuquqbuzarlik')

class PeriodChoices(models.TextChoices):
    KUNLIK = 'daily', _('Kunlik')
    HAFTALIK = 'weekly', _('Haftalik')
    OYLIK = 'monthly', _('Oylik')
    CHORAKLIK = 'quarterly', _('Choraklik (3 oy)')
    YILLIK = 'yearly', _('Yillik')

class ReportType(models.TextChoices):
    UNSAVED = 'unsaved', _('Unsaved')
    SENT = 'sent', _('Sent')
    RETURNED = 'returned', _('Returned')
    ACCEPTED = 'accepted', _('Accepted')

class Report(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    statement = models.CharField(
        max_length=10,
        choices=SectionChoices.choices
    )
    period = models.CharField(
        max_length=10,
        choices=PeriodChoices.choices
    )
    status = models.CharField(
        max_length=10,
        choices=ReportType.choices,
        default=ReportType.UNSAVED
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True
    )
    submission_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _('Report')
        verbose_name_plural = _('Reports')

    def __str__(self):
        return f"{self.organization.name} - {self.statement} "

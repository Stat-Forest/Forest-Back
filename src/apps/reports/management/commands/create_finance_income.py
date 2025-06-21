import random
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.reports.models import Statement, StatementColumn
from apps.reports.models.statement_column import StatementColumn as SC
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    help = 'Creates default Statement and StatementColumn data'

    def handle(self, *args, **kwargs):
      
        with transaction.atomic():


            moliya_statement = Statement.objects.create(
                name="Moliya-iqtisod va buxgalteriya",
                parent=None
            )
            daromad_statement = Statement.objects.create(
                name="Daromad",
                parent=moliya_statement,
                period=PeriodChoices.OYLIK,
            )

            daromad_turlari = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=None,
                title="Daromad turlari bo‘yicha",
                ordering="1"
            )
            info = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=daromad_turlari,
                title="2025 yil davomida topilgan daromadlar haqida MA'LUMOT",
                ordering="1.1"
            )

            titles = [
                "Tashkilot nomi",
                "Ko‘chat va nihol sotish",
                "Yog‘och o‘tin sotish",
                "Sanoat, xalq iste’mol mollari",
                "Aholiga pullik xizmat",
                "Yaylov tushumi",
                "Qishloq xo‘jaligi mahsulotlari",
                "Chorvachilik",
                "Parrandachilik",
                "Quyonchilik",
                "Baliqchilik",
                "Asalarichilik",
                "Dorivor o‘simliklar",
                "Ko‘kalamzorlashtirish",
                "Boshqa tushumlar",
                "Ixota",
                "Urug‘ sotishdan",
                "Ijara to‘lovlari",
                "Jami"
            ]
            for idx, title in enumerate(titles, start=1):
                StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=info,
                    title=title,
                    ordering=f"1.1.{idx}",
                    is_organization=(idx == 1)
                )

            tushumlar = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=None,
                title="Tushumlar bo‘yicha",
                ordering="2"
            )
            tushum_info = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushumlar,
                title="2025 yil holatiga daromad tushumi to‘g‘risida ma’lumot",
                ordering="2.1"
            )
            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushum_info,
                title='Tashkilot nomi',
                ordering="2.1.1",
                is_organization=True
            )

            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushum_info,
                title='Yillik reja',
                ordering="2.1.2",
                status_plan=SC.PlanStatus.YILLIK
            )

            choraklar = {
                SC.PlanStatus.CHORAK_1: [SC.PlanStatus.YANVAR, SC.PlanStatus.FEVRAL, SC.PlanStatus.MART],
                SC.PlanStatus.CHORAK_2: [SC.PlanStatus.APREL, SC.PlanStatus.MAY, SC.PlanStatus.IYUN],
                SC.PlanStatus.CHORAK_3: [SC.PlanStatus.IYUL, SC.PlanStatus.AVGUST, SC.PlanStatus.SENTABR],
                SC.PlanStatus.CHORAK_4: [SC.PlanStatus.OKTABR, SC.PlanStatus.NOYABR, SC.PlanStatus.DEKABR],
            }

            for c_idx, (chorak_status, oylar) in enumerate(choraklar.items(), start=1):
                chorak_order = f"2.1.{2 + c_idx * 2 - 1}"
                chorak_reja = StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=tushum_info,
                    title=f"{chorak_status.label} reja",
                    ordering=chorak_order
                )
                StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=chorak_reja,
                    title="Reja",
                    ordering=f"{chorak_order}.1",
                    status_plan=chorak_status
                )
                StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=chorak_reja,
                    title="Amalda",
                    ordering=f"{chorak_order}.2"
                )

                chorak_oy_node = StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=tushum_info,
                    title=chorak_status.label,
                    ordering=f"2.1.{2 + c_idx * 2}"
                )

                for o_idx, oy_status in enumerate(oylar, start=1):
                    oy_order = f"2.1.{2 + c_idx * 2}.{o_idx}"
                    oy_node = StatementColumn.objects.create(
                        statement=daromad_statement,
                        parent=chorak_oy_node,
                        title=oy_status.label,
                        ordering=oy_order
                    )

                    for p_idx, title in enumerate(["Reja", "Amalda", "Foiz"], start=1):
                        StatementColumn.objects.create(
                            statement=daromad_statement,
                            parent=oy_node,
                            title=title,
                            ordering=f"{oy_order}.{p_idx}",
                            status_plan=(oy_status if title == "Reja" else None)
                        )

                    tushum_node = StatementColumn.objects.create(
                        statement=daromad_statement,
                        parent=oy_node,
                        title="tushum",
                        ordering=f"{oy_order}.4"
                    )
                    for t_idx, sub in enumerate(["kunlik", "Oy boshidan"], start=1):
                        StatementColumn.objects.create(
                            statement=daromad_statement,
                            parent=tushum_node,
                            title=sub,
                            ordering=f"{oy_order}.4.{t_idx}"
                        )

            year_begin=StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushum_info,
                title='Yil boshidan',
                ordering="2.1.11",
            )
            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=year_begin,
                title='Tushum',
                ordering="2.1.11.1",
            )
            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=year_begin,
                title='Yillik rejaga nisbatan %',
                ordering="2.1.11.2",
            )
            svod = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=None,
                title="Svod",
                ordering="3"
            )
            svod_title = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=svod,
                title="2025 yil davomida topilgan daromadlar haqida MA'LUMOT",
                ordering="3.1"
            )
            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=svod_title,
                title="Tashkilot nomi",
                ordering="3.1.1",
                is_organization=True
            )
            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=svod_title,
                title="Yillik reja (ming sum)",
                ordering="3.1.2",
                status_plan=SC.PlanStatus.YILLIK
            )
            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=svod_title,
                title="Amalda (ming sum)",
                ordering="3.1.3"
            )
            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=svod_title,
                title="Rejaga nisbatan %",
                ordering="3.1.4"
            )

            self.stdout.write(self.style.SUCCESS("StatementColumn entries created with `status_plan` structure."))

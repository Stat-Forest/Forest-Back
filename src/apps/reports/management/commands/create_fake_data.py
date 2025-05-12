import random

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.general.models import Organization
from apps.reports.models import Statement, StatementColumn

from apps.utils.services import *


class Command(BaseCommand):
    help = 'Creates default Statement and StatementColumn data'

    def handle(self, *args, **kwargs):
        Statement.objects.all().delete()
        StatementColumn.objects.all().delete()
        Organization.objects.all().delete()

        with transaction.atomic():
            # Create organizations
            organizations = []
            for _ in range(13):
                org_region = random.choice(RegionChoices.values)
                organization = Organization(
                    name='Organization {}'.format(org_region),
                    region=org_region,
                )
                organizations.append(organization)

            Organization.objects.bulk_create(organizations)

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
            info_title = "O‘rmon xo‘jaligi agentligi tizimidagi tashkilotlarining 2025 yil davomida topilgan daromadlari to‘g‘risida MA'LUMOT"
            info = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=daromad_turlari,
                title=info_title,
                ordering="1.1"
            )

            titles = [
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
                    ordering=f"1.1.{idx}"
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
                title="O‘rmon xo‘jaligi agentligi tizimi korxonalarida 2025 yil holatiga daromad tushumi to‘g‘risida ma’lumot",
                ordering="2.1"
            )

            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushum_info,
                title='Yillik reja',
                ordering="2.1.1",
                is_plan=True
            )

            choraklar = {
                "1 - chorak": ["yanvar", "fevral", "mart"],
                "2 - chorak": ["aprel", "may", "iyun"],
                "3 - chorak": ["iyul", "avgust", "sentyabr"],
                "4 - chorak": ["oktyabr", "noyabr", "dekabr"]
            }

            for chorak_idx, (chorak_nomi, oylari) in enumerate(choraklar.items(), start=1):
                chorak_reja_order = f"2.1.{2 + (chorak_idx - 1) * 2}"
                chorak_reja_node = StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=tushum_info,
                    title=f"{chorak_nomi} reja",
                    ordering=chorak_reja_order
                )
                StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=chorak_reja_node,
                    title="Reja",
                    ordering=f"{chorak_reja_order}.1",
                    is_plan=True
                )
                StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=chorak_reja_node,
                    title="Amalda",
                    ordering=f"{chorak_reja_order}.2",
                    is_plan=False
                )

                chorak_order = f"2.1.{2 + (chorak_idx - 1) * 2 + 1}"
                chorak_node = StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=tushum_info,
                    title=chorak_nomi,
                    ordering=chorak_order
                )

                for oy_idx, oy in enumerate(oylari, start=1):
                    oy_order = f"{chorak_order}.{oy_idx}"
                    oy_node = StatementColumn.objects.create(
                        statement=daromad_statement,
                        parent=chorak_node,
                        title=oy,
                        ordering=oy_order
                    )

                    tushum_order = f"{oy_order}.1"
                    tushum_node = StatementColumn.objects.create(
                        statement=daromad_statement,
                        parent=oy_node,
                        title='tushum',
                        ordering=tushum_order
                    )

                    sub_titles = ["Reja", "Amalda", "Foiz", "kunlik", "Oy boshidan"]
                    for sub_idx, sub in enumerate(sub_titles, start=1):
                        ordering_value = f"{tushum_order}.{sub_idx}"
                        is_plan_flag = sub == "Reja"
                        StatementColumn.objects.update_or_create(
                            statement=daromad_statement,
                            parent=tushum_node,
                            title=sub,
                            ordering=ordering_value,
                            defaults={'is_plan': is_plan_flag}
                        )

            svod = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=None,
                title="Svod",
                ordering="3"
            )
            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=svod,
                title="Yillik Reja (ming so'm)",
                ordering="3.1",
                is_plan=True
            )
            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=svod,
                title="Amalda (ming so'm)",
                ordering="3.2"
            )
            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=svod,
                title="Rejaga nisbatan %",
                ordering="3.3"
            )

            self.stdout.write(self.style.SUCCESS("✅ Successfully created statement columns with full 12-month breakdown and all quarterly 'reja' sections."))

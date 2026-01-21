from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.reports.models import Statement, StatementColumn
from apps.reports.models.statement_column import StatementColumn as SC
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    help = 'Daromad 1 statementining to‘liq column tuzilmasini yaratadi.'

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            moliya_statement = Statement.objects.filter(
                name="Moliya-iqtisod va buxgalteriya"
            ).first()

            current_year = timezone.now().year

            # Asosiy statement
            daromad_statement = Statement.objects.create(
                name="Daromad 1",
                name_uz="Daromad 1",
                name_ru="Доход 1",
                parent=moliya_statement,
                period=PeriodChoices.OYLIK,
            )

            # 1 - asosiy root
            tushumlar = StatementColumn.objects.create(
                statement=daromad_statement,
                title="Daromad 1 ilovasi",
                title_uz="Daromad 1 ilovasi",
                title_ru="Доход приложение 1",
                ordering="1",
            )

            # 1.1 - info qismi
            tushum_info = StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushumlar,
                title=f"{current_year} yil holatiga daromad tushumi to‘g‘risida ma’lumot",
                title_uz=f"{current_year} yil holatiga daromad tushumi to‘g‘risida ma’lumot",
                title_ru=f"ИНФОРМАЦИЯ о доходах по состоянию на {current_year} год",
                ordering="1.1",
            )

            # 1.1.x - asosiy ustunlar
            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushum_info,
                title='Tashkilot nomi',
                title_uz='Tashkilot nomi',
                title_ru='Название организации',
                ordering="1.1.1",
                is_organization=True,
                is_user_input=True,
            )

            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushum_info,
                title='Yillik reja',
                title_uz='Yillik reja',
                title_ru='Годовой план',
                ordering="1.1.2",
                status_plan=SC.PlanStatus.YILLIK,
                is_user_input=True,
            )

            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushum_info,
                title='Amalda',
                title_uz='Amalda',
                title_ru='На практике',
                ordering="1.1.3",
                is_user_input=False,
            )

            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushum_info,
                title='Farqi',
                title_uz='Farqi',
                title_ru='Разница',
                ordering="1.1.4",
                is_user_input=False,
            )

            StatementColumn.objects.create(
                statement=daromad_statement,
                parent=tushum_info,
                title='Foizda',
                title_uz='Foizda',
                title_ru='В процентах',
                ordering="1.1.5",
                is_user_input=False,
            )

            # Chorak va oylar lug‘atlari
            choraklar = {
                SC.PlanStatus.CHORAK_1: ["Yanvar", "Fevral", "Mart"],
                SC.PlanStatus.CHORAK_2: ["Aprel", "May", "Iyun"],
                SC.PlanStatus.CHORAK_3: ["Iyul", "Avgust", "Sentabr"],
                SC.PlanStatus.CHORAK_4: ["Oktabr", "Noyabr", "Dekabr"],
            }

            choraklar_ru = {
                SC.PlanStatus.CHORAK_1: ["Январь", "Февраль", "Март"],
                SC.PlanStatus.CHORAK_2: ["Апрель", "Май", "Июнь"],
                SC.PlanStatus.CHORAK_3: ["Июль", "Август", "Сентябрь"],
                SC.PlanStatus.CHORAK_4: ["Октябрь", "Ноябрь", "Декабрь"],
            }

            chorak_nomi_uz = {
                SC.PlanStatus.CHORAK_1: "1-chorak",
                SC.PlanStatus.CHORAK_2: "2-chorak",
                SC.PlanStatus.CHORAK_3: "3-chorak",
                SC.PlanStatus.CHORAK_4: "4-chorak",
            }

            chorak_nomi_ru = {
                SC.PlanStatus.CHORAK_1: "1-й квартал",
                SC.PlanStatus.CHORAK_2: "2-й квартал",
                SC.PlanStatus.CHORAK_3: "3-й квартал",
                SC.PlanStatus.CHORAK_4: "4-й квартал",
            }

            base_order = 2  # 1.1 dan keyingi raqamlar
            for c_idx, (chorak_status, oylar_uz) in enumerate(choraklar.items(), start=1):
                order_prefix = f"1.{base_order + c_idx}"

                # Chorak reja qismi
                chorak_reja = StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=tushum_info,
                    title=f"{chorak_nomi_uz[chorak_status]} reja",
                    title_uz=f"{chorak_nomi_uz[chorak_status]} reja",
                    title_ru=f"{chorak_nomi_ru[chorak_status]} план",
                    ordering=f"{order_prefix}.1",
                )

                StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=chorak_reja,
                    title="Reja",
                    title_uz="Reja",
                    title_ru="План",
                    ordering=f"{order_prefix}.1.1",
                    status_plan=chorak_status,
                    is_user_input=True,
                )
                StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=chorak_reja,
                    title="Amalda",
                    title_uz="Amalda",
                    title_ru="Факт",
                    ordering=f"{order_prefix}.1.2",
                    is_user_input=False,
                )
                StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=chorak_reja,
                    title="Farqi",
                    title_uz="Farqi",
                    title_ru="Разница",
                    ordering=f"{order_prefix}.1.3",
                    is_user_input=False,
                )

                # Chorak oylar qismi
                chorak_oy_node = StatementColumn.objects.create(
                    statement=daromad_statement,
                    parent=tushum_info,
                    title=chorak_nomi_uz[chorak_status],
                    title_uz=chorak_nomi_uz[chorak_status],
                    title_ru=chorak_nomi_ru[chorak_status],
                    ordering=f"{order_prefix}.2",
                )

                oylar_ru = choraklar_ru[chorak_status]
                for o_idx, (oy_uz, oy_ru) in enumerate(zip(oylar_uz, oylar_ru), start=1):
                    oy_node = StatementColumn.objects.create(
                        statement=daromad_statement,
                        parent=chorak_oy_node,
                        title=oy_uz,
                        title_uz=oy_uz,
                        title_ru=oy_ru,
                        ordering=f"{order_prefix}.2.{o_idx}",
                    )

                    # Har oy uchun reja va amalda
                    StatementColumn.objects.create(
                        statement=daromad_statement,
                        parent=oy_node,
                        title="Reja",
                        title_uz="Reja",
                        title_ru="План",
                        ordering=f"{order_prefix}.2.{o_idx}.1",
                        status_plan=getattr(SC.PlanStatus, oy_uz.upper(), None),
                        is_user_input=True,
                    )

                    StatementColumn.objects.create(
                        statement=daromad_statement,
                        parent=oy_node,
                        title="Amalda",
                        title_uz="Amalda",
                        title_ru="Факт",
                        ordering=f"{order_prefix}.2.{o_idx}.2",
                        is_user_input=True,
                    )

            self.stdout.write(self.style.SUCCESS("✅ Daromad 1 statement to‘liq va tartibli yaratildi."))

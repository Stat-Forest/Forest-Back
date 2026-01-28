from django.core.management import BaseCommand

from apps.reports.models import StatementColumn, Statement
from apps.utils.services import PeriodChoices


class Command(BaseCommand):
    def handle(self, *args, **options):
        parent_statement_2 = Statement.objects.get(
            name_uz="O'rmon barpo qilish",
            name_ru="Создание леса",
        )

        kochat_statement = Statement.objects.create(
            parent=parent_statement_2,
            name_uz="Ko'chat va Nihol Yetishtirish Jami",
            name_ru="Всего выращивание саженцев и рассады",
            period=PeriodChoices.OYLIK
        )

        app_column = StatementColumn.objects.create(
            statement=kochat_statement,
            title_uz="1-ilova",
            title_ru="Приложение 1",
            ordering="1"
        )

        title_column_1 = StatementColumn.objects.create(
            statement=kochat_statement,
            parent=app_column,
            title_uz=f"2026-yilda  o‘rmon xo‘jaliklari tomonidan niholxona va ko‘chatxonalar tashkil etish, shuningdek yillik nihol va ko‘chat yetishtirish tezkor ma’lumoti",
            title_ru=f"Оперативная информация о создании лесными хозяйствами питомников и питомников, а также выращивании годовых саженцев и рассады в 2026 году",
            ordering="1.1"
        )
        StatementColumn.objects.create(
            statement=kochat_statement,
            parent=title_column_1,
            title_uz="Tashkilot nomi",
            title_ru="Названия регионов",
            ordering="1.1.1",
            is_organization=True
        )

        jami = StatementColumn.objects.create(
            statement=kochat_statement,
            parent=title_column_1,
            title_uz="Jami niholxona va ko‘chatxonalar tashkil etish (dona)",
            title_ru="Всего создание питомников и теплиц (штук)",
            ordering="1.1.2"
        )
        StatementColumn.objects.create(
            statement=kochat_statement,
            parent=jami,
            title_uz="Reja",
            title_ru="План",
            ordering="1.1.2.1",
            status_plan=StatementColumn.PlanStatus.YILLIK_TOTAL,
            is_user_input=True
        )
        StatementColumn.objects.create(
            statement=kochat_statement,
            parent=jami,
            title_uz="Amalda",
            title_ru="Факт",
            ordering="1.1.2.2",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=kochat_statement,
            parent=jami,
            title_uz="Foiz",
            title_ru="Процент",
            ordering="1.1.2.3",
            is_user_input=False
        )

        subgroup = StatementColumn.objects.create(
            statement=kochat_statement,
            parent=jami,
            title_uz="shundan",
            title_ru="в том числе",
            ordering="1.1.3",
        )

        niholxona = StatementColumn.objects.create(
            statement=kochat_statement,
            parent=subgroup,
            title_uz="Nihol",
            title_ru="Питомник",
            ordering="1.1.3.1",
        )
        StatementColumn.objects.create(
            statement=kochat_statement,
            parent=niholxona,
            title_uz="Reja",
            title_ru="План",
            ordering="1.1.3.1.1",
            status_plan=StatementColumn.PlanStatus.YILLIK,
        )
        StatementColumn.objects.create(
            statement=kochat_statement,
            parent=niholxona,
            title_uz="Amalda",
            title_ru="Факт",
            ordering="1.1.3.1.2",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=kochat_statement,
            parent=niholxona,
            title_uz="Foiz",
            title_ru="Процент",
            ordering="1.1.3.1.3",
            is_user_input=False
        )

        kochatxona_2 = StatementColumn.objects.create(
            statement=kochat_statement,
            parent=subgroup,
            title_uz="Ko'chat",
            title_ru="Питомница",
            ordering="1.1.3.2",
        )
        StatementColumn.objects.create(
            statement=kochat_statement,
            parent=kochatxona_2,
            title_uz="Reja",
            title_ru="План",
            ordering="1.1.3.2.1",
            status_plan=StatementColumn.PlanStatus.YILLIK,
        )
        StatementColumn.objects.create(
            statement=kochat_statement,
            parent=kochatxona_2,
            title_uz="Amalda",
            title_ru="Факт",
            ordering="1.1.3.2.2",
            is_user_input=False
        )
        StatementColumn.objects.create(
            statement=kochat_statement,
            parent=kochatxona_2,
            title_uz="Foiz",
            title_ru="Процент",
            ordering="1.1.3.2.3",
            is_user_input=False
        )

        return self.stdout.write(self.style.SUCCESS("✅ Ko'chat va Nihol Yetishtirish Jami created!!!"))
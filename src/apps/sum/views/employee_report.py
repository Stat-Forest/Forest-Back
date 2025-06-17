from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.reports.models import ReportItem
from django.db.models import Sum
from django.db.models.functions import Cast
from django.db.models import FloatField


class SumEmployeeReportListAPIView(APIView):
    def get(self, request):
        employee_item = ReportItem.objects.filter(
            statement_column__title='Jami xodimlar soni'
        ).annotate(
            value_as_float=Cast('value', FloatField())
        ).order_by('-value_as_float').first()

        rep_1 = employee_item.report if employee_item else None

        vacancy_item = ReportItem.objects.filter(
            statement_column__title='Jami vakatlar soni'
        ).annotate(
            value_as_float=Cast('value', FloatField())
        ).order_by('-value_as_float').first()

        rep_2 = vacancy_item.report if vacancy_item else None

        total_employees = ReportItem.objects.filter(
            statement_column__title='Jami xodimlar soni'
        ).annotate(
            value_as_float=Cast('value', FloatField())
        ).aggregate(
            sum_value=Sum('value_as_float')
        )['sum_value'] or 0

        total_vacancies = ReportItem.objects.filter(
            statement_column__title='Jami vakatlar soni'
        ).annotate(
            value_as_float=Cast('value', FloatField())
        ).aggregate(
            sum_value=Sum('value_as_float')
        )['sum_value'] or 0

        data = {
            "Jami xodimlar": total_employees,
            "Eng ko'p xodimli tashkilot": getattr(rep_1.organization.name, 'name', 'UnKnown') if rep_1 else 'UnKnown',
            "Jami vakansiyalar": total_vacancies,
            "Eng ko'p vakansiyali tashkilot": getattr(rep_2.organization.name, 'name', 'UnKnown') if rep_2 else 'UnKnown'
        }

        return Response(data, status=status.HTTP_200_OK)

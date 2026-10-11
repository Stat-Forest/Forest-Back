"""
Qabul qilingan hisobot bo'yicha yig'ma hisobotlar (Tashkilot / Viloyat /
Respublika Jami) — Celery'da. Ilgari accept so'rovining o'zida sinxron
bajarilar, so'rov bir necha soniya davom etardi.
"""
import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(name="reports.aggregate_report_totals", ignore_result=True)
def aggregate_report_totals(report_id: str):
    from apps.reports.models import Report
    from apps.reports.services import aggregate_general_report, aggregate_national_report
    from apps.reports.services.individual_general_report import aggregate_individual_report
    from apps.utils.services import RegionChoices

    report = (
        Report.objects
        .select_related("statement", "deadline", "organization")
        .filter(id=report_id)
        .first()
    )
    if report is None:
        logger.info("aggregate_report_totals: report %s topilmadi", report_id)
        return
    if report.status != Report.StatusChoices.ACCEPTED or not report.is_report:
        return

    if not report.is_general and not report.is_republic:
        aggregate_individual_report(report)
        aggregate_general_report(statement=report.statement, deadline=report.deadline, region=report.region)
        aggregate_national_report(statement=report.statement, deadline=report.deadline, region=RegionChoices.REPUBLIC)
    elif report.region and report.is_general:
        aggregate_general_report(statement=report.statement, deadline=report.deadline, region=report.region)
        aggregate_national_report(statement=report.statement, deadline=report.deadline, region=RegionChoices.REPUBLIC)


@shared_task(name="reports.aggregate_statement_totals", ignore_result=True)
def aggregate_statement_totals(statement_id: str, deadline_id: str, region: str):
    """Bekor qilish / o'chirishdan keyin Viloyat va Respublika Jami qayta hisoblanadi."""
    from apps.reports.models import Deadline, Statement
    from apps.reports.services import aggregate_general_report, aggregate_national_report
    from apps.utils.services import RegionChoices

    statement = Statement.objects.filter(id=statement_id).first()
    deadline = Deadline.objects.filter(id=deadline_id).first()
    if statement is None or deadline is None:
        logger.info("aggregate_statement_totals: statement/deadline topilmadi (%s, %s)", statement_id, deadline_id)
        return
    if region:
        aggregate_general_report(statement=statement, deadline=deadline, region=region)
    aggregate_national_report(statement=statement, deadline=deadline, region=RegionChoices.REPUBLIC)


def _schedule(task, args):
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        task.apply(args=args)
        return
    transaction.on_commit(lambda: task.delay(*args))


def schedule_statement_totals(statement_id: str, deadline_id: str, region: str):
    _schedule(aggregate_statement_totals, (str(statement_id), str(deadline_id), region))


def schedule_report_totals(report_id: str):
    """
    Eager rejimda (testlar, CELERY_TASK_ALWAYS_EAGER) darhol shu yerda bajariladi;
    aks holda tranzaksiya commit bo'lgach worker'ga yuboriladi (worker commit'dan
    oldingi eski ma'lumotni o'qimasligi uchun).
    """
    _schedule(aggregate_report_totals, (report_id,))

from apps.reports.models.statement_column import StatementColumn


MONTHLY_STATUSES = [
    StatementColumn.PlanStatus.YANVAR,
    StatementColumn.PlanStatus.FEVRAL,
    StatementColumn.PlanStatus.MART,
    StatementColumn.PlanStatus.APREL,
    StatementColumn.PlanStatus.MAY,
    StatementColumn.PlanStatus.IYUN,
    StatementColumn.PlanStatus.IYUL,
    StatementColumn.PlanStatus.AVGUST,
    StatementColumn.PlanStatus.SENTABR,
    StatementColumn.PlanStatus.OKTABR,
    StatementColumn.PlanStatus.NOYABR,
    StatementColumn.PlanStatus.DEKABR,
]

QUARTERLY_STATUSES = [
    StatementColumn.PlanStatus.CHORAK_1,
    StatementColumn.PlanStatus.CHORAK_2,
    StatementColumn.PlanStatus.CHORAK_3,
    StatementColumn.PlanStatus.CHORAK_4,
]

YEARLY_STATUSES = [
    StatementColumn.PlanStatus.YILLIK,
]

YEARLY_TOTAL_STATUSES = [
    StatementColumn.PlanStatus.YILLIK_TOTAL,
]
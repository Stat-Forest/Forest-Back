# apps/report_admin_stat/services.py

from apps.reports.models import Report, Statement
from apps.users.models import CustomUser


class StatementReportStatService:

    def __init__(self, user):
        self.user = user

    def _get_base_reports_qs(self):
        user = self.user

        if user.role == CustomUser.Role.SUPER_ADMIN:
            if not user.organization and not user.statement:
                return Report.objects.filter(is_report=True)

        if user.statement:
            return Report.objects.filter(
                statement__parent_id=user.statement_id,
                is_report=True
            )

        if user.role == CustomUser.Role.HUDUDIY_BOSHQARMA:
            orgs = list(user.region_user_orgs.all())
            return Report.objects.filter(
                organization__in=orgs,
                is_report=True
            )

        if user.organization:
            return Report.objects.filter(
                organization=user.organization,
                is_report=True
            )

        return Report.objects.none()

    def _get_all_children(self, statement):
        """Rekursiv barcha child statementlarni olish"""
        children = []
        direct_children = Statement.objects.filter(parent=statement)
        for child in direct_children:
            children.append(child)
            children.extend(self._get_all_children(child))
        return children

    def _build_stat(self, reports_qs):
        return {
            "saved":     reports_qs.filter(status=Report.StatusChoices.SAVED).count(),
            "sent":      reports_qs.filter(status=Report.StatusChoices.SENT).count(),
            "cancelled": reports_qs.filter(status=Report.StatusChoices.CANCELLED).count(),
            "accepted":  reports_qs.filter(status=Report.StatusChoices.ACCEPTED).count(),
            "total":     reports_qs.count(),
        }

    def get_statistics(self):
        base_qs = self._get_base_reports_qs()
        parent_statements = Statement.objects.filter(
            parent__isnull=True,
            is_used=True
        ).order_by('name')

        result = []

        for parent in parent_statements:
            children = self._get_all_children(parent)
            all_ids = [parent.id] + [c.id for c in children]

            parent_reports = base_qs.filter(statement_id__in=all_ids)
            parent_stat = self._build_stat(parent_reports)

            children_data = []
            for child in children:
                child_reports = base_qs.filter(statement_id=child.id)
                child_stat = self._build_stat(child_reports)
                child_children_count = Statement.objects.filter(parent=child, is_used=True).count()
                children_data.append({
                    "id":    child.id,
                    "name":  getattr(child, 'name_uz', child.name),
                    "count": child_children_count,
                    **child_stat,
                })

            result.append({
                "id":       parent.id,
                "name":     getattr(parent, 'name_uz', parent.name),
                "count":    len(children),
                "children": children_data,
                **parent_stat,
            })

        return result

    def get_totals(self, statistics):
        """ЖАМИ qatorini hisoblash"""
        return {
            "count":     sum(s["count"]     for s in statistics),
            "saved":     sum(s["saved"]     for s in statistics),
            "sent":      sum(s["sent"]      for s in statistics),
            "cancelled": sum(s["cancelled"] for s in statistics),
            "accepted":  sum(s["accepted"]  for s in statistics),
            "total":     sum(s["total"]     for s in statistics),
        }
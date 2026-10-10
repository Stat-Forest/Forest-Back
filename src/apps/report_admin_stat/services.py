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

    @staticmethod
    def _empty_stat():
        return {"saved": 0, "sent": 0, "cancelled": 0, "accepted": 0, "total": 0}

    def _stat_for(self, counts, statement_ids):
        stat = self._empty_stat()
        for sid in statement_ids:
            row = counts.get(sid)
            if row:
                for key in stat:
                    stat[key] += row[key]
        return stat

    @staticmethod
    def _collect_children(children_by_parent, statement_id):
        """Rekursiv barcha avlodlar (xotiradagi daraxt bo'yicha, so'rovsiz)."""
        result = []
        for child in children_by_parent.get(statement_id, []):
            result.append(child)
            result.extend(StatementReportStatService._collect_children(children_by_parent, child.id))
        return result

    def get_statistics(self):
        """
        3 ta so'rov: statement'lar daraxti, statement bo'yicha status sonlari
        (bitta GROUP BY). Ilgari har bir statement uchun ~7 so'rov edi.
        """
        from collections import defaultdict
        from django.db.models import Count, Q

        S = Report.StatusChoices
        counts = {
            row["statement_id"]: row
            for row in (
                self._get_base_reports_qs()
                .order_by()
                .values("statement_id")
                .annotate(
                    saved=Count("id", filter=Q(status=S.SAVED)),
                    sent=Count("id", filter=Q(status=S.SENT)),
                    cancelled=Count("id", filter=Q(status=S.CANCELLED)),
                    accepted=Count("id", filter=Q(status=S.ACCEPTED)),
                    total=Count("id"),
                )
            )
        }

        statements = list(Statement.objects.order_by("name"))
        children_by_parent = defaultdict(list)
        for st in statements:
            children_by_parent[st.parent_id].append(st)

        result = []
        for parent in statements:
            if parent.parent_id is not None or not parent.is_used:
                continue
            children = self._collect_children(children_by_parent, parent.id)
            parent_stat = self._stat_for(counts, [parent.id] + [c.id for c in children])

            children_data = []
            for child in children:
                child_stat = self._stat_for(counts, [child.id])
                child_children_count = sum(
                    1 for c in children_by_parent.get(child.id, []) if c.is_used
                )
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
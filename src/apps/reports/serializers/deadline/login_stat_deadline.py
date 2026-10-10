# chat_serializers.py
from rest_framework import serializers
from apps.reports.models import Deadline, Report


class DeadlineReportListSerializer(serializers.ModelSerializer):
    statement_name = serializers.CharField(source='statement.name', read_only=True)
    statement_id = serializers.IntegerField(source='statement.id', read_only=True)
    statement_period = serializers.CharField(source='statement.period', read_only=True)
    parent_statement_name = serializers.CharField(source='statement.parent.name', read_only=True)

    total_organizations = serializers.SerializerMethodField()
    submitted_organizations = serializers.SerializerMethodField()
    pending_organizations = serializers.SerializerMethodField()
    submission_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Deadline
        fields = [
            'id',
            'statement_id',
            'statement_name',
            'parent_statement_name',
            'statement_period',
            'submit_at',
            'deadline_at',
            'total_organizations',
            'submitted_organizations',
            'pending_organizations',
            'submission_percentage',
            'created_at',
        ]

    def _get_deadlines_for_period(self, obj):
        all_deadlines = self.context.get("all_deadlines")
        if all_deadlines is not None:
            return [d for d in all_deadlines if d.submit_at == obj.submit_at]
        return [obj]

    def _stats(self, obj):
        """
        Davr (submit_at) bo'yicha {"total", "submitted"}.

        View `period_stats` ni bitta so'rov bilan tayyorlab beradi; u bo'lmasa
        davr uchun bir marta hisoblanadi va context'da keshlanadi. Ilgari har
        qator uchun bu hisob 3 marta, har bir muddat uchun alohida so'rovlar
        bilan qilinardi (10 qator ≈ 900 so'rov).
        """
        stats = self.context.get("period_stats")
        if stats is not None and obj.submit_at in stats:
            return stats[obj.submit_at]
        fallback = self.context.setdefault("_period_stats_fallback", {})
        if obj.submit_at not in fallback:
            fallback[obj.submit_at] = compute_period_stats(self._get_deadlines_for_period(obj))
        return fallback[obj.submit_at]

    def get_total_organizations(self, obj):
        return self._stats(obj)["total"]

    def get_submitted_organizations(self, obj):
        return self._stats(obj)["submitted"]

    def get_pending_organizations(self, obj):
        stats = self._stats(obj)
        return stats["total"] - stats["submitted"]

    def get_submission_percentage(self, obj):
        stats = self._stats(obj)
        if stats["total"] == 0:
            return 0
        return round((stats["submitted"] / stats["total"]) * 100, 2)


def compute_period_stats(deadlines):
    """Bir davrdagi muddatlar uchun tashkilotlar soni va topshirganlar soni (1 so'rov)."""
    org_ids = set()
    for d in deadlines:
        org_ids.update(o.id for o in d.organizations.all())  # prefetch bo'lsa so'rovsiz
    submitted = (
        Report.objects.filter(
            deadline__in=deadlines,
            status=Report.StatusChoices.ACCEPTED,
            is_report=True,
        )
        .values("organization").distinct().count()
    )
    return {"total": len(org_ids), "submitted": submitted}


def build_period_stats(deadlines):
    """
    Berilgan muddatlar uchun davr → {"total", "submitted"} xaritasi, 2 ta
    GROUP BY so'rov bilan (tashkilotlar prefetch qilinmaydi).
    """
    from django.db.models import Count
    from apps.reports.models import Deadline

    if not deadlines:
        return {}

    totals = {
        row["deadline__submit_at"]: row["n"]
        for row in (
            Deadline.organizations.through.objects
            .filter(deadline__in=deadlines)
            .order_by()
            .values("deadline__submit_at")
            .annotate(n=Count("organization_id", distinct=True))
        )
    }
    submitted = {
        row["deadline__submit_at"]: row["n"]
        for row in (
            Report.objects
            .filter(
                deadline__in=deadlines,
                status=Report.StatusChoices.ACCEPTED,
                is_report=True,
            )
            .order_by()
            .values("deadline__submit_at")
            .annotate(n=Count("organization_id", distinct=True))
        )
    }
    return {
        submit_at: {"total": totals.get(submit_at, 0), "submitted": submitted.get(submit_at, 0)}
        for submit_at in {d.submit_at for d in deadlines}
    }

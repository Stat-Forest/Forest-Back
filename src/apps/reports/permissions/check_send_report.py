from rest_framework.permissions import BasePermission
from apps.reports.services.quarter_validator import DaromadQuarterService


class CanSendReport(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role != 'tashkilot_rahbari':
            return False

        if DaromadQuarterService.is_daromad_report(obj):
            # Daromad: current_quarter ning statusini tekshiramiz
            current_quarter = obj.current_quarter
            if not current_quarter:
                return False
            return obj.get_quarter_status(current_quarter) == 'saved'

        # Oddiy report
        return obj.status == 'saved'
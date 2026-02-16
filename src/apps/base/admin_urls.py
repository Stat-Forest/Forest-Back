# base/admin_urls.py

from django.urls import path
from django.http import JsonResponse
from django.contrib.admin.models import LogEntry
from django.utils import timezone
from django.db.models import Count

from apps.reports.models import Report
from apps.users.models import CustomUser


def dashboard_charts(request):
    """Dashboard uchun chart ma'lumotlari (AJAX)"""
    try:
        # Oxirgi 7 kundagi hisobotlar
        last_week = timezone.now() - timezone.timedelta(days=7)
        daily_stats = []

        for i in range(7):
            day = timezone.now() - timezone.timedelta(days=i)
            count = Report.objects.filter(
                created_at__date=day.date()
            ).count()
            daily_stats.append({
                'date': day.strftime('%d-%m'),
                'count': count
            })

        # Statuslar bo'yicha statistika
        status_stats = {
            'saved': Report.objects.filter(status='saved').count(),
            'sent': Report.objects.filter(status='sent').count(),
            'accepted': Report.objects.filter(status='accepted').count(),
            'cancelled': Report.objects.filter(status='cancelled').count(),
        }

        return JsonResponse({
            'success': True,
            'daily_stats': daily_stats[::-1],  # Teskari tartibda
            'status_stats': status_stats,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def recent_activities_json(request):
    """So'ngi harakatlar (AJAX)"""
    try:
        logs = LogEntry.objects.select_related(
            'user', 'content_type'
        ).order_by('-action_time')[:20]

        activities = []
        for log in logs:
            activities.append({
                'id': log.id,
                'user': str(log.user) if log.user else 'Tizim',
                'action': log.get_change_message(),
                'object': log.object_repr,
                'time': log.action_time.isoformat(),
            })

        return JsonResponse({
            'success': True,
            'activities': activities
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# URL patterns
urlpatterns = [
    path('dashboard/charts/', dashboard_charts, name='admin_dashboard_charts'),
    path('dashboard/activities/', recent_activities_json, name='admin_recent_activities'),
]
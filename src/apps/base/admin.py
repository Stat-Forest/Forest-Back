# base/admin.py

from django.contrib import admin
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.utils import timezone
from django.db.models import Count
from django.urls import reverse

from apps.report_admin_stat.admin import StatementStatisticsAdmin
from apps.report_admin_stat.models import StatementStatistics
# Modellarni import qilish
from apps.reports.models import Report, Statement, Deadline, StatementColumn, Plant, Plan, PlanItem, PlantPlan, \
    PlantPlanItem, ReportStatistics
from apps.users.models import CustomUser, PersonalInfo
from apps.general.models import Organization, Announcement, Notification, Handbook, LandDocument, LandManagement, \
    Republic
from apps.logs.models import HistoryActionJournal

# MUHIM: Admin class'larni import qilish
from apps.users.admin import CustomUserAdmin
from apps.reports.admin import ReportAdmin, StatementAdmin, StatementColumnAdmin, DeadlineAdmin, PlantAdmin, PlanAdmin, \
    ReportStatisticsAdmin
from apps.general.admin import OrganizationAdmin, AnnouncementAdmin, NotificationAdmin, LandDocumentAdmin, \
    LandManagementAdmin
from apps.logs.admin import HistoryActionJournalAdmin


class ForestAdminSite(admin.AdminSite):
    site_header = "O'rmon Xo'jaligi - Boshqaruv Paneli"
    site_title = "O'rmon Admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}

        # Hozirgi vaqtni qo'shish
        extra_context["now"] = timezone.now()

        try:
            # ========== HISOBOTLAR STATISTIKASI ==========
            reports = Report.objects.all()
            total_reports = reports.count()
            extra_context["total_reports"] = total_reports
            extra_context["total_reports_count"] = total_reports  # Sidebar uchun

            saved = reports.filter(status="saved").count()
            sent = reports.filter(status="sent").count()
            accepted = reports.filter(status="accepted").count()
            cancelled = reports.filter(status="cancelled").count()

            extra_context["saved_reports"] = saved
            extra_context["sent_reports"] = sent
            extra_context["accepted_reports"] = accepted
            extra_context["cancelled_reports"] = cancelled

            # Foizlarni hisoblash
            if total_reports > 0:
                extra_context["accepted_percent"] = round((accepted / total_reports) * 100, 1)
                extra_context["sent_percent"] = round((sent / total_reports) * 100, 1)
                extra_context["saved_percent"] = round((saved / total_reports) * 100, 1)
                extra_context["cancelled_percent"] = round((cancelled / total_reports) * 100, 1)
            else:
                extra_context["accepted_percent"] = 0
                extra_context["sent_percent"] = 0
                extra_context["saved_percent"] = 0
                extra_context["cancelled_percent"] = 0

            # ========== FOYDALANUVCHILAR STATISTIKASI ==========
            users = CustomUser.objects.all()
            total_users = users.count()
            extra_context["total_users"] = total_users
            extra_context["active_users"] = users.filter(is_active=True).count()
            extra_context["new_users_today"] = users.filter(created_at__date=timezone.now().date()).count()

            # Users app qo'shimcha statistikalar
            extra_context["total_personal_info"] = PersonalInfo.objects.count()

            # ========== TASHKILOTLAR STATISTIKASI ==========
            organizations = Organization.objects.all()
            total_organizations = organizations.count()
            extra_context["total_organizations"] = total_organizations

            # ========== STATEMENTLAR STATISTIKASI ==========
            total_statements = Statement.objects.filter(is_used=True).count()
            extra_context["total_statements"] = total_statements

            # Reports app qo'shimcha statistikalar
            extra_context["total_statement_columns"] = StatementColumn.objects.count()
            extra_context["total_plants"] = Plant.objects.count()
            extra_context["total_plans_count"] = Plan.objects.count()
            extra_context["total_plan_items"] = PlanItem.objects.count()
            extra_context["total_plant_plans"] = PlantPlan.objects.count()

            # ========== MUDDATLAR STATISTIKASI ==========
            all_deadlines = Deadline.objects.all()
            total_deadlines = all_deadlines.count()
            extra_context["total_deadlines_count"] = total_deadlines

            # submit_at bor yoki yo'qligiga qarab
            with_submit = all_deadlines.filter(submit_at__isnull=False).exclude(submit_at='').count()
            without_submit = total_deadlines - with_submit

            extra_context["total_deadlines"] = total_deadlines
            extra_context["deadlines_with_submit"] = with_submit
            extra_context["deadlines_without_submit"] = without_submit
            extra_context["active_deadlines"] = with_submit
            extra_context["expired_deadlines"] = 0

            print(f"Total deadlines: {total_deadlines}")
            print(f"With submit_at: {with_submit}")
            print(f"Without submit_at: {without_submit}")

            # ========== GENERAL APP STATISTIKALARI ==========
            extra_context["total_notifications"] = Notification.objects.count()
            extra_context["total_announcements"] = Announcement.objects.count()
            extra_context["total_handbooks"] = Handbook.objects.count()
            extra_context["total_land_documents"] = LandDocument.objects.count()
            extra_context["total_land_management"] = LandManagement.objects.count()
            extra_context["total_republics"] = Republic.objects.count()

            # ========== LOGS APP STATISTIKALARI ==========
            extra_context["total_history_actions"] = HistoryActionJournal.objects.count()

            # ========== SO'NGI HARAKATLAR ==========
            extra_context["recent_actions"] = self.get_recent_actions(request)

            # ========== SO'NGI HISOBOTLAR ==========
            extra_context["recent_reports"] = Report.objects.select_related(
                'organization', 'statement'
            ).order_by('-created_at')[:5]

            # ========== KUTILAYOTGAN TOPSHIRIQLAR ==========
            # deadline_at ishlatilmaydi, submit_at asosida
            pending_list = []
            for deadline in all_deadlines.filter(submit_at__isnull=False).exclude(submit_at='')[:5]:
                pending_list.append(deadline)
            extra_context["pending_deadlines"] = pending_list

            # ========== OXIRGI KIRGANLAR ==========
            extra_context["recent_logins"] = CustomUser.objects.filter(
                last_login__isnull=False
            ).order_by('-last_login')[:5]

            # ========== FOYDALANUVCHILAR ROLLARI ==========
            role_stats = {}
            if users.exists():
                role_counts = users.values('role').annotate(count=Count('role'))

                for role_data in role_counts:
                    role_code = role_data['role']
                    count = role_data['count']
                    # Role kodini labelga o'tkazish
                    for role_choice in CustomUser.Role.choices:
                        if role_choice[0] == role_code:
                            role_stats[role_choice[1]] = count
                            break

            extra_context["user_roles"] = role_stats

            # Debug uchun print
            print("=" * 50)
            print("DASHBOARD STATISTIKALARI:")
            print(f"Users: {total_users}")
            print(f"Organizations: {total_organizations}")
            print(f"Statements: {total_statements}")
            print(f"Statement Columns: {extra_context['total_statement_columns']}")
            print(f"Reports: {total_reports}")
            print(f"Deadlines: {total_deadlines}")
            print(f"Plants: {extra_context['total_plants']}")
            print(f"Notifications: {extra_context['total_notifications']}")
            print(f"Announcements: {extra_context['total_announcements']}")
            print(f"Land Documents: {extra_context['total_land_documents']}")
            print("=" * 50)

        except Exception as e:
            print(f"Dashboard ma'lumotlarini yig'ishda xatolik: {e}")
            import traceback
            traceback.print_exc()

        # Super metodni chaqirish
        return super().index(request, extra_context)

    def get_recent_actions(self, request, limit=15):
        """So'ngi harakatlarni olish"""
        actions = []

        try:
            # LogEntry dan ma'lumotlarni olish
            log_entries = LogEntry.objects.select_related(
                'user', 'content_type'
            ).order_by('-action_time')[:limit]

            action_labels = {
                ADDITION: "Qo'shildi",
                CHANGE: "O'zgartirildi",
                DELETION: "O'chirildi",
            }

            action_icons = {
                ADDITION: 'fa-plus-circle text-success',
                CHANGE: 'fa-edit text-warning',
                DELETION: 'fa-trash text-danger',
            }

            for log in log_entries:
                # Vaqtni formatlash
                time_diff = timezone.now() - log.action_time
                if time_diff.days > 0:
                    time_str = f"{time_diff.days} kun, {time_diff.seconds // 3600} soat oldin"
                elif time_diff.seconds > 3600:
                    time_str = f"{time_diff.seconds // 3600} soat oldin"
                elif time_diff.seconds > 60:
                    time_str = f"{time_diff.seconds // 60} minut oldin"
                else:
                    time_str = "hozirgina"

                # Foydalanuvchi ma'lumotlari
                if log.user:
                    user_fullname = f"{log.user.first_name} {log.user.last_name}".strip()
                    if not user_fullname:
                        user_fullname = log.user.email
                    user_email = log.user.email

                    # User rolini olish
                    if hasattr(log.user, 'get_role_display'):
                        user_role = log.user.get_role_display()
                    else:
                        user_role = "Foydalanuvchi"
                else:
                    user_fullname = "Tizim"
                    user_email = ""
                    user_role = "System"

                # Model nomi
                if log.content_type:
                    model_name = log.content_type.name
                else:
                    model_name = "Noma'lum"

                # URL yaratish (agar object mavjud bo'lsa)
                url = None
                if log.content_type and log.object_id:
                    try:
                        url = reverse(
                            f'admin:{log.content_type.app_label}_{log.content_type.model}_change',
                            args=[log.object_id]
                        )
                    except:
                        pass

                actions.append({
                    'time': time_str,
                    'time_raw': log.action_time,
                    'user': {
                        'fullname': user_fullname,
                        'email': user_email,
                        'role': user_role,
                        'avatar': None,
                    },
                    'action': {
                        'type': action_labels.get(log.action_flag, 'Amal'),
                        'icon': action_icons.get(log.action_flag, 'fa-circle text-info'),
                        'message': log.get_change_message(),
                        'object': log.object_repr,
                    },
                    'model': {
                        'name': model_name,
                        'verbose': model_name,
                    },
                    'url': url,
                })
        except Exception as e:
            print(f"Recent actions xatolik: {e}")

        return actions


# Admin saytini yaratish
admin_site = ForestAdminSite(name="forest_admin")


# FAQAT LogEntry ni ro'yxatdan o'tkazish (chunki u Django'ning o'z modeli)
@admin.register(LogEntry, site=admin_site)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ['action_time', 'user', 'content_type', 'object_repr', 'action_flag']
    list_filter = ['action_flag', 'content_type', 'action_time']
    search_fields = ['object_repr', 'change_message']
    date_hierarchy = 'action_time'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# MUHIM: Barcha modellarni o'z admin class'lari bilan ro'yxatdan o'tkazish
# Users app dan
admin_site.register(CustomUser, CustomUserAdmin)

# Reports app dan
admin_site.register(Report, ReportAdmin)
admin_site.register(Statement, StatementAdmin)
admin_site.register(StatementColumn, StatementColumnAdmin)
admin_site.register(Deadline, DeadlineAdmin)
admin_site.register(Plant, PlantAdmin)
admin_site.register(Plan, PlanAdmin)

# General app dan
admin_site.register(Organization, OrganizationAdmin)
admin_site.register(Announcement, AnnouncementAdmin)
admin_site.register(Notification, NotificationAdmin)
admin_site.register(LandDocument, LandDocumentAdmin)
admin_site.register(LandManagement, LandManagementAdmin)

# Logs app dan
admin_site.register(HistoryActionJournal, HistoryActionJournalAdmin)
admin_site.register(ReportStatistics, ReportStatisticsAdmin)
admin_site.register(StatementStatistics, StatementStatisticsAdmin)
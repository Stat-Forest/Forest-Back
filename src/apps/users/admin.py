from datetime import timedelta
from django.contrib import admin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef, Subquery, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

from apps.users.models import CustomUser, PersonalInfo
from apps.logs.models import HistoryActionJournal
from apps.logs.mixins import AdminHistoryMixin
from apps.users.admin_forms import CustomUserAdminForm


# ================================
# INLINE
# ================================
class PersonalInfoInline(admin.StackedInline):
    model = PersonalInfo
    fk_name = "user"
    extra = 0
    can_delete = False


# ================================
# CUSTOM FILTER (LOGIN STATUS) - TUZATILGAN
# ================================
class LoginStatusFilter(admin.SimpleListFilter):
    title = _("Login holati")
    parameter_name = "login_status"

    def lookups(self, request, model_admin):
        return (
            ("never", _("Hech qachon sitega kirmagan")),
            ("7d", _("Oxirgi 7 kun ichida kirmagan")),
            ("1m", _("Oxirgi 1 oy ichida kirmagan")),
            ("3m", _("Oxirgi 3 oy ichida kirmagan")),
        )

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        now = timezone.now()

        if self.value() == "never":
            # Hech qachon login qilmagan userlar (admin va e-imzo orqali ham)
            # 'login' va 'add' actionlarini tekshiramiz
            user_ids_with_activity = HistoryActionJournal.objects.filter(
                Q(action='login') | Q(action='add')
            ).values_list('user_id', flat=True).distinct()

            return queryset.exclude(id__in=user_ids_with_activity)

        # Vaqt chegaralarini aniqlash
        if self.value() == "7d":
            date_threshold = now - timedelta(days=7)
        elif self.value() == "1m":
            date_threshold = now - timedelta(days=30)
        elif self.value() == "3m":
            date_threshold = now - timedelta(days=90)
        else:
            return queryset

        # Har bir user uchun eng oxirgi login yoki add vaqtini topish
        # E-imzo orqali yaratilgan userlar uchun ham 'add' actionini hisoblaymiz
        latest_activity_per_user = HistoryActionJournal.objects.filter(
            user_id=OuterRef('pk'),
            action__in=['login', 'add']
        ).order_by('-created_at').values('created_at')[:1]

        # Oxirgi faollik vaqti threshold dan oldingi yoki hech qachon faollik qilmagan userlar
        user_ids = queryset.annotate(
            last_activity_time=Subquery(latest_activity_per_user)
        ).filter(
            Q(last_activity_time__lt=date_threshold) | Q(last_activity_time__isnull=True)
        ).values_list('id', flat=True)

        return queryset.filter(id__in=user_ids)


# ================================
# USER ADMIN
# ================================
@admin.register(CustomUser)
class CustomUserAdmin(AdminHistoryMixin, admin.ModelAdmin):
    model = CustomUser
    form = CustomUserAdminForm
    inlines = [PersonalInfoInline]
    filter_horizontal = ("region_user_orgs",)

    list_display = (
        "id",
        "email",
        "organization",
        "statement",
        "first_name",
        "last_name",
        "role",
        "gender",
        "is_active",
        "get_last_login_display",
    )

    list_filter = (
        LoginStatusFilter,
        "role",
        "organization",
        "statement",
        "region",
    )

    search_fields = (
        "email",
        "first_name",
        "last_name",
        "phone_number",
        "passport_number",
        "jshshr",
        "user_number",
    )

    ordering = ("-created_at",)
    readonly_fields = ("last_login", "created_at", "updated_at", "user_number")
    actions = ["export_to_excel"]

    fieldsets = (
        (_("Login Credentials"), {"fields": ("email", "password")}),
        (_("Personal Info"), {
            "fields": (
                "first_name",
                "last_name",
                "father_name",
                "gender",
                "user_number",
                "statement",
                "organization",
                "date_of_birth",
                "date_of_place",
                "nationality",
                "passport_number",
                "jshshr",
                "phone_number",
                "address",
            )
        }),
        (_("Hududiy boshqarma"), {"fields": ("region", "region_user_orgs")}),
        (_("Permissions and Role"), {
            "fields": (
                "role",
                "is_active",
                "is_staff",
                "is_superuser",
                "is_disabled",
                "groups",
                "user_permissions",
            )
        }),
        (_("Important Dates"), {"fields": ("created_at", "updated_at")}),
    )

    add_fieldsets = (
        (_("Create User"), {
            "classes": ("wide",),
            "fields": (
                "email",
                "password1",
                "password2",
                "first_name",
                "last_name",
                "father_name",
                "gender",
                "nationality",
                "passport_number",
                "phone_number",
                "date_of_birth",
                "date_of_place",
                "address",
                "role",
                "statement",
                "organization",
                "region",
                "region_user_orgs",
                "is_active",
                "is_staff",
                "is_superuser",
                "is_disabled",
                "groups",
                "user_permissions",
            ),
        }),
    )

    # ================================
    # OXIRGI LOGIN VAQTINI KO'RSATISH
    # ================================
    def get_last_login_display(self, obj):
        """List display uchun oxirgi login"""
        # Login yoki Add actionni topamiz (E-imzo uchun ham)
        last_login = HistoryActionJournal.objects.filter(
            user=obj,
            action__in=['login', 'add']
        ).order_by('-created_at').first()

        if last_login:
            # Vaqt farqini hisoblash
            now = timezone.now()
            days_diff = (now - last_login.created_at).days

            if days_diff == 0:
                return f"✅ {last_login.created_at.strftime('%H:%M:%S')}"
            elif days_diff <= 7:
                return f"✅ {days_diff} kun oldin"
            elif days_diff <= 30:
                return f"⚠️ {days_diff} kun oldin"
            else:
                return f"❌ {days_diff} kun oldin"

        return "❌ Hech qachon"

    get_last_login_display.short_description = _("Oxirgi login")

    # ================================
    # OXIRGI LOGIN VAQTINI OLISH (export uchun)
    # ================================
    def get_user_last_login(self, user):
        """Foydalanuvchining oxirgi login vaqti"""
        last_login = HistoryActionJournal.objects.filter(
            user=user,
            action__in=['login', 'add']
        ).order_by('-created_at').first()

        if last_login:
            return last_login.created_at.strftime('%Y-%m-%d %H:%M:%S')
        return "Hech qachon"

    def get_login_status(self, user):
        """Login holatini aniqlash"""
        last_login = HistoryActionJournal.objects.filter(
            user=user,
            action__in=['login', 'add']
        ).order_by('-created_at').first()

        if not last_login:
            return "Hech qachon sitega kirmagan"

        now = timezone.now()
        days_diff = (now - last_login.created_at).days

        if days_diff <= 7:
            return "Faol"
        elif days_diff <= 30:
            return "Oxirgi 1 oy ichida kirmagan"
        elif days_diff <= 90:
            return "Oxirgi 3 oy ichida kirmagan"
        else:
            return "Oxirgi 3 oydan ko'proq vaqt ichida kirmagan"

    # ================================
    # EXPORT SELECTED USERS TO EXCEL
    # ================================
    def export_to_excel(self, request, queryset):
        """Excel formatda export qilish"""
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="foydalanuvchilar.xlsx"'

        wb = Workbook()
        ws = wb.active
        ws.title = "Foydalanuvchilar"

        # Stil uchun ranglar
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # Border
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # Data alignment
        data_alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        center_alignment = Alignment(horizontal="center", vertical="center")

        # Headerlar
        headers = [
            '№',
            'Email',
            'Ism',
            'Familiya',
            'Tashkilot',
            "Bo'lim",
            'Rol',
            'Jinsi',
            'Telefon',
            'Passport',
            'JSHSHR',
            'Faol',
            'Oxirgi login',
            'Login holati'
        ]

        # Header qo'shish
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = thin_border

        # Ma'lumotlar qo'shish
        for row_num, user in enumerate(queryset, start=2):
            # №
            cell = ws.cell(row=row_num, column=1)
            cell.value = row_num - 1
            cell.alignment = center_alignment
            cell.border = thin_border

            # Email
            cell = ws.cell(row=row_num, column=2)
            cell.value = str(user.email) if user.email else ''
            cell.alignment = data_alignment
            cell.border = thin_border

            # Ism
            cell = ws.cell(row=row_num, column=3)
            cell.value = str(user.first_name) if user.first_name else ''
            cell.alignment = data_alignment
            cell.border = thin_border

            # Familiya
            cell = ws.cell(row=row_num, column=4)
            cell.value = str(user.last_name) if user.last_name else ''
            cell.alignment = data_alignment
            cell.border = thin_border

            # Tashkilot
            cell = ws.cell(row=row_num, column=5)
            if user.organization:
                org_name = user.organization.name_uz if hasattr(user.organization,
                                                                'name_uz') and user.organization.name_uz else str(
                    user.organization)
                cell.value = org_name
            else:
                cell.value = ''
            cell.alignment = data_alignment
            cell.border = thin_border

            # Bayonot
            cell = ws.cell(row=row_num, column=6)
            cell.value = str(user.statement) if user.statement else ''
            cell.alignment = data_alignment
            cell.border = thin_border

            # Rol
            cell = ws.cell(row=row_num, column=7)
            cell.value = str(user.get_role_display()) if hasattr(user, 'get_role_display') else ''
            cell.alignment = data_alignment
            cell.border = thin_border

            # Jinsi
            cell = ws.cell(row=row_num, column=8)
            cell.value = str(user.get_gender_display()) if hasattr(user, 'get_gender_display') and user.gender else ''
            cell.alignment = center_alignment
            cell.border = thin_border

            # Telefon
            cell = ws.cell(row=row_num, column=9)
            cell.value = str(user.phone_number) if user.phone_number else ''
            cell.alignment = center_alignment
            cell.border = thin_border

            # Passport
            cell = ws.cell(row=row_num, column=10)
            cell.value = str(user.passport_number) if user.passport_number else ''
            cell.alignment = center_alignment
            cell.border = thin_border

            # JSHSHR
            cell = ws.cell(row=row_num, column=11)
            cell.value = str(user.jshshr) if user.jshshr else ''
            cell.alignment = center_alignment
            cell.border = thin_border

            # Faol
            cell = ws.cell(row=row_num, column=12)
            cell.value = "Ha" if user.is_active else "Yo'q"
            cell.alignment = center_alignment
            cell.border = thin_border

            # Oxirgi login
            cell = ws.cell(row=row_num, column=13)
            cell.value = self.get_user_last_login(user)
            cell.alignment = center_alignment
            cell.border = thin_border

            # Login holati
            cell = ws.cell(row=row_num, column=14)
            cell.value = self.get_login_status(user)
            cell.alignment = center_alignment
            cell.border = thin_border

        # Ustunlar kengligini sozlash
        ws.column_dimensions['A'].width = 6  # №
        ws.column_dimensions['B'].width = 30  # Email
        ws.column_dimensions['C'].width = 20  # Ism
        ws.column_dimensions['D'].width = 20  # Familiya
        ws.column_dimensions['E'].width = 50  # Tashkilot
        ws.column_dimensions['F'].width = 30  # Bayonot
        ws.column_dimensions['G'].width = 25  # Rol
        ws.column_dimensions['H'].width = 12  # Jinsi
        ws.column_dimensions['I'].width = 18  # Telefon
        ws.column_dimensions['J'].width = 15  # Passport
        ws.column_dimensions['K'].width = 18  # JSHSHR
        ws.column_dimensions['L'].width = 10  # Faol
        ws.column_dimensions['M'].width = 22  # Oxirgi login
        ws.column_dimensions['N'].width = 35  # Login holati

        # Birinchi qatorni (header) balandligini sozlash
        ws.row_dimensions[1].height = 30

        # Freeze panes - header qatorini doimo ko'rinishda qoldirish
        ws.freeze_panes = 'A2'

        wb.save(response)
        return response

    export_to_excel.short_description = _("Excel formatda yuklab olish")

    # ================================
    # SAVE / HUDUDIY BOSHQA LOGIKA
    # ================================
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("organization", "statement")

    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get("password") and not change:
            obj.set_password(form.cleaned_data["password"])
        elif "password" in form.changed_data:
            obj.set_password(obj.password)

        super().save_model(request, obj, form, change)

        role_group_map = {
            CustomUser.Role.SUPER_ADMIN: "super_admin",
            CustomUser.Role.RAHBARIYAT: "rahbariyat",
            CustomUser.Role.BOLIM_ADMIN: "bolim_admin",
            CustomUser.Role.TASHKILOT_RAHBARI: "tashkilot_rahbari",
            CustomUser.Role.TASHKILOT_HODIMI: "tashkilot_hodimi",
            CustomUser.Role.HUDUDIY_BOSHQARMA: "hududiy_boshqarma",
        }
        group_name = role_group_map.get(obj.role)
        if group_name:
            try:
                group = Group.objects.get(name=group_name)
                obj.groups.set([group])
            except Group.DoesNotExist:
                pass

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance

        if obj.role != CustomUser.Role.HUDUDIY_BOSHQARMA:
            return

        if not obj.region:
            raise ValidationError("Hududiy boshqarma uchun region majburiy")

        orgs = obj.region_user_orgs.all()
        if not orgs.exists():
            raise ValidationError("Kamida bitta tashkilot biriktirilishi shart")

        invalid_orgs = orgs.exclude(region=obj.region)
        if invalid_orgs.exists():
            raise ValidationError("Tashkilotlar regionga mos emas")

        if change:
            old_role = (
                CustomUser.objects
                .filter(pk=obj.pk)
                .values_list("role", flat=True)
                .first()
            )
            if (
                    old_role == CustomUser.Role.HUDUDIY_BOSHQARMA
                    and obj.role != CustomUser.Role.HUDUDIY_BOSHQARMA
            ):
                obj.region = None
                obj.region_user_orgs.clear()
                obj.save(update_fields=["region"])


# ================================
# GROUPNI ADMIN DAN CHIQARISH
# ================================
admin.site.unregister(Group)
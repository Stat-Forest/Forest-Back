"""
Modul administratori API (TZ §17.1 «маъмурий созламалар», §17.2 audit, §19.2, §24.1; plans §11.1-9).

Django `/admin/` IP allowlist ortida — buyurtmachi superadmini shu ekranlar orqali
ishlaydi. Faqat `is_module_admin` (super_admin / superuser / `yashil.manage_module`).
Har o'zgarish `apps.logs` jurnaliga yoziladi (`_history_user`).
"""
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.base.pagination import CustomPageNumberPagination
from apps.general.models import Organization
from apps.logs.models import HistoryActionJournal
from apps.yashil.api import CabinetMixin, IsAuthenticated, YashilError, invalid_format, not_found
from apps.yashil.models import (
    CalendarDay,
    CatalogItem,
    Mahalla,
    MahallaUnionRoute,
    SupplierAssignment,
    SupplierProfile,
    UnionUnit,
    YashilMembership,
)
from apps.yashil.serializers_admin import (
    AssignmentAdminSerializer,
    CalendarDayAdminSerializer,
    CatalogAdminSerializer,
    MahallaAdminSerializer,
    MembershipAdminSerializer,
    RouteAdminSerializer,
    SupplierProfileAdminSerializer,
    UnionUnitAdminSerializer,
)
from apps.yashil.services import capacity as capacity_service
from apps.yashil.services import imports, rules

User = get_user_model()
AUDIT_MODELS = (
    "Mahalla", "UnionUnit", "MahallaUnionRoute", "SupplierProfile", "SupplierAssignment", "YashilMembership",
    "CalendarDay", "CatalogItem", "NormRule", "ServiceCapacity", "YashilSetting",
)
IMPORT_MAX_SIZE = 10 * 1024 * 1024


class IsModuleAdmin(BasePermission):
    message = "Бу бўлим фақат модул администратори учун"
    code = "not_module_admin"

    def has_cabinet_permission(self, request, view):
        return view.is_admin


class AdminPagination(CustomPageNumberPagination):
    page_size = 25
    max_page_size = 200


class AdminView(CabinetMixin, APIView):
    permission_classes = [IsAuthenticated]
    cabinet_permission_classes = (IsModuleAdmin,)


class AdminCrudView(AdminView):
    """Ro'yxat (GET, sahifalangan) va yaratish (POST) — `model`, `serializer_class`, `filter_queryset`."""

    model = None
    serializer_class = None
    ordering: tuple = ()
    paginate = True

    def get_queryset(self):
        return self.model.objects.all().order_by(*self.ordering) if self.ordering else self.model.objects.all()

    def filter_queryset(self, qs, params):
        return qs

    def get(self, request):
        qs = self.filter_queryset(self.get_queryset(), request.query_params)
        if not self.paginate:
            return Response({"results": self.serializer_class(qs, many=True, context={"request": request}).data})
        paginator = AdminPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(self.serializer_class(page, many=True, context={"request": request}).data)

    def post(self, request):
        ser = self.serializer_class(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(self.serializer_class(obj, context={"request": request}).data, status=status.HTTP_201_CREATED)


class AdminDetailView(AdminView):
    model = None
    serializer_class = None
    allow_delete = False

    def get_object(self, pk):
        obj = self.model.objects.filter(pk=pk).first()
        if obj is None:
            raise not_found()
        return obj

    def patch(self, request, pk):
        obj = self.get_object(pk)
        ser = self.serializer_class(obj, data=request.data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(self.serializer_class(obj, context={"request": request}).data)

    def delete(self, request, pk):
        if not self.allow_delete:
            raise YashilError("Ўчириш мумкин эмас — амал қилиш муддатини ёпинг", error_code="delete_forbidden", status_code=405)
        obj = self.get_object(pk)
        obj._history_user = request.user
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _q(params, key="q"):
    return (params.get(key) or "").strip()


# ----------------------------------------------------------------------------- foydalanuvchi / a'zolik
class UserSearchView(AdminView):
    def get(self, request):
        q = _q(request.query_params)
        if len(q) < 2:
            raise invalid_format("Камида 2 та белги киритинг", "q")
        qs = (User.objects.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
              .select_related("organization").annotate(n=Count("yashil_memberships")).order_by("last_name", "email")[:20])
        return Response({"results": [{
            "id": str(u.id), "email": u.email, "full_name": f"{u.last_name} {u.first_name}".strip(), "role": u.role,
            "organization": u.organization.name if getattr(u, "organization_id", None) else "", "memberships": u.n,
        } for u in qs]})


class MembershipListView(AdminCrudView):
    model = YashilMembership
    serializer_class = MembershipAdminSerializer

    def get_queryset(self):
        return YashilMembership.objects.select_related("user", "mahalla", "union_unit", "organization").order_by("user__last_name", "member_type")

    def filter_queryset(self, qs, p):
        if p.get("member_type"):
            qs = qs.filter(member_type=p["member_type"])
        if p.get("active") == "1":
            qs = qs.filter(is_active=True)
        if q := _q(p):
            qs = qs.filter(Q(user__email__icontains=q) | Q(user__last_name__icontains=q) | Q(user__first_name__icontains=q)
                           | Q(mahalla__name__icontains=q) | Q(union_unit__name__icontains=q) | Q(organization__name__icontains=q))
        return qs


class MembershipDetailView(AdminDetailView):
    model = YashilMembership
    serializer_class = MembershipAdminSerializer


# ----------------------------------------------------------------------------- kalendar
class CalendarAdminView(AdminCrudView):
    model = CalendarDay
    serializer_class = CalendarDayAdminSerializer
    ordering = ("date",)
    paginate = False

    def filter_queryset(self, qs, p):
        if p.get("year"):
            try:
                qs = qs.filter(date__year=int(p["year"]))
            except ValueError:
                raise invalid_format("Йил нотўғри", "year")
        return qs


class CalendarDetailView(AdminDetailView):
    model = CalendarDay
    serializer_class = CalendarDayAdminSerializer
    allow_delete = True


# ----------------------------------------------------------------------------- mahalla, uyushma, yetkazib beruvchi
class MahallaAdminView(AdminCrudView):
    model = Mahalla
    serializer_class = MahallaAdminSerializer

    def get_queryset(self):
        return Mahalla.objects.select_related("region", "district").order_by("region__code", "district__code", "name")

    def filter_queryset(self, qs, p):
        if p.get("region"):
            qs = qs.filter(region_id=p["region"])
        if p.get("district"):
            qs = qs.filter(district_id=p["district"])
        if q := _q(p):
            qs = qs.filter(Q(name__icontains=q) | Q(source_code__icontains=q))
        return qs


class MahallaAdminDetailView(AdminDetailView):
    model = Mahalla
    serializer_class = MahallaAdminSerializer


class UnionUnitAdminView(AdminCrudView):
    model = UnionUnit
    serializer_class = UnionUnitAdminSerializer
    paginate = False

    def get_queryset(self):
        return UnionUnit.objects.select_related("region", "district").order_by("level", "name")

    def filter_queryset(self, qs, p):
        if q := _q(p):
            qs = qs.filter(name__icontains=q)
        return qs


class UnionUnitAdminDetailView(AdminDetailView):
    model = UnionUnit
    serializer_class = UnionUnitAdminSerializer


class OrganizationSearchView(AdminView):
    def get(self, request):
        q = _q(request.query_params)
        if len(q) < 2:
            raise invalid_format("Камида 2 та белги киритинг", "q")
        orgs = Organization.objects.filter(name__icontains=q).select_related("supplier_profile").order_by("name")[:20]
        out = []
        for o in orgs:
            profile = getattr(o, "supplier_profile", None)
            out.append({"id": str(o.id), "name": o.name, "region": o.region, "is_supplier": profile is not None,
                        "supplier_type": profile.supplier_type if profile else None})
        return Response({"results": out})


class SupplierAdminView(AdminCrudView):
    model = SupplierProfile
    serializer_class = SupplierProfileAdminSerializer
    paginate = False

    def get_queryset(self):
        return SupplierProfile.objects.select_related("organization").prefetch_related("service_regions", "service_districts").order_by("supplier_type", "organization__name")

    def filter_queryset(self, qs, p):
        if p.get("supplier_type"):
            qs = qs.filter(supplier_type=p["supplier_type"])
        if q := _q(p):
            qs = qs.filter(organization__name__icontains=q)
        return qs


class SupplierAdminDetailView(AdminDetailView):
    model = SupplierProfile
    serializer_class = SupplierProfileAdminSerializer


class AssignmentAdminView(AdminCrudView):
    model = SupplierAssignment
    serializer_class = AssignmentAdminSerializer

    def get_queryset(self):
        return SupplierAssignment.objects.select_related("mahalla", "organization").order_by("mahalla__name", "-valid_from")

    def filter_queryset(self, qs, p):
        if p.get("mahalla"):
            qs = qs.filter(mahalla_id=p["mahalla"])
        if p.get("organization"):
            qs = qs.filter(organization_id=p["organization"])
        if q := _q(p):
            qs = qs.filter(Q(mahalla__name__icontains=q) | Q(mahalla__source_code__icontains=q) | Q(organization__name__icontains=q))
        return qs


class AssignmentAdminDetailView(AdminDetailView):
    model = SupplierAssignment
    serializer_class = AssignmentAdminSerializer


class RouteAdminView(AdminCrudView):
    model = MahallaUnionRoute
    serializer_class = RouteAdminSerializer

    def get_queryset(self):
        return MahallaUnionRoute.objects.select_related("mahalla", "union_unit").order_by("mahalla__name", "-valid_from")

    def filter_queryset(self, qs, p):
        if p.get("mahalla"):
            qs = qs.filter(mahalla_id=p["mahalla"])
        if p.get("union_unit"):
            qs = qs.filter(union_unit_id=p["union_unit"])
        if q := _q(p):
            qs = qs.filter(Q(mahalla__name__icontains=q) | Q(mahalla__source_code__icontains=q) | Q(union_unit__name__icontains=q))
        return qs


class RouteAdminDetailView(AdminDetailView):
    model = MahallaUnionRoute
    serializer_class = RouteAdminSerializer


# ----------------------------------------------------------------------------- katalog, quvvat
class CatalogAdminView(AdminCrudView):
    model = CatalogItem
    serializer_class = CatalogAdminSerializer
    ordering = ("supplier_type", "order", "code")
    paginate = False

    def filter_queryset(self, qs, p):
        if p.get("supplier_type"):
            qs = qs.filter(supplier_type=p["supplier_type"])
        return qs


class CatalogAdminDetailView(AdminDetailView):
    model = CatalogItem
    serializer_class = CatalogAdminSerializer


class CapacityAdminView(AdminView):
    """GET ?organization=&period= — DM quvvati; PUT {organization, period, rows:[{catalog_item, capacity}]}."""

    def _org(self, value):
        org = Organization.objects.filter(pk=value).first() if value else None
        if org is None or not SupplierProfile.objects.filter(organization=org, supplier_type=SupplierProfile.SupplierType.DM).exists():
            raise invalid_format("DM ташкилоти кўрсатилиши керак", "organization")
        return org

    def get(self, request):
        org = self._org(request.query_params.get("organization"))
        try:
            return Response(capacity_service.capacity_payload(org, request.query_params.get("period") or ""))
        except capacity_service.CapacityError as exc:
            raise YashilError(exc.message, error_code=exc.code, field=exc.field, status_code=exc.status)

    def put(self, request):
        d = request.data if isinstance(request.data, dict) else {}
        org = self._org(d.get("organization"))
        try:
            return Response(capacity_service.set_capacity(org, d.get("period") or "", d.get("rows") or [], request.user))
        except capacity_service.CapacityError as exc:
            raise YashilError(exc.message, error_code=exc.code, field=exc.field, status_code=exc.status)


# ----------------------------------------------------------------------------- sozlamalar, audit
class SettingsAdminView(AdminView):
    def get(self, request):
        return Response({"results": rules.snapshot()})

    def put(self, request):
        from datetime import date

        d = request.data if isinstance(request.data, dict) else {}
        eff = d.get("effective_from")
        try:
            eff = date.fromisoformat(eff) if eff else None
        except (TypeError, ValueError):
            raise invalid_format("Сана YYYY-MM-DD кўринишида", "effective_from")
        try:
            rules.set_value(str(d.get("key") or ""), d.get("value"), request.user, effective_from=eff, note=str(d.get("note") or ""))
        except rules.RuleError as exc:
            raise YashilError(str(exc), error_code="validation", field=exc.field)
        return Response({"results": rules.snapshot()})


class AuditAdminView(AdminView):
    def get(self, request):
        p = request.query_params
        qs = HistoryActionJournal.objects.filter(model_name__in=AUDIT_MODELS).select_related("user").order_by("-created_at")
        if p.get("model"):
            qs = qs.filter(model_name=p["model"])
        if q := _q(p):
            qs = qs.filter(Q(object_repr__icontains=q) | Q(user__email__icontains=q))
        paginator = AdminPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response([{
            "id": r.id, "created_at": r.created_at.isoformat(), "user": r.user.email if r.user_id else "",
            "action": r.action, "model_name": r.model_name, "object_id": r.object_id, "object_repr": r.object_repr,
            "change_message": r.change_message,
        } for r in page])


# ----------------------------------------------------------------------------- Excel importlar
def read_upload(request):
    f = request.FILES.get("file")
    if f is None:
        raise invalid_format("Файл юборилмади", "file")
    if f.size > IMPORT_MAX_SIZE:
        raise invalid_format("Файл 10 МБ дан катта", "file")
    if not f.name.lower().endswith(".xlsx"):
        raise invalid_format("Фақат .xlsx файл", "file")
    return f


def is_dry_run(request) -> bool:
    return str(request.data.get("dry_run", "1")).lower() in ("1", "true", "yes")


def import_response(run):
    """Servis importini bajaradi: fayl xatosi 400; tasdiq + xato — 422 (hech narsa yozilmagan)."""
    try:
        result = run()
    except imports.ImportFileError as exc:
        raise invalid_format(str(exc), "file")
    if not result.dry_run and result.errors:
        err = YashilError(f"Файлда {len(result.errors)} та хато бор — тузатиб қайта юкланг", error_code="import_has_errors")
        err.extra = result.to_dict()
        raise err
    return Response(result.to_dict())


class _ImportView(AdminView):
    func = None
    extra_param = None  # ("source_ref" | "source_doc", kwarg nomi)

    def post(self, request):
        f = read_upload(request)
        kwargs = {"dry_run": is_dry_run(request), "partial": False, "user": request.user}
        if self.extra_param:
            kwargs[self.extra_param] = str(request.data.get(self.extra_param) or "")[:300]
        return import_response(lambda: type(self).func(f, **kwargs))


class MahallaImportView(_ImportView):
    func = staticmethod(imports.import_mahallas)


class AssignmentImportView(_ImportView):
    func = staticmethod(imports.import_assignments)
    extra_param = "source_doc"


class RouteImportView(_ImportView):
    func = staticmethod(imports.import_routes)
    extra_param = "source_doc"


class CalendarImportView(_ImportView):
    func = staticmethod(imports.import_calendar)
    extra_param = "source_ref"

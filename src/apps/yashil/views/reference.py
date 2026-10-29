"""Ma'lumotnoma va kabinet API'lari (1-bosqich)."""
from datetime import date

from django.db.models import Q
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.base.pagination import CustomPageNumberPagination
from apps.billing.models import District, Region
from apps.yashil.api import CabinetMixin, HasCabinet, IsAuthenticated, invalid_format, not_found
from apps.yashil.models import CalendarDay, CatalogItem, Mahalla, ObjectType, Season, SupplierProfile
from apps.yashil.serializers import (
    CabinetSerializer,
    CalendarDaySerializer,
    CatalogItemSerializer,
    DistrictSerializer,
    MahallaSerializer,
    ObjectTypeSerializer,
    RegionSerializer,
    SeasonSerializer,
    SupplierSerializer,
    UnionUnitSerializer,
)
from apps.yashil.services import rules
from apps.yashil.services import scope as scope_service
from apps.yashil.services.workdays import (
    add_workdays,
    calendar_from_db,
)


class YashilAPIView(CabinetMixin, APIView):
    permission_classes = [IsAuthenticated]
    cabinet_permission_classes = (HasCabinet,)


class YashilListView(CabinetMixin, ListAPIView):
    permission_classes = [IsAuthenticated]
    cabinet_permission_classes = (HasCabinet,)
    pagination_class = None


class MeView(CabinetMixin, APIView):
    """Foydalanuvchining kabinetlari; a'zolik bo'lmasa ham 200 (frontend menyuni yashiradi)."""

    permission_classes = [IsAuthenticated]
    cabinet_permission_classes = ()

    def get(self, request):
        cabinets = list(scope_service.memberships_for(request.user))
        from apps.yashil.models import YashilNotification

        unread = YashilNotification.objects.filter(recipient_user=request.user, read_at__isnull=True).count()
        return Response({
            "unread_notifications": unread,
            "user": {
                "id": str(request.user.id),
                "full_name": f"{request.user.last_name} {request.user.first_name}".strip(),
                "role": request.user.role,
            },
            "is_admin": self.is_admin,
            "is_member": bool(cabinets),
            "active_cabinet": CabinetSerializer(self.cabinet).data if self.cabinet else None,
            "cabinets": CabinetSerializer(cabinets, many=True).data,
            "rules": {"review_workdays": rules.get("review_workdays"), "delivery_workdays": rules.get("delivery_workdays")},
        })


class RegionListView(YashilListView):
    serializer_class = RegionSerializer
    queryset = Region.objects.all().order_by("code")


class DistrictListView(YashilListView):
    serializer_class = DistrictSerializer

    def get_queryset(self):
        qs = District.objects.all().order_by("code")
        region = self.request.query_params.get("region")
        return qs.filter(region_id=region) if region else qs


class MahallaListView(CabinetMixin, ListAPIView):
    permission_classes = [IsAuthenticated]
    cabinet_permission_classes = (HasCabinet,)
    serializer_class = MahallaSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = Mahalla.objects.filter(is_active=True).select_related("region", "district")
        qs = scope_service.scope_mahallas(qs, self.cabinet)
        params = self.request.query_params
        if params.get("district"):
            qs = qs.filter(district_id=params["district"])
        if params.get("region"):
            qs = qs.filter(region_id=params["region"])
        if params.get("q"):
            q = params["q"].strip()
            qs = qs.filter(Q(name__icontains=q) | Q(source_code__icontains=q) | Q(address__icontains=q))
        return qs.order_by("district__code", "name")


class SeasonListView(YashilListView):
    serializer_class = SeasonSerializer
    queryset = Season.objects.filter(is_active=True)


class ObjectTypeListView(YashilListView):
    serializer_class = ObjectTypeSerializer
    queryset = ObjectType.objects.filter(is_active=True)


class SuppliersForMahallaView(YashilAPIView):
    """Mahalla uchun yetkazib beruvchilar: asosiy xo'jalik, boshqa xo'jaliklar, DM'lar, uyushma bo'linmasi."""

    def get(self, request, mahalla_id):
        if not scope_service.mahalla_visible(mahalla_id, self.cabinet):
            raise not_found()
        mahalla = Mahalla.objects.filter(pk=mahalla_id, is_active=True).select_related("region", "district").first()
        if mahalla is None:
            raise not_found()
        assignment = scope_service.primary_forest_assignment(mahalla)
        primary = assignment.organization.supplier_profile if assignment else None
        alternatives = scope_service.forest_suppliers(exclude_org_id=primary.organization_id if primary else None)
        route = scope_service.union_route(mahalla)
        return Response({
            "mahalla": {"id": str(mahalla.id), "name": mahalla.name},
            "forest": {
                "primary": SupplierSerializer(primary).data if primary else None,
                "assignment_valid_to": assignment.valid_to if assignment else None,
                "alternatives": SupplierSerializer(alternatives, many=True).data,
                "message": None if primary else scope_service.NOT_ASSIGNED_FOREST,
            },
            "dm": {"options": SupplierSerializer(scope_service.dm_suppliers_for(mahalla), many=True).data},
            "union": UnionUnitSerializer(route.union_unit).data if route else None,
            "union_message": None if route else scope_service.NOT_ROUTED_UNION,
        })


class CatalogListView(YashilListView):
    serializer_class = CatalogItemSerializer

    def get_queryset(self):
        qs = CatalogItem.objects.filter(is_active=True)
        supplier = self.request.query_params.get("supplier")
        if supplier:
            profile = SupplierProfile.objects.filter(organization_id=supplier).first()
            if profile is None:
                raise not_found("Етказиб берувчи топилмади")
            qs = qs.filter(supplier_type=profile.supplier_type)
        supplier_type = self.request.query_params.get("supplier_type")
        if supplier_type:
            qs = qs.filter(supplier_type=supplier_type)
        return qs.order_by("supplier_type", "order", "code")


class CalendarListView(YashilListView):
    serializer_class = CalendarDaySerializer

    def get_queryset(self):
        qs = CalendarDay.objects.all()
        year = self.request.query_params.get("year")
        if year:
            if not year.isdigit():
                raise invalid_format("Йил YYYY кўринишида бўлиши керак", "year")
            qs = qs.filter(date__year=int(year))
        return qs.order_by("date")


class CalendarDueView(YashilAPIView):
    """start sanasidan 3 va 10 ish kuni muddatlari (frontend ko'rsatish uchun)."""

    def get(self, request):
        raw = request.query_params.get("start")
        try:
            start = date.fromisoformat(raw) if raw else date.today()
        except (TypeError, ValueError):
            raise invalid_format("Сана YYYY-MM-DD кўринишида бўлиши керак", "start")
        cal = calendar_from_db()
        return Response({
            "start": start.isoformat(),
            "review_due": add_workdays(start, rules.get("review_workdays", start), cal).isoformat(),
            "delivery_due": add_workdays(start, rules.get("delivery_workdays", start), cal).isoformat(),
        })

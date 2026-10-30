"""
«Яшил маҳалла» API'sining OpenAPI tavsifi (TZ §19.1, §21).

View'lar oddiy APIView (serializer'ni o'zi chaqiradi), shuning uchun drf-spectacular so'rov va
javobni taxmin qila olmaydi. Har amal (`<ViewClass>.<method>`) uchun qisqa tavsif, so'rov va javob
shu yerda `OPERATIONS` da yoziladi; `schema.YashilAutoSchema` ularni o'qiydi va umumiy qismlarni
qo'shadi: kabinet header'i, `Idempotency-Key`, xato javoblari (YashilError), bo'lim tegi.

Fayl: `python manage.py yashil_openapi --out docs/yashil/openapi-yashil.yaml`.
Swagger UI prod'da faqat admin uchun (audit #1086) — tavsif repo'dagi fayl orqali beriladi.
"""
from dataclasses import dataclass
from typing import Any

from django.urls import include, path
from drf_spectacular.drainage import GENERATOR_STATS
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.settings import patched_settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from rest_framework import serializers

from apps.yashil import serializers as ref_s
from apps.yashil import serializers_acts as act_s
from apps.yashil import serializers_admin as adm_s
from apps.yashil import serializers_cancel as can_s
from apps.yashil import serializers_orders as ord_s
from apps.yashil import serializers_stock as stk_s

# ----------------------------------------------------------------------------- umumiy komponentlar
_PAGES: dict[str, type] = {}


def page_of(item=None, name=None):
    """Sahifalangan javob: {count, next, previous, results: [item]} (CustomPageNumberPagination)."""
    name = name or f"Paginated{item.__name__.removesuffix('Serializer')}List"
    if name not in _PAGES:
        results = item(many=True) if item else serializers.ListField(child=serializers.DictField())
        _PAGES[name] = type(name, (serializers.Serializer,), {
            "count": serializers.IntegerField(),
            "next": serializers.URLField(allow_null=True),
            "previous": serializers.URLField(allow_null=True),
            "results": results,
            "__module__": __name__,
        })
    return _PAGES[name]


def form(name, **fields):
    return type(name, (serializers.Serializer,), {**fields, "__module__": __name__})


VersionBody = form("VersionNoRequest", version_no=serializers.IntegerField(required=False, help_text="Жорий version_no (эски бўлса 409)"))
UploadBody = form("FileUploadRequest", file=serializers.FileField(), kind=serializers.CharField(required=False))
ImportBody = form(
    "ImportRequest",
    file=serializers.FileField(help_text="XLSX ёки CSV"),
    dry_run=serializers.BooleanField(required=False, help_text="1 — фақат текшириш, ҳеч нарса ёзилмайди"),
    source_doc=serializers.CharField(required=False, help_text="Асос ҳужжат (бириктириш/йўналиш импорти)"),
    source_ref=serializers.CharField(required=False, help_text="Манба (календарь импорти)"),
)
SignTaskBody = form("SignTaskRequest", version_no=serializers.IntegerField(required=False))
ExportBody = form(
    "ExportRequest",
    kind=serializers.CharField(help_text="registry / summary / …"),
    format=serializers.CharField(help_text="xlsx / csv / pdf"),
    filters=serializers.DictField(required=False, help_text="reports/registry/ фильтрлари"),
)
CapacityBody = form(
    "CapacityRequest",
    organization=serializers.UUIDField(required=False, help_text="Фақат маъмурий амалда"),
    period=serializers.CharField(help_text="YYYY-MM"),
    rows=serializers.ListField(child=serializers.DictField()),
)
SettingBody = form(
    "SettingRequest",
    key=serializers.CharField(),
    value=serializers.JSONField(),
    effective_from=serializers.DateField(required=False),
    note=serializers.CharField(required=False),
)


def q(name, description, type_=str, enum=None, many=False):
    return OpenApiParameter(name, type_, OpenApiParameter.QUERY, required=False, description=description, enum=enum,
                            many=many, explode=False if many else None)


PAGE = [q("page", "Саҳифа рақами", int), q("per_page", "Саҳифадаги қатор (энг кўпи 100–200)", int)]
REGISTRY_FILTERS = [
    q("period_basis", "Давр асоси", enum=["submitted", "accepted", "delivered"]),
    q("date_from", "Давр боши (YYYY-MM-DD)", OpenApiTypes.DATE),
    q("date_to", "Давр охири (YYYY-MM-DD)", OpenApiTypes.DATE),
    q("region", "Вилоят ID"), q("district", "Туман ID"), q("mahalla", "Маҳалла ID"),
    q("supplier_org", "Етказиб берувчи ташкилот ID"),
    q("route", "Йўналиш", enum=["forest", "dm"]),
    q("catalog_item", "Каталог позицияси ID"), q("category", "Каталог тоифаси"),
    q("state", "Ҳолатлар, вергул билан"),
    q("overdue", "Фақат муддати ўтганлар (1)"),
    q("q", "Қидирув матни"),
    q("ordering", "Саралаш майдони"),
]
ADMIN_Q = [*PAGE, q("q", "Қидирув матни")]


@dataclass(frozen=True)
class Op:
    summary: str
    request: Any = None
    response: Any = OpenApiTypes.OBJECT
    status: int = 200
    params: tuple = ()
    description: str = ""
    multipart: bool = False


OBJ = OpenApiTypes.OBJECT
DETAIL_ORDER = ord_s.OrderDetailSerializer
DETAIL_ACT = act_s.ActDetailSerializer
DOC_TASK = form("SignTaskResponse", document_version=ord_s.DocumentVersionSerializer(), challenge=serializers.CharField(required=False),
                payload=serializers.CharField(required=False))

OPERATIONS: dict[str, Op] = {
    # --- foydalanuvchi va ma'lumotnomalar
    "MeView.get": Op("Фойдаланувчи кабинетлари ва фаол кабинет"),
    "RegionListView.get": Op("Вилоятлар", response=ref_s.RegionSerializer(many=True)),
    "DistrictListView.get": Op("Туманлар", response=ref_s.DistrictSerializer(many=True), params=(q("region", "Вилоят ID"),)),
    "MahallaListView.get": Op("Маҳаллалар (кабинет кўламида)", response=page_of(ref_s.MahallaSerializer),
                              params=(*PAGE, q("region", "Вилоят ID"), q("district", "Туман ID"), q("q", "Номи бўйича қидирув"))),
    "SeasonListView.get": Op("Мавсумлар", response=ref_s.SeasonSerializer(many=True)),
    "ObjectTypeListView.get": Op("Объект турлари", response=ref_s.ObjectTypeSerializer(many=True)),
    "SuppliersForMahallaView.get": Op("Маҳалла учун етказиб берувчилар (асосий, муқобил, ДМ, уюшма)"),
    "CatalogListView.get": Op("Каталог (йўналиш бўйича)", response=ref_s.CatalogItemSerializer(many=True),
                              params=(q("supplier", "Етказиб берувчи ташкилот ID"), q("supplier_type", "forest / dm"))),
    "CalendarListView.get": Op("Иш кунлари календари", response=ref_s.CalendarDaySerializer(many=True), params=(q("year", "Йил", int),)),
    "CalendarDueView.get": Op("3 ва 10 иш кунлик муддатлар ҳисоби", params=(q("start", "Бошланғич сана (YYYY-MM-DD)", OpenApiTypes.DATE),)),
    # --- buyurtmalar
    "OrderListCreateView.get": Op("Буюртмалар рўйхати", response=page_of(ord_s.OrderListSerializer), params=(*PAGE, *REGISTRY_FILTERS)),
    "OrderListCreateView.post": Op("Буюртма қораламасини яратиш", request=ord_s.OrderWriteSerializer, response=DETAIL_ORDER, status=201),
    "OrderDetailView.get": Op("Буюртма тафсилоти", response=DETAIL_ORDER),
    "OrderDetailView.patch": Op("Қоралама ёки қайтарилган буюртмани таҳрирлаш", request=ord_s.OrderWriteSerializer, response=DETAIL_ORDER),
    "OrderAttachmentsView.post": Op("Буюртмага файл илова қилиш", request=UploadBody, response=ord_s.AttachmentSerializer, status=201, multipart=True),
    "OrderAttachmentDeleteView.delete": Op("Иловани ўчириш (фақат таҳрирланадиган ҳолатда)", response=None, status=204),
    "OrderDocumentView.post": Op("Буюртманома ҳужжатини тайёрлаш ва имзо топшириғи", request=VersionBody, response=DOC_TASK),
    "OrderSubmitView.post": Op("Имзолаб юбориш", request=ord_s.SubmitSerializer, response=DETAIL_ORDER),
    "OrderReviewView.post": Op("Уюшма кўриб чиқишни бошлайди", request=VersionBody, response=DETAIL_ORDER),
    "OrderForwardView.post": Op("Уюшма етказиб берувчига йўллайди", request=VersionBody, response=DETAIL_ORDER),
    "OrderReturnView.post": Op("Сабаб билан қайтариш", request=ord_s.ReturnSerializer, response=DETAIL_ORDER),
    "OrderAcceptView.post": Op("Етказиб берувчи ижрога қабул қилади", request=ord_s.AcceptSerializer, response=DETAIL_ORDER),
    "OrderEventsView.get": Op("Ҳолатлар тарихи", response=ord_s.OrderEventSerializer(many=True)),
    # --- bekor qilish
    "OrderCancelView.post": Op("Бекор қилиш (қоралама — дарҳол, бошқалари — сўров)", request=can_s.CancelRequestWriteSerializer,
                               response=can_s.CancelRequestSerializer, status=201),
    "CancelListView.get": Op("Бекор қилиш сўровлари", response=page_of(can_s.CancelRequestSerializer),
                             params=(*PAGE, q("order", "Буюртма ID"), q("status", "Ҳолатлар, вергул билан"))),
    "CancelDetailView.get": Op("Бекор қилиш сўрови", response=can_s.CancelRequestSerializer),
    "CancelAgreeView.post": Op("Бекор қилишга рози бўлиш", request=can_s.CancelDecisionSerializer, response=can_s.CancelRequestSerializer),
    "CancelApproveView.post": Op("Бекор қилишни тасдиқлаш", request=can_s.CancelDecisionSerializer, response=can_s.CancelRequestSerializer),
    "CancelRejectView.post": Op("Бекор қилишни рад этиш", request=can_s.CancelDecisionSerializer, response=can_s.CancelRequestSerializer),
    # --- dalolatnomalar
    "OrderActsCreateView.post": Op("Етказишни қайд этиш ва акт қораламаси", request=act_s.ActWriteSerializer, response=DETAIL_ACT, status=201),
    "ActListView.get": Op("Актлар рўйхати", response=page_of(act_s.ActListSerializer),
                          params=(*PAGE, q("order", "Буюртма ID"), q("status", "Ҳолатлар, вергул билан"), q("q", "Рақам, буюртма ёки маҳалла"),
                                  *[p for p in REGISTRY_FILTERS if p.name not in ("state", "q", "ordering")])),
    "ActDetailView.get": Op("Акт тафсилоти", response=DETAIL_ACT),
    "ActDetailView.patch": Op("Акт қораламасини таҳрирлаш", request=act_s.ActWriteSerializer, response=DETAIL_ACT),
    "ActAttachmentsView.post": Op("Актга файл илова қилиш", request=UploadBody, response=act_s.ActAttachmentSerializer, status=201, multipart=True),
    "ActAttachmentDeleteView.delete": Op("Акт иловасини ўчириш", response=None, status=204),
    "ActSignTaskView.post": Op("Акт ҳужжатини тайёрлаш ва имзо топшириғи", request=SignTaskBody, response=DOC_TASK),
    "ActSignView.post": Op("Актни имзолаш (етказиб берувчи — юбориш, маҳалла — қабул)", request=act_s.ActSignSerializer, response=DETAIL_ACT),
    "ActReturnView.post": Op("Маҳалла актни изоҳ билан қайтаради", request=act_s.ActReturnSerializer, response=DETAIL_ACT),
    "ActCancelView.post": Op("Акт қораламасини бекор қилиш", request=act_s.ActCancelSerializer, response=DETAIL_ACT),
    # --- ombor
    "StockSummaryView.get": Op("Омбор қолдиқлари", params=(q("organization", "Ташкилот ID (кузатувчи/маъмур)"),)),
    "StockOrganizationsView.get": Op("Омбори бор етказиб берувчилар", params=(q("q", "Номи бўйича қидирув"),)),
    "StockMovementListView.get": Op("Омбор ҳаракатлари", response=page_of(stk_s.StockMovementSerializer),
                                    params=(*PAGE, q("organization", "Ташкилот ID"), q("item", "Каталог позицияси ID"),
                                            q("kind", "Турлари, вергул билан"), q("status", "Ҳолатлари, вергул билан"))),
    "StockReceiptView.post": Op("Кирим", request=stk_s.StockEntrySerializer, status=201),
    "StockOpeningView.post": Op("Бошланғич қолдиқ", request=stk_s.StockEntrySerializer, status=201),
    "StockReturnInView.post": Op("Қайтарилган товар кирими", request=stk_s.StockEntrySerializer, status=201),
    "StockReversalRequestView.post": Op("Ҳаракатни бекор қилиш сўрови", request=stk_s.ReversalRequestSerializer, status=201),
    "StockReversalApproveView.post": Op("Бекор қилиш сўровини тасдиқлаш", request=stk_s.DecisionSerializer),
    "StockReversalRejectView.post": Op("Бекор қилиш сўровини рад этиш", request=stk_s.DecisionSerializer),
    "ServiceCapacityView.get": Op("ДМ хизмат қуввати", params=(q("period", "YYYY-MM"),)),
    "ServiceCapacityView.put": Op("ДМ хизмат қувватини киритиш", request=CapacityBody),
    "StockOpeningImportView.post": Op("Бошланғич қолдиқларни файлдан юклаш", request=ImportBody, multipart=True),
    # --- modul ma'muri
    "UserSearchView.get": Op("Фойдаланувчи қидириш", params=(q("q", "Email ёки исм"),)),
    "OrganizationSearchView.get": Op("Ташкилот қидириш", params=(q("q", "Номи"),)),
    "MembershipListView.get": Op("Кабинет аъзоликлари", response=page_of(adm_s.MembershipAdminSerializer),
                                 params=(*ADMIN_Q, q("member_type", "Кабинет тури"), q("active", "Фақат фаоллар (1)"))),
    "MembershipListView.post": Op("Аъзолик қўшиш", request=adm_s.MembershipAdminSerializer, response=adm_s.MembershipAdminSerializer, status=201),
    "MembershipDetailView.patch": Op("Аъзоликни ўзгартириш", request=adm_s.MembershipAdminSerializer, response=adm_s.MembershipAdminSerializer),
    "MembershipDetailView.delete": Op("Аъзоликни ўчириш", response=None, status=204),
    "CalendarAdminView.get": Op("Календарь кунлари", response=page_of(adm_s.CalendarDayAdminSerializer), params=(*ADMIN_Q, q("year", "Йил", int))),
    "CalendarAdminView.post": Op("Календарь кунини қўшиш", request=adm_s.CalendarDayAdminSerializer, response=adm_s.CalendarDayAdminSerializer, status=201),
    "CalendarImportView.post": Op("Календарни файлдан юклаш", request=ImportBody, multipart=True),
    "CalendarDetailView.patch": Op("Календарь кунини ўзгартириш", request=adm_s.CalendarDayAdminSerializer, response=adm_s.CalendarDayAdminSerializer),
    "CalendarDetailView.delete": Op("Календарь кунини ўчириш", response=None, status=204),
    "MahallaAdminView.get": Op("Маҳаллалар маълумотномаси", response=page_of(adm_s.MahallaAdminSerializer),
                               params=(*ADMIN_Q, q("region", "Вилоят ID"), q("district", "Туман ID"))),
    "MahallaAdminView.post": Op("Маҳалла қўшиш", request=adm_s.MahallaAdminSerializer, response=adm_s.MahallaAdminSerializer, status=201),
    "MahallaImportView.post": Op("Маҳаллаларни файлдан юклаш", request=ImportBody, multipart=True),
    "MahallaAdminDetailView.patch": Op("Маҳаллани ўзгартириш", request=adm_s.MahallaAdminSerializer, response=adm_s.MahallaAdminSerializer),
    "MahallaAdminDetailView.delete": Op("Маҳаллани ўчириш (фаолсизлантириш)", response=None, status=204),
    "UnionUnitAdminView.get": Op("Уюшма бўлинмалари", response=page_of(adm_s.UnionUnitAdminSerializer), params=ADMIN_Q),
    "UnionUnitAdminView.post": Op("Уюшма бўлинмаси қўшиш", request=adm_s.UnionUnitAdminSerializer, response=adm_s.UnionUnitAdminSerializer, status=201),
    "UnionUnitAdminDetailView.patch": Op("Уюшма бўлинмасини ўзгартириш", request=adm_s.UnionUnitAdminSerializer, response=adm_s.UnionUnitAdminSerializer),
    "UnionUnitAdminDetailView.delete": Op("Уюшма бўлинмасини ўчириш", response=None, status=204),
    "SupplierAdminView.get": Op("Етказиб берувчилар", response=page_of(adm_s.SupplierProfileAdminSerializer),
                                params=(*ADMIN_Q, q("supplier_type", "forest / dm"))),
    "SupplierAdminView.post": Op("Етказиб берувчи қўшиш", request=adm_s.SupplierProfileAdminSerializer, response=adm_s.SupplierProfileAdminSerializer, status=201),
    "SupplierAdminDetailView.patch": Op("Етказиб берувчини ўзгартириш", request=adm_s.SupplierProfileAdminSerializer,
                                        response=adm_s.SupplierProfileAdminSerializer),
    "SupplierAdminDetailView.delete": Op("Етказиб берувчини ўчириш", response=None, status=204),
    "AssignmentAdminView.get": Op("Маҳалла — хўжалик бириктиришлари", response=page_of(adm_s.AssignmentAdminSerializer), params=ADMIN_Q),
    "AssignmentAdminView.post": Op("Бириктириш қўшиш", request=adm_s.AssignmentAdminSerializer, response=adm_s.AssignmentAdminSerializer, status=201),
    "AssignmentImportView.post": Op("Бириктиришларни файлдан юклаш", request=ImportBody, multipart=True),
    "AssignmentAdminDetailView.patch": Op("Бириктиришни ўзгартириш", request=adm_s.AssignmentAdminSerializer, response=adm_s.AssignmentAdminSerializer),
    "AssignmentAdminDetailView.delete": Op("Бириктиришни ўчириш", response=None, status=204),
    "RouteAdminView.get": Op("Маҳалла — уюшма йўналишлари", response=page_of(adm_s.RouteAdminSerializer), params=ADMIN_Q),
    "RouteAdminView.post": Op("Йўналиш қўшиш", request=adm_s.RouteAdminSerializer, response=adm_s.RouteAdminSerializer, status=201),
    "RouteImportView.post": Op("Йўналишларни файлдан юклаш", request=ImportBody, multipart=True),
    "RouteAdminDetailView.patch": Op("Йўналишни ўзгартириш", request=adm_s.RouteAdminSerializer, response=adm_s.RouteAdminSerializer),
    "RouteAdminDetailView.delete": Op("Йўналишни ўчириш", response=None, status=204),
    "CatalogAdminView.get": Op("Каталог (маъмур)", response=page_of(adm_s.CatalogAdminSerializer), params=ADMIN_Q),
    "CatalogAdminView.post": Op("Каталог позицияси қўшиш", request=adm_s.CatalogAdminSerializer, response=adm_s.CatalogAdminSerializer, status=201),
    "CatalogAdminDetailView.patch": Op("Каталог позициясини ўзгартириш", request=adm_s.CatalogAdminSerializer, response=adm_s.CatalogAdminSerializer),
    "CatalogAdminDetailView.delete": Op("Каталог позициясини ўчириш (фаолсизлантириш)", response=None, status=204),
    "CapacityAdminView.get": Op("ДМ хизмат қуввати (маъмур)", params=(q("organization", "ДМ ташкилоти ID"), q("period", "YYYY-MM"))),
    "CapacityAdminView.put": Op("ДМ хизмат қувватини киритиш (маъмур)", request=CapacityBody),
    "SettingsAdminView.get": Op("Бизнес қоидалари ва сиёсатлар"),
    "SettingsAdminView.put": Op("Қоида қийматини ўзгартириш (effective_from билан)", request=SettingBody),
    "AuditAdminView.get": Op("Маъмурий ўзгаришлар журнали", response=page_of(name="PaginatedAuditList"),
                             params=(*ADMIN_Q, q("model", "Модель номи"))),
    # --- hisobotlar, statistika, xarita
    "RegistryView.get": Op("Кабинетлар реестри (қатор — буюртма позицияси)", response=page_of(name="PaginatedRegistryRowList"),
                           params=(*PAGE, *REGISTRY_FILTERS)),
    "RegistrySummaryView.get": Op("Реестр йиғиндиси", params=tuple(REGISTRY_FILTERS)),
    "ReportFiltersView.get": Op("Ҳисобот фильтрлари учун луғатлар"),
    "ExportCreateView.get": Op("Экспорт вазифалари рўйхати"),
    "ExportCreateView.post": Op("Экспорт яратиш (кичиги дарҳол, каттаси фонда)", request=ExportBody),
    "ExportDetailView.get": Op("Экспорт ҳолати ва юклаб олиш ҳаволаси"),
    "StatsCardsView.get": Op("Статистика карточкалари", params=tuple(REGISTRY_FILTERS)),
    "StatsSeedlingsView.get": Op("Кўчатлар бўйича фарқ", params=tuple(REGISTRY_FILTERS)),
    "StatsOrganizationsView.get": Op("Орқада қолаётган ташкилотлар", params=tuple(REGISTRY_FILTERS)),
    "MapPointsView.get": Op("Қабул қилинган буюртмалар харитаси",
                            params=(*REGISTRY_FILTERS, q("bbox", "Чегара: minLon,minLat,maxLon,maxLat"))),
    # --- hujjatlar, QR, xabarnomalar
    "DocumentVersionView.get": Op("Ҳужжат версияси (мазмун, хэш, имзолар)", response=ord_s.DocumentVersionSerializer),
    "DocumentVersionHtmlView.get": Op("Ҳужжатнинг босма кўриниши (HTML)", response=OpenApiTypes.STR),
    "DocumentVersionPdfView.get": Op("Ҳужжат PDF ҳаволаси"),
    "PublicVerifyView.get": Op("QR орқали ҳужжатни текшириш (очиқ, шахсий маълумотсиз)"),
    "NotificationListView.get": Op("Хабарномалар", response=page_of(ord_s.NotificationSerializer), params=(*PAGE, q("unread", "Фақат ўқилмаганлар (1)"))),
    "NotificationReadAllView.post": Op("Барчасини ўқилган деб белгилаш"),
    "NotificationReadView.post": Op("Хабарномани ўқилган деб белгилаш"),
}

# Bir xil nomli maydonlar (kind, status) turli tanlovlarga ega — komponent nomlari aniq bo'lsin
ENUM_NAME_OVERRIDES = {
    "CalendarDayKindEnum": "apps.yashil.models.CalendarDay.Kind",
    "DocumentVersionStatusEnum": "apps.yashil.models.DocumentVersion.Status",
    "ActStatusEnum": "apps.yashil.models.Act.Status",
    "PartyEnum": "apps.yashil.models.CancelRequest.Party",
    "RouteEnum": "apps.yashil.models.SupplierProfile.SupplierType",
}


def _patterns():
    return [path("api/v1/yashil/", include("apps.yashil.urls"))]


def build_schema(collect_problems=False):
    """Faqat modul URL'lari bo'yicha OpenAPI sxemasi (dict). collect_problems — (schema, xato/ogohlantirishlar)."""
    GENERATOR_STATS.reset()
    generator = SchemaGenerator(patterns=_patterns())
    with GENERATOR_STATS.silence(), patched_settings({"ENUM_NAME_OVERRIDES": ENUM_NAME_OVERRIDES}):
        schema = generator.get_schema(request=None, public=True)
    schema["info"] = {
        "title": "STAT-URMON — «Яшил маҳалла» API",
        "version": "1.0",
        "description": (
            "Барча ўзгартириш сўровларида Authorization (Bearer JWT) ва жорий version_no узатилади; "
            "ҳолат ўзгартирувчи POST амалларда Idempotency-Key мажбурий. Фаол кабинет X-Yashil-Cabinet "
            "сарлавҳаси билан танланади. Хато жавоби: error_code, field, message, request_id (TZ §21). "
            "Ваколат ва кўлам ҳар сўровда серверда текширилади."
        ),
    }
    problems = sorted([*GENERATOR_STATS._error_cache, *GENERATOR_STATS._warn_cache])
    GENERATOR_STATS.reset()
    return (schema, problems) if collect_problems else schema

"""Yashil mahalla ma'lumotnomalari — asosiy stat admin saytida (`/admin/`)."""
from django.contrib import admin

from apps.base.admin import admin_site
from apps.yashil.models import (
    Acceptance,
    CancelRequest,
    ReconcileIssue,
    YashilSetting,
    ExportJob,
    Act,
    ActAttachment,
    ActVersion,
    Document,
    ServiceAllocation,
    StockMovement,
    Warehouse,
    DocumentVersion,
    IdempotencyRecord,
    Order,
    OrderAttachment,
    OrderEvent,
    OrderLine,
    Signature,
    YashilNotification,
    CalendarDay,
    CatalogItem,
    Mahalla,
    MahallaUnionRoute,
    NormRule,
    ObjectType,
    Season,
    ServiceCapacity,
    SupplierAssignment,
    SupplierProfile,
    UnionUnit,
    YashilMembership,
)


def register(model):
    def decorator(admin_class):
        admin_site.register(model, admin_class)
        return admin_class

    return decorator


class SupplierAssignmentInline(admin.TabularInline):
    model = SupplierAssignment
    extra = 0
    raw_id_fields = ("organization",)
    fields = ("organization", "valid_from", "valid_to", "source_doc")


class UnionRouteInline(admin.TabularInline):
    model = MahallaUnionRoute
    extra = 0
    fields = ("union_unit", "valid_from", "valid_to", "source_doc")


@register(Mahalla)
class MahallaAdmin(admin.ModelAdmin):
    list_display = ("name", "source_code", "district", "region", "is_active", "valid_from", "valid_to")
    list_filter = ("is_active", "region")
    search_fields = ("name", "source_code", "address")
    raw_id_fields = ("district",)
    inlines = (SupplierAssignmentInline, UnionRouteInline)
    list_select_related = ("district", "region")


@register(UnionUnit)
class UnionUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "region", "district", "is_active")
    list_filter = ("level", "is_active", "region")
    search_fields = ("name", "stir")
    raw_id_fields = ("district", "parent")


@register(MahallaUnionRoute)
class MahallaUnionRouteAdmin(admin.ModelAdmin):
    list_display = ("mahalla", "union_unit", "valid_from", "valid_to")
    list_filter = ("union_unit",)
    search_fields = ("mahalla__name", "mahalla__source_code")
    raw_id_fields = ("mahalla",)


@register(SupplierProfile)
class SupplierProfileAdmin(admin.ModelAdmin):
    list_display = ("organization", "supplier_type", "parent", "is_active_supplier")
    list_filter = ("supplier_type", "is_active_supplier")
    search_fields = ("organization__name", "official_name", "stir")
    raw_id_fields = ("organization", "parent")
    filter_horizontal = ("service_regions", "service_districts")


@register(SupplierAssignment)
class SupplierAssignmentAdmin(admin.ModelAdmin):
    list_display = ("mahalla", "organization", "valid_from", "valid_to", "source_doc")
    list_filter = ("organization",)
    search_fields = ("mahalla__name", "mahalla__source_code", "organization__name")
    raw_id_fields = ("mahalla", "organization")


@register(YashilMembership)
class YashilMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "member_type", "cabinet_name", "can_prepare", "can_sign", "is_active", "valid_from", "valid_to")
    list_filter = ("member_type", "is_active", "can_sign")
    search_fields = ("user__email", "user__last_name", "user__first_name", "mahalla__name", "organization__name")
    raw_id_fields = ("user", "mahalla", "union_unit", "organization")
    fieldsets = (
        (None, {"fields": ("user", "member_type", "mahalla", "union_unit", "organization", "is_active", "valid_from", "valid_to")}),
        ("Vakolat", {"fields": ("can_prepare", "can_sign", "position_title", "phone",
                                 "authority_doc_number", "authority_doc_date", "authority_file")}),
        ("Kuzatuvchi ko'lami", {"fields": ("observer_scope",), "classes": ("collapse",)}),
    )


@register(CalendarDay)
class CalendarDayAdmin(admin.ModelAdmin):
    list_display = ("date", "kind", "note", "source_ref", "version")
    list_filter = ("kind",)
    date_hierarchy = "date"
    search_fields = ("note", "source_ref")


@register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("year", "kind", "date_from", "date_to", "is_active")
    list_filter = ("year", "kind")


@register(ObjectType)
class ObjectTypeAdmin(admin.ModelAdmin):
    list_display = ("order", "code", "name_cyr", "name_lat", "requires_note", "is_active")
    list_editable = ("requires_note", "is_active")
    ordering = ("order",)


@register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name_cyr", "supplier_type", "item_type", "category", "unit", "precision", "is_active", "version")
    list_filter = ("supplier_type", "item_type", "category", "is_active")
    search_fields = ("code", "name_cyr", "name_lat")
    readonly_fields = ("precision",)


@register(NormRule)
class NormRuleAdmin(admin.ModelAdmin):
    list_display = ("code", "version", "applies_to_category", "applies_to_item", "effective_from", "effective_to", "approved_ref")
    list_filter = ("applies_to_category",)
    search_fields = ("code", "description")
    raw_id_fields = ("applies_to_item",)


@register(ServiceCapacity)
class ServiceCapacityAdmin(admin.ModelAdmin):
    list_display = ("organization", "catalog_item", "period", "capacity")
    list_filter = ("period",)
    raw_id_fields = ("organization", "catalog_item")


# ----------------------------------------------------------------------------- 2-bosqich: buyurtmalar (faqat ko'rish)
class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    can_delete = False
    readonly_fields = ("catalog_item", "qty", "attrs_note", "position")

    def has_add_permission(self, request, obj=None):
        return False


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    can_delete = False
    readonly_fields = ("action", "from_state", "to_state", "actor_label", "comment", "reason_code", "created_at")
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


@register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Buyurtmalar adminda faqat ko'riladi — o'zgartirish faqat modul oqimi orqali (TZ §17.2)."""

    list_display = ("display_number", "title", "mahalla", "supplier_org", "route", "state", "version_no", "last_submitted_at", "delivery_due")
    list_filter = ("state", "route", "mahalla__region")
    search_fields = ("number", "title", "mahalla__name", "supplier_org__name")
    readonly_fields = [f.name for f in Order._meta.fields]
    inlines = (OrderLineInline, OrderEventInline)
    list_select_related = ("mahalla", "supplier_org")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@register(OrderAttachment)
class OrderAttachmentAdmin(admin.ModelAdmin):
    list_display = ("order", "original_name", "kind", "size", "version_no", "created_at")
    readonly_fields = ("order", "file", "original_name", "size", "kind", "version_no", "uploaded_by")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # imzolangan versiya fayllari tarixda qoladi (TZ §17.2); qoralama ilovasi API orqali o'chiriladi
        return False


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    can_delete = False
    readonly_fields = ("version_no", "template_version", "status", "content_hash", "qr_token", "created_at")
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


@register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("number", "kind", "order", "current_version", "created_at")
    list_filter = ("kind",)
    search_fields = ("number", "order__number")
    readonly_fields = ("kind", "order", "number", "current_version")
    inlines = (DocumentVersionInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display = ("document_version", "role", "signer_cn", "signer_tin", "mode", "is_valid", "signed_at")
    list_filter = ("role", "mode", "is_valid")
    search_fields = ("signer_cn", "signer_tin", "document_version__document__number")
    readonly_fields = [f.name for f in Signature._meta.fields]
    exclude = ("pkcs7",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@register(YashilNotification)
class YashilNotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient_user", "kind", "title", "order", "read_at", "created_at")
    list_filter = ("kind",)
    search_fields = ("recipient_user__email", "title", "order__number")
    readonly_fields = ("recipient_user", "membership", "kind", "title", "body", "order", "read_at")

    def has_add_permission(self, request):
        return False


@register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "path", "key", "status_code", "created_at")
    readonly_fields = ("user", "key", "path", "request_hash", "status_code", "response", "created_at")
    search_fields = ("key", "path", "user__email")

    def has_add_permission(self, request):
        return False


# ----------------------------------------------------------------------------- ombor (3-bosqich)
@register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("organization", "name", "is_default", "created_at")
    search_fields = ("organization__name", "name")
    raw_id_fields = ("organization",)


@register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """Harakatlar o'chirilmaydi va tahrirlanmaydi — tuzatish faqat teskari operatsiya bilan (TZ §9.3)."""

    list_display = ("created_at", "warehouse", "catalog_item", "kind", "qty", "status", "doc_number", "doc_date")
    list_filter = ("kind", "status", "warehouse__organization")
    search_fields = ("doc_number", "catalog_item__code", "warehouse__organization__name", "note")
    readonly_fields = [f.name for f in StockMovement._meta.fields]
    list_select_related = ("warehouse__organization", "catalog_item")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@register(Acceptance)
class AcceptanceAdmin(admin.ModelAdmin):
    list_display = ("order", "warehouse", "accepted_on", "delivery_due", "executor_name", "accepted_by")
    search_fields = ("order__number", "executor_name")
    readonly_fields = [f.name for f in Acceptance._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@register(ServiceAllocation)
class ServiceAllocationAdmin(admin.ModelAdmin):
    list_display = ("organization", "catalog_item", "period", "order_line", "qty")
    list_filter = ("period",)
    readonly_fields = [f.name for f in ServiceAllocation._meta.fields]

    def has_add_permission(self, request):
        return False


# ----------------------------------------------------------------------------- dalolatnoma (3-bosqich)
class ActVersionInline(admin.TabularInline):
    model = ActVersion
    extra = 0
    can_delete = False
    readonly_fields = ("version_no", "delivery_date", "responsible", "document_version", "submitted_at", "superseded_at", "created_at")
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


@register(Act)
class ActAdmin(admin.ModelAdmin):
    list_display = ("number", "order", "status", "version_no", "is_partial", "approved_at", "returned_at", "created_at")
    list_filter = ("status", "is_partial")
    search_fields = ("number", "order__number", "order__mahalla__name")
    readonly_fields = [f.name for f in Act._meta.fields]
    inlines = (ActVersionInline,)
    list_select_related = ("order",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@register(ActAttachment)
class ActAttachmentAdmin(admin.ModelAdmin):
    list_display = ("act", "original_name", "kind", "size", "version_no", "created_at")
    readonly_fields = ("act", "file", "original_name", "size", "kind", "version_no", "uploaded_by")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # imzolangan versiya fayllari tarixda qoladi (TZ §17.2); qoralama ilovasi API orqali o'chiriladi
        return False


# ----------------------------------------------------------------------------- bekor qilish va solishtirish (3-bosqich)
@register(CancelRequest)
class CancelRequestAdmin(admin.ModelAdmin):
    list_display = ("order", "requested_by_party", "is_full", "status", "agreed_by", "approved_by", "created_at")
    list_filter = ("status", "requested_by_party", "is_full")
    search_fields = ("order__number", "reason")
    readonly_fields = [f.name for f in CancelRequest._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@register(ReconcileIssue)
class ReconcileIssueAdmin(admin.ModelAdmin):
    list_display = ("found_at", "kind", "key", "order", "warehouse", "resolved_at")
    list_filter = ("kind",)
    search_fields = ("key", "order__number", "warehouse__organization__name")
    readonly_fields = ("kind", "key", "order", "warehouse", "details", "found_at")

    def has_add_permission(self, request):
        return False


@register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = ("created_at", "requested_by", "membership", "kind", "format", "status", "row_count", "finished_at")
    list_filter = ("kind", "format", "status")
    search_fields = ("requested_by__email", "membership__user__email")
    readonly_fields = ("requested_by", "membership", "kind", "format", "filters", "status", "row_count", "file", "error", "started_at", "finished_at")

    def has_add_permission(self, request):
        return False


@register(YashilSetting)
class YashilSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "version", "value", "effective_from", "changed_by", "created_at")
    list_filter = ("key",)
    readonly_fields = ("key", "value", "effective_from", "version", "changed_by", "note")

    def has_add_permission(self, request):
        return False  # yangi versiya faqat modul sozlamalari ekrani / rules.set_value orqali

    def has_delete_permission(self, request, obj=None):
        return False

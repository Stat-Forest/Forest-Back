"""
Modul administratori serializer'lari (plans §11.1-9). Saqlash `ValidatedModel.full_clean` orqali —
Django ValidationError 422 ga aylanadi (`AdminWriteMixin`). Har yozuvga `_history_user`
qo'yiladi — `apps.logs` jurnali shu foydalanuvchi nomidan yoziladi (TZ 17.2).
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.yashil.api import YashilError
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

ISO = {"format": "iso-8601", "input_formats": ["iso-8601", "%d.%m.%Y"]}


def model_error(exc: DjangoValidationError) -> YashilError:
    if hasattr(exc, "message_dict"):
        field, messages = next(iter(exc.message_dict.items()))
        return YashilError("; ".join(messages), error_code="validation", field=None if field == "__all__" else field)
    return YashilError("; ".join(exc.messages), error_code="validation")


class AdminWriteMixin:
    """create/update: model obyektini qo'lda yig'adi, `_history_user` qo'yadi, M2M'ni keyin o'rnatadi."""

    read_only_on_update: tuple = ()

    def _user(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def _persist(self, instance, validated_data):
        m2m = {}
        for name, value in list(validated_data.items()):
            field = instance._meta.get_field(name)
            if field.many_to_many:
                m2m[name] = validated_data.pop(name)
            else:
                setattr(instance, name, value)
        instance._history_user = self._user()
        try:
            with transaction.atomic():
                instance.save()
                for name, value in m2m.items():
                    getattr(instance, name).set(value)
        except DjangoValidationError as exc:
            raise model_error(exc)
        except IntegrityError:
            raise YashilError("Бундай ёзув аллақачон мавжуд", error_code="duplicate")
        return instance

    def create(self, validated_data):
        return self._persist(self.Meta.model(), validated_data)

    def update(self, instance, validated_data):
        for name in self.read_only_on_update:
            validated_data.pop(name, None)
        return self._persist(instance, validated_data)


def _ref(obj, *fields):
    if obj is None:
        return None
    return {f: (str(getattr(obj, f)) if f == "id" else getattr(obj, f)) for f in fields}


class MembershipAdminSerializer(AdminWriteMixin, serializers.ModelSerializer):
    read_only_on_update = ("user", "member_type", "mahalla", "union_unit", "organization")
    cabinet_name = serializers.CharField(read_only=True)
    valid_from = serializers.DateField(required=False, **ISO)
    valid_to = serializers.DateField(required=False, allow_null=True, **ISO)
    authority_doc_date = serializers.DateField(required=False, allow_null=True, **ISO)

    class Meta:
        model = YashilMembership
        fields = (
            "id", "user", "member_type", "mahalla", "union_unit", "organization", "can_prepare", "can_sign",
            "position_title", "phone", "authority_doc_number", "authority_doc_date", "authority_file",
            "observer_scope", "valid_from", "valid_to", "is_active", "cabinet_name",
        )
        extra_kwargs = {"authority_file": {"required": False, "allow_null": True}}

    def to_representation(self, obj):
        data = super().to_representation(obj)
        u = obj.user
        data["user_info"] = {"id": str(u.id), "email": u.email, "full_name": f"{u.last_name} {u.first_name}".strip(), "role": u.role}
        data["authority_file"] = bool(obj.authority_file)
        data["is_current"] = obj.is_active and obj.is_current()
        return data


class MahallaAdminSerializer(AdminWriteMixin, serializers.ModelSerializer):
    valid_from = serializers.DateField(required=False, **ISO)
    valid_to = serializers.DateField(required=False, allow_null=True, **ISO)

    class Meta:
        model = Mahalla
        fields = ("id", "source_code", "name", "district", "address", "is_active", "valid_from", "valid_to")

    def validate(self, attrs):
        district = attrs.get("district")
        if district is not None:
            attrs["region"] = district.region
        return attrs

    def _persist(self, instance, validated_data):
        region = validated_data.pop("region", None)
        if region is not None:
            instance.region = region
        return super()._persist(instance, validated_data)

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data["region"] = _ref(obj.region, "id", "code", "name")
        data["district"] = _ref(obj.district, "id", "code", "name")
        return data


class UnionUnitAdminSerializer(AdminWriteMixin, serializers.ModelSerializer):
    class Meta:
        model = UnionUnit
        fields = ("id", "name", "level", "region", "district", "parent", "stir", "is_active")
        extra_kwargs = {"region": {"required": False}, "district": {"required": False}}

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data["region_name"] = obj.region.name if obj.region_id else ""
        data["district_name"] = obj.district.name if obj.district_id else ""
        data["mahallas"] = obj.mahalla_routes.filter(valid_to__isnull=True).count()
        return data


class SupplierProfileAdminSerializer(AdminWriteMixin, serializers.ModelSerializer):
    read_only_on_update = ("organization", "supplier_type")

    class Meta:
        model = SupplierProfile
        fields = ("id", "organization", "supplier_type", "parent", "official_name", "stir", "is_active_supplier",
                  "service_regions", "service_districts")
        extra_kwargs = {"service_regions": {"required": False}, "service_districts": {"required": False}}

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data["organization_name"] = obj.organization.name
        data["members"] = YashilMembership.objects.filter(organization_id=obj.organization_id, is_active=True).count()
        return data


class AssignmentAdminSerializer(AdminWriteMixin, serializers.ModelSerializer):
    read_only_on_update = ("mahalla", "organization", "valid_from")
    valid_from = serializers.DateField(**ISO)
    valid_to = serializers.DateField(required=False, allow_null=True, **ISO)

    class Meta:
        model = SupplierAssignment
        fields = ("id", "mahalla", "organization", "valid_from", "valid_to", "source_doc")

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data["mahalla_name"] = obj.mahalla.name
        data["organization_name"] = obj.organization.name
        data["is_current"] = obj.is_current()
        return data


class RouteAdminSerializer(AdminWriteMixin, serializers.ModelSerializer):
    read_only_on_update = ("mahalla", "union_unit", "valid_from")
    valid_from = serializers.DateField(**ISO)
    valid_to = serializers.DateField(required=False, allow_null=True, **ISO)

    class Meta:
        model = MahallaUnionRoute
        fields = ("id", "mahalla", "union_unit", "valid_from", "valid_to", "source_doc")

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data["mahalla_name"] = obj.mahalla.name
        data["union_unit_name"] = obj.union_unit.name
        data["is_current"] = obj.is_current()
        return data


class CatalogAdminSerializer(AdminWriteMixin, serializers.ModelSerializer):
    read_only_on_update = ("code", "supplier_type", "item_type", "unit")
    effective_from = serializers.DateField(required=False, allow_null=True, **ISO)

    class Meta:
        model = CatalogItem
        fields = ("id", "code", "name_cyr", "name_lat", "supplier_type", "item_type", "category", "unit", "precision",
                  "attributes", "is_active", "effective_from", "version", "order")
        read_only_fields = ("precision", "version")

    def update(self, instance, validated_data):
        # Nomi/atributi o'zgarsa versiya oshadi (imzolangan hujjatlarda eski snapshot qoladi)
        if any(k in validated_data and validated_data[k] != getattr(instance, k) for k in ("name_cyr", "name_lat", "attributes", "category")):
            validated_data["version"] = instance.version + 1
        return super().update(instance, validated_data)


class CalendarDayAdminSerializer(AdminWriteMixin, serializers.ModelSerializer):
    date = serializers.DateField(**ISO)

    class Meta:
        model = CalendarDay
        fields = ("id", "date", "kind", "note", "source_ref", "version")
        read_only_fields = ("version",)

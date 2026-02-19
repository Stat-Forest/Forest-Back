from rest_framework import serializers
from django.utils import timezone

from apps.general.models.land_document import LandDocument


class LandDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for LandDocument API responses.
    Provides safe formatted output for frontend usage.
    """

    document_type_display = serializers.CharField(
        source='get_document_type_display',
        read_only=True
    )

    file_url = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()

    class Meta:
        model = LandDocument
        fields = [
            "id",
            "name",
            "date",
            "document_type",
            "document_type_display",
            "organization",
            "organization_name",
            "comment",
            "file",
            "file_url",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "document_type_display",
            "file_url",
            "organization_name",
        ]

    # ------------------------------------------------------
    # Returns absolute file URL (safe frontend usage)
    # ------------------------------------------------------
    def get_file_url(self, obj):
        request = self.context.get("request")

        if obj.file and hasattr(obj.file, "url"):
            return (
                request.build_absolute_uri(obj.file.url)
                if request else obj.file.url
            )
        return None

    # ------------------------------------------------------
    # Avoids extra DB query thanks to select_related
    # ------------------------------------------------------
    def get_organization_name(self, obj):
        return getattr(obj.organization, "name_uz", None)

    # ------------------------------------------------------
    # Validation layer (API security)
    # ------------------------------------------------------
    def validate_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError(
                "The date cannot be in the future."
            )
        return value

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Document name cannot be empty."
            )
        return value

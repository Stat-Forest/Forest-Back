from rest_framework import serializers
from apps.general.models.land_document import LandDocument


class LandDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = LandDocument
        fields = [
            "id",
            "name",
            "date",
            "document_type",
            "document_type_display",
            "organization",
            "comment",
            "file",
            "file_url",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "document_type_display", "file_url"]

    def get_file_url(self, obj):
        """Return full file URL if file exists"""
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return None

    def validate_date(self, value):
        from django.utils import timezone
        if value > timezone.now().date():
            raise serializers.ValidationError("The date cannot be in the future.")
        return value

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Document name cannot be empty.")
        return value

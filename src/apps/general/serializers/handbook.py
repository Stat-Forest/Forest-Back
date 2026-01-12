from rest_framework import serializers
from apps.general.models.handbook import Handbook

class HandBookSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Handbook
        fields = [
            "id",
            "name",
            "file",
            "file_url",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "file_url"]

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return None


    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Document name cannot be empty.")
        return value

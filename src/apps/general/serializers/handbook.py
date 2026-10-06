from rest_framework import serializers
from apps.general.models.handbook import Handbook
from apps.general.protected_media import signed_file_url


class HandBookSerializer(serializers.ModelSerializer):
    """
    Serializer for handbook documents.

    Security:
    - Prevents empty document names
    - Returns absolute file URL safely
    """

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
        extra_kwargs = {"file": {"write_only": True}}  # faqat imzolangan file_url chiqadi

    def get_file_url(self, obj):
        """
        Returns absolute file URL if request context exists.
        Prevents exposing invalid file paths.
        """
        # Imzolangan, muddatli havola — /media/handbooks/ login'siz ochilmaydi
        return signed_file_url(self.context.get('request'), obj.file)

    def validate_name(self, value):
        """
        Prevent empty or whitespace-only names.
        """
        if not value.strip():
            raise serializers.ValidationError("Document name cannot be empty.")
        return value

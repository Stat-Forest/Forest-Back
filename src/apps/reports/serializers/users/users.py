from rest_framework import serializers
from apps.users.models import CustomUser

class UserListSerializer(serializers.ModelSerializer):
    information = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()

    def get_information(self, obj):
        personal_info = getattr(obj, 'personal_info', None)
        return personal_info.information if personal_info else ""

    def get_role_display(self, obj):
        return obj.get_role_display()

    def get_organization_name(self, obj):
        lang = self.context.get("lang", "uz")  # default = uz
        if not obj.organization:
            return ""
        # Agar modelda name_ru va name_uz maydonlari mavjud bo‘lsa
        return getattr(obj.organization, f"name_{lang}", obj.organization.name or "")

    class Meta:
        model = CustomUser
        fields = (
            'user_number',
            'first_name',
            'last_name',
            'organization',
            'statement',
            'organization_name',
            'nationality',
            'information',
            'phone_number',
            'role',
            'role_display',
        )

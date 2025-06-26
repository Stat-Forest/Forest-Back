from rest_framework import serializers
from apps.users.models import CustomUser

class UserListSerializer(serializers.ModelSerializer):
    information = serializers.SerializerMethodField()
    organization__name = serializers.CharField(source='organization.name', read_only=True)

    def get_information(self, obj):
        personal_info = obj.personal_info if hasattr(obj, 'personal_info') else None
        if personal_info:
            return personal_info.information
        return ""

    class Meta:
        model = CustomUser
        fields = (
            'user_number', 'first_name', 'last_name',
            'organization','organization__name',
            'nationality', 'information', 'role'
        )


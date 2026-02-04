from rest_framework import serializers
from apps.users.models import CustomUser


class UserListSerializer(serializers.ModelSerializer):
    information = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    statement_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    region_display = serializers.SerializerMethodField()
    region_user_orgs = serializers.SerializerMethodField()

    def get_information(self, obj):
        personal_info = getattr(obj, 'personal_info', None)
        return personal_info.information if personal_info else ""

    def get_role(self, obj):
        return obj.role

    def get_role_display(self, obj):
        return obj.get_role_display()

    def get_region_display(self, obj):
        return obj.get_region_display() if obj.region else ""

    def get_organization_name(self, obj):
        lang = self.context.get("lang", "uz")
        if not obj.organization:
            return ""
        return getattr(obj.organization, f"name_{lang}", obj.organization.name or "")

    def get_statement_name(self, obj):
        lang = self.context.get("lang", "uz")
        if not obj.statement:
            return ""
        return getattr(obj.statement, f"name_{lang}", obj.statement.name or "")

    def get_region_user_orgs(self, obj):
        """
        ['Org A', 'Org B', 'Org C'] ko‘rinishida qaytaradi
        """
        lang = self.context.get("lang", "uz")
        orgs = obj.region_user_orgs.all()

        return [
            getattr(org, f"name_{lang}", org.name)
            for org in orgs
        ]

    class Meta:
        model = CustomUser
        fields = (
            'user_number',
            'first_name',
            'last_name',
            'organization',
            'statement',
            'organization_name',
            'statement_name',
            'nationality',
            'information',
            'phone_number',
            'role',
            'role_display',
            'region',
            'region_display',
            'region_user_orgs',
        )

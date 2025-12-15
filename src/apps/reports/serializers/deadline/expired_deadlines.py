from rest_framework import serializers
from apps.general.models import Organization
from apps.reports.models import Deadline, Statement
from apps.utils.translation import get_lang_code, get_translated_field


class OrganizationExpiredSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ('id', 'name')

    def get_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj, "name", lang)


class StatementExpiredSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()
    period = serializers.SerializerMethodField()

    class Meta:
        model = Statement
        fields = ("id", "name", "period", "parent_name")

    def get_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj, "name", lang)

    def get_parent_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj.parent, "name", lang) if obj.parent else None

    def get_period(self, obj):
        return obj.get_period_display()


class DeadlineExpiredSerializer(serializers.ModelSerializer):
    organizations = serializers.SerializerMethodField()
    statement = StatementExpiredSerializer(read_only=True)

    class Meta:
        model = Deadline
        fields = ("id", "submit_at", "deadline_at", "statement", "organizations")

    def get_organizations(self, obj):
        organizations = getattr(
            obj,
            "_filtered_organizations",
            obj.organizations.all()
        )
        return OrganizationExpiredSerializer(
            organizations,
            many=True,
            context=self.context
        ).data


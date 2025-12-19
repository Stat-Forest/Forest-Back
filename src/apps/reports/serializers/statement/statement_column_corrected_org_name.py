from rest_framework import serializers
from apps.reports.models import StatementColumn
from apps.utils.translation import get_lang_code, get_translated_field


SPECIAL_STATEMENT_NAMES = [
    "Urug xarakati Reja",
    "Urug harakati",
    "Ko`chat va Nihol",
    "Kochatxona va Niholxona Jami",
    "Shakl 8-O'x",
    "Shakl 9-O'x",
    "Shakl 10-O'x",
    "Shakl 11-O'x",
]


class CorrectedStatementColumnTreeSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    parent = serializers.PrimaryKeyRelatedField(read_only=True)
    statement = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = StatementColumn
        fields = (
            'id',
            'statement',
            'title',
            'ordering',
            'parent',
            'status_plan',
            'is_organization',
            'children',
        )

    def get_title(self, obj):
        lang = get_lang_code(self.context)

        # ✅ ANIQ VA XAVFSIZ SHART
        if (
            obj.is_organization
            and getattr(obj, "statement", None)
            and obj.statement.name in SPECIAL_STATEMENT_NAMES
        ):
            return "O'simliklar nomi"

        # ✅ ODDIY HOLAT (tarjima bilan)
        return get_translated_field(obj, "title", lang)

    def get_children(self, obj):
        children = getattr(obj, "children_list", [])
        return CorrectedStatementColumnTreeSerializer(
            children,
            many=True,
            context=self.context
        ).data

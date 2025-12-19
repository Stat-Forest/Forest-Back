from rest_framework import serializers
from apps.reports.models import StatementColumn
from apps.utils.translation import get_lang_code, get_translated_field

# 🔹 Maxsus statement column id'lari
SPECIAL_STATEMENT_IDS = [
    "61ae3c83-1f9c-4ec8-bb06-0c2fc35d0a00",  # "Ko‘chat va Nihol"
    "4c4e3393-4b33-4c46-af32-fbb5fda6067b",  # "Urug' harakati"
    "0efead0e-25c3-44ab-8200-c2a7628dca8f",  # "Urug' xarakati Reja"
    "3a94c662-37b1-43ca-a717-09b4004cc226",  # "Shakl 9-O‘X"
    "51835775-5c9d-4f6e-96c9-4f7ff081f228",  # "Shakl 10-O‘X"
    "0e0cb4de-e2ae-475c-a3a6-a2b9bc37efb8",  # "Shakl 11-O‘X"
    "ddf6419b-5729-44ba-8f85-6092691f5138",  # "Shakl 8-O'X"
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

        # 🔹 ID bo'yicha maxsus logika
        if obj.is_organization and str(obj.id) in SPECIAL_STATEMENT_IDS:
            return "O'simliklar nomi"

        # 🔹 Oddiy holat (tarjima bilan)
        return get_translated_field(obj, "title", lang)

    def get_children(self, obj):
        children = getattr(obj, "children_list", [])
        return CorrectedStatementColumnTreeSerializer(
            children,
            many=True,
            context=self.context
        ).data

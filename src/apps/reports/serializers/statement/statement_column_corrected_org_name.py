from rest_framework import serializers
from apps.reports.models import StatementColumn
from apps.utils.translation import get_lang_code, get_translated_field


class CorrectedStatementColumnTreeSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()

    children = serializers.SerializerMethodField()
    parent = serializers.PrimaryKeyRelatedField(read_only=True)
    statement = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = StatementColumn
        fields = [
            'id', 'statement', 'title',
            'ordering', 'parent', 'status_plan',
            'is_organization','children'
        ]

    def get_title(self, obj):
        lang = get_lang_code(self.context)
        title = get_translated_field(obj, "title", lang)

        # 🔢 Statement nomlari bo‘yicha o‘zgartirish
        STATEMENT_TITLE_MAP = {
            # Asosiy o‘simlik nomi kerak bo‘ladigan statementlar
            "Urug' xarakati Reja": "O‘simlik nomi",
            "Urug' harakati": "O‘simlik nomi",
            "Ko‘chat va Nihol": "O‘simlik nomi",
            "Ko'chatxona va Niholxona Jami": "O‘simlik nomi",
            "Shakl 8-O'X": "Daraxt (ko‘chat, nihol) turi",
            "Shakl 9-O'X": "Yillar",
            "Shakl 10-O'X": "Yillar",
            "Shakl 11-O'X": "O‘rmon fondi yer toifasi va tadbirlar nomi",
        }

        # 🔍 Statement nomini aniqlaymiz
        statement_name = obj.statement.name_uz.strip() if obj.statement else ""

        # 🎯 Agar `is_organization` bo‘lsa va mos title bo‘lsa — o‘zgartiramiz
        if (
                obj.is_organization
                and statement_name in STATEMENT_TITLE_MAP
                and title.strip().lower() in {"tashkilot nomi", "название организации"}
        ):
            fallback = STATEMENT_TITLE_MAP[statement_name]
            return {
                "uz": fallback,
                "ru": {
                    "O‘simlik nomi": "Название растения",
                    "Daraxt (ko‘chat, nihol) turi": "Вид дерева (саженец, росток)",
                    "Yillar": "Годы",
                    "O‘rmon fondi yer toifasi va tadbirlar nomi": "Категория земель и мероприятий",
                }.get(fallback, fallback)
            }.get(lang, fallback)

        return title

    def get_children(self, obj):
        if hasattr(obj, 'children_list'):
            return CorrectedStatementColumnTreeSerializer(
                obj.children_list,
                many=True,
                context=self.context
            ).data
        return []
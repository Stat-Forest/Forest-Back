from rest_framework import serializers
from apps.reports.models import Report
from apps.utils.translation import get_lang_code, get_translated_field


class ReportListSerializer(serializers.ModelSerializer):
    period = serializers.CharField(source='statement.period')
    organization_name = serializers.SerializerMethodField()
    report_items = serializers.SerializerMethodField()
    statement_name = serializers.SerializerMethodField()
    sent_by_full_name = serializers.SerializerMethodField()
    sent_by_org_name = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            'id', 'organization', 'organization_name',
            'statement', 'statement_name',
            'deadline', 'period', 'status',
            'created_at', 'cancel_reason',
            'cancelled_at', 'sent_at', 'accepted_at',
            'report_items',
            'sent_by_full_name', 'sent_by_org_name', 'sent_by_role',
        )

    def get_organization_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj.organization, "name", lang)

    def get_statement_name(self, obj):
        lang = get_lang_code(self.context)
        return get_translated_field(obj.statement, "name", lang)

    def get_sent_by_full_name(self, obj):
        if obj.sent_by:
            return obj.sent_by.full_name
        return None

    def get_sent_by_org_name(self, obj):
        lang = get_lang_code(self.context)
        if obj.sent_by_org:
            return get_translated_field(obj.sent_by_org, "name", lang)
        return None

    def get_report_items(self, obj):
        items = (
            obj.report_items
            .select_related("statement_column")
            .prefetch_related("inners")
            .all()
        )
        lang = get_lang_code(self.context)

        # 1️⃣ Tashkilotlarni aniqlash
        org_map = {}  # {org_id: org_name}
        column_map = {}  # {org_id: [columns]}

        for item in items:
            column = item.statement_column

            # Agar bu organization ustuni bo‘lsa → org_id ni olamiz
            if column.is_organization:
                org_id = item.value  # bu yerda org_id saqlanadi
                from apps.general.models import Organization
                org = Organization.objects.filter(id=org_id).first()
                org_name = get_translated_field(org, "name", lang) if org else "Noma'lum tashkilot"

                # agar yangi org bo‘lsa, mapga qo‘shamiz
                if org_id not in org_map:
                    org_map[org_id] = org_name
                    column_map[org_id] = []  # shu orgga tegishli ustunlar ro‘yxati
                continue

        # 2️⃣ Endi boshqa columnlarni organizationga bog‘lash
        current_org = None
        for item in items:
            column = item.statement_column

            # bu org ustuni emas → uni tegishli orgga qo‘shamiz
            if not column.is_organization:
                # organization ni oxirgi qo‘shilganidan aniqlash
                if current_org is None:
                    # agar hech qaysi org bo‘lmasa, default None bilan saqlaymiz
                    continue

                col_data = {
                    "statement_column_id": str(column.id),
                    "statement_column_name": get_translated_field(column, "title", lang),
                    "organization_id": current_org,
                    "inners": [
                        {"id": str(inner.id), "value": inner.value}
                        for inner in item.inners.all()
                    ]
                }
                column_map[current_org].append(col_data)
            else:
                # bu yangi organization boshlanganini bildiradi
                current_org = item.value  # org_id

        # 3️⃣ Yig‘ilgan natijani chiqaramiz
        result = []
        for org_id, columns in column_map.items():
            result.append({
                "organization_id": org_id,
                "organization_name": org_map.get(org_id, "Noma'lum tashkilot"),
                "columns": columns
            })

        return result

{
  "deadline": "a55dad33-40de-4f6b-be52-facdfc899a16",
  "report_items": [
    {
      "statement_column": "6e427073-be17-4be1-94dd-4ca0abd6f508",
      "value": "464bb31b-62a2-49cd-a077-7d2013b8b0a7"
    },
    {
      "statement_column": "95a4f08d-9263-4f45-a0e6-4b1da1fb8fa0",
      "inners": [
        {"value": "10"},
        {"value": "20"},
        {"value": "30"},
        {"value": "30"},
        {"value": "30"},
        {"value": "30"},
        {"value": "30"}
      ]
    },
    {
      "statement_column": "98c71be2-567f-418f-8a2a-6ef738700256",
      "inners": [
        {"value": "5"},
        {"value": "15"},
        {"value": "25"},
        {"value": "25"},
        {"value": "25"},
        {"value": "25"},
        {"value": "25"}
      ]
    },

    {
      "statement_column": "02ebf235-fb07-429d-9f56-b0697d1dfd80",
      "value": "464bb31b-62a2-49cd-a077-7d2013b8b0a7"
    },
    {
      "statement_column": "99f4138b-e606-44f9-a3db-b8006e4bc946",
      "inners": [
        {"value": "11"},
        {"value": "22"},
        {"value": "33"}
      ]
    },
    {
      "statement_column": "b9d9255e-ece4-4223-b0e7-2985c7004d97",
      "inners": [
        {"value": "100"},
        {"value": "200"},
        {"value": "300"}
      ]
    },
    {
      "statement_column": "1f53497a-fd4d-4598-b649-683a8a86a616",
      "value": "464bb31b-62a2-49cd-a077-7d2013b8b0a7"
    },
    {
      "statement_column": "b599e076-7e43-4629-bff6-ebd4f9f58e34",
      "inners": [
        {"value": "100"},
        {"value": "200"},
        {"value": "300"}
      ]
    }
  ]
}

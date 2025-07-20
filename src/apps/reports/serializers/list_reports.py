from rest_framework import serializers
from apps.reports.models import Report
from apps.utils.services.general_values import build_columns_with_jami
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
            normal_columns, general_columns = build_columns_with_jami(columns)
            result.append({
                "organization_id": org_id,
                "organization_name": org_map.get(org_id, "Noma'lum tashkilot"),
                "columns": normal_columns,
                "general": general_columns
            })

        return result

# XODIM HISOBI ==========================================
{
  "deadline": "e6e475b0-313c-4cf7-8549-651f6ac8a5d9",
  "report_items": [
    {
      "statement_column": "ff250268-05e1-4b4a-9391-0bbf3affa2f7",
      "inners": [
        { "value": "b8e8f89c-405c-4fdb-9f72-19f765da3f04" }
      ]
    },
    {
      "statement_column": "0c2e4fc0-3190-4251-a695-122855e93cab",
      "inners": [
        { "value": "10" },
        { "value": "20" },
        { "value": "30" },
        { "value": "30" },
        { "value": "30" },
        { "value": "30" },
        { "value": "30" }
      ]
    },
    {
      "statement_column": "b7c8a6a9-ebe0-464d-b1b1-896d7c5b3800",
      "inners": [
        { "value": "5" },
        { "value": "15" },
        { "value": "25" },
        { "value": "25" },
        { "value": "25" },
        { "value": "25" },
        { "value": "25" }
      ]
    },
    {
      "statement_column": "94f83fd3-675c-4e22-ac33-70aef3b99515",
      "inners": [
        { "value": "b8e8f89c-405c-4fdb-9f72-19f765da3f04" }
      ]
    },
    {
      "statement_column": "fc1f5be5-0cfd-490d-bb3f-831d7f24f520",
      "inners": [
        { "value": "11" },
        { "value": "22" },
        { "value": "33" }
      ]
    },
    {
      "statement_column": "4b1675b6-0324-4853-b9fd-eb16ad641967",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "05174a66-34fa-4332-a579-4b988b98f258",
      "inners": [
        { "value": "b8e8f89c-405c-4fdb-9f72-19f765da3f04" }
      ]
    },
    {
      "statement_column": "3105c87d-9725-40d5-bef5-df5cd133a7ba",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    }
  ]
}


# DAROMAD =============================================

{
  "deadline": "67b18205-7f60-4492-a9d5-99fa8c5a3c58",
  "report_items": [
    {
      "statement_column": "332bf656-956b-4da6-8c90-2bd283ed33ae",
      "inners": [
        { "value": "fa6b4ffc-cc9f-4a59-bd8f-190241e06392" }
      ]
    },
    {
      "statement_column": "369fd215-64f0-423e-a713-0e7eaf772cf9",
      "inners": [
        { "value": "Bagryanik" },
        { "value": "Lotos" },
        { "value": "Atirgul" },
        { "value": "Jiyda" },
        { "value": "Nimadur yana gul" }
      ]
    },
    {
      "statement_column": "2115cc9b-8aff-41ec-b73a-1750b5ff42cd",
      "inners": [
        { "value": "mol" },
        { "value": "qoy" },
        { "value": "ochki" },
        { "value": "telefon" },
        { "value": "Davlat" },
        { "value": "Iphone" }
      ]
    },
    {
      "statement_column": "f4ff900c-bcb1-4972-b1bb-15d2df9af813",
      "inners": [
        { "value": "fa6b4ffc-cc9f-4a59-bd8f-190241e06392" }
      ]
    },
    {
      "statement_column": "db838543-a869-42be-a600-b38d31b1fb19",
      "inners": [
        { "value": "11" },
        { "value": "22" },
        { "value": "33" }
      ]
    },
    {
      "statement_column": "e398f48c-ab40-4c3f-b1be-c36742794edf",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "84a74b5a-03c8-49e8-bc61-8bd226b0a62b",
      "inners": [
        { "value": "fa6b4ffc-cc9f-4a59-bd8f-190241e06392" }
      ]
    },
    {
      "statement_column": "3ac14d68-f26e-4417-9c26-60962e6bb71f",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    }
  ]
}
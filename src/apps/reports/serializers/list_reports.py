from rest_framework import serializers
from apps.reports.models import Report, StatementColumn
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

    def get_report_items(self, report):
        lang = get_lang_code(self.context)
        # ❗️ Bunda inner so‘rov ketmaydi, chunki oldindan prefetch bo‘lgan
        items = report.report_items.all()

        if report.is_general:
            organization_id = "general"
            organization_name = "Barcha tashkilotlar bo‘yicha umumiy"

            org_qs = Report.objects.filter(
                statement=report.statement,
                deadline=report.deadline,
                is_general=False
            ).values("organization_id", "organization__name").distinct()

            org_inners = [
                {"id": str(o["organization_id"]), "value": o["organization__name"] or ""}
                for o in org_qs
            ]

            org_column = StatementColumn.objects.filter(
                statement=report.statement,
                is_organization=True
            ).first()

            org_column_json = {
                "statement_column_id": str(org_column.id),
                "statement_column_name": get_translated_field(org_column, "title", lang),
                "inners": org_inners
            }

            other_columns = []
            for item in items:
                if item.statement_column.is_organization:
                    continue
                other_columns.append({
                    "statement_column_id": str(item.statement_column.id),
                    "statement_column_name": get_translated_field(item.statement_column, "title", lang),
                    # ❗️ Bu yerda endi query bo‘lmaydi
                    "inners": [
                        {"id": str(inner.id), "value": inner.value}
                        for inner in item.inners.all()
                    ]
                })

            return [{
                "organization_id": organization_id,
                "organization_name": organization_name,
                "statement_columns": [org_column_json] + other_columns
            }]
        else:
            return [{
                "organization_id": str(report.organization.id),
                "organization_name": report.organization.name,
                "statement_columns": [
                    {
                        "statement_column_id": str(item.statement_column.id),
                        "statement_column_name": get_translated_field(item.statement_column, "title", lang),
                        # ❗️ Bu yerda ham query bo‘lmaydi
                        "inners": [
                            {"id": str(inner.id), "value": inner.value}
                            for inner in item.inners.all()
                        ]
                    }
                    for item in items
                ]
            }]


# XODIM HISOBI ==========================================
{
  "deadline": "9c1d32be-c555-422e-a6de-52414026da5e",
  "report_items": [
    {
      "statement_column": "0ab7b707-3f6e-47b0-bc43-f749c016e109",
      "inners": [
        { "value": "c0b0e7be-db01-48ed-bf65-0500ad608ec0" }
      ]
    },
    {
      "statement_column": "b64b093f-14fc-4c9f-a437-ef5f397b287f",
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
      "statement_column": "a034a391-7981-45ce-be8a-35eff8c70f90",
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
      "statement_column": "16f981f0-a49e-43c6-b220-b1fa8d29d85f",
      "inners": [
        { "value": "11" },
        { "value": "22" },
        { "value": "33" }
      ]
    },
    {
      "statement_column": "46f97fde-6271-41e5-a03c-09c93fa16f1b",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "9e153529-6db2-4b34-9f7c-a5a98f497374",
      "inners": [
        { "value": "c0b0e7be-db01-48ed-bf65-0500ad608ec0" }
      ]
    },
    {
      "statement_column": "badd2eea-19f3-4f00-bcdf-a1c81b6f66bc",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "8c0e85bf-3639-45a9-bd46-2de6deb05eff",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "500" }
      ]
    },
    {
      "statement_column": "929c4890-4a30-48b7-bd26-f10c48b5bdf0",
      "inners": [
        { "value": "100" },
        { "value": "650" },
        { "value": "500" }
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


{
  "deadline": "67b18205-7f60-4492-a9d5-99fa8c5a3c58",
  "report_items": [
    {
      "statement_column": "332bf656-956b-4da6-8c90-2bd283ed33ae",
      "inners": [
        { "value": "db1e6111-9791-4ddc-b421-806fbe0f89fb" }
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
        { "value": "db1e6111-9791-4ddc-b421-806fbe0f89fb" }
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
        { "value": "db1e6111-9791-4ddc-b421-806fbe0f89fb" }
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


{
  "deadline": "34257f28-10e9-4810-b03e-a4d72259f921",
  "report_items": [
    {
      "statement_column": "b57bfc34-753c-42cf-b96b-5cbb672e5fc2",
      "inners": [
        { "value": "db1e6111-9791-4ddc-b421-806fbe0f89fb" }
      ]
    },
    {
      "statement_column": "ea2d27d2-4949-45d9-b3ba-9b4b8b3c7f6e",
      "inners": [
        { "value": "Bagryanik" },
        { "value": "Lotos" },
        { "value": "Atirgul" },
        { "value": "Jiyda" },
        { "value": "Nimadur yana gul" }
      ]
    },
    {
      "statement_column": "a7f822a6-354a-41ad-b420-4b01a1b61c12",
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
      "statement_column": "79a7d447-1547-4c3a-a2a1-80abe0c52426",
      "inners": [
        { "value": "db1e6111-9791-4ddc-b421-806fbe0f89fb" }
      ]
    },
    {
      "statement_column": "101156ec-4c6c-4e42-8607-adebe4b014e3",
      "inners": [
        { "value": "11" },
        { "value": "22" },
        { "value": "33" }
      ]
    },
    {
      "statement_column": "30e8e34b-5572-4d2f-9c6a-156bbf689d02",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    }
  ]
}

# ========== JAMGARMA

{
  "deadline": "d696556b-aac2-41dc-ad1c-f4f5e31952ce",
  "report_items": [
    {
      "statement_column": "7013d65e-bf85-4125-be4a-454a08a78b83",
      "inners": [
        { "value": "6499fe70-27d3-49bc-bf07-6441edb4043c" }
      ]
    },
    {
      "statement_column": "54c01ea0-79bd-4055-853b-705070b5451f",
      "inners": [
        { "value": "Bagryanik" },
        { "value": "Lotos" },
        { "value": "Atirgul" },
        { "value": "Jiyda" },
        { "value": "Nimadur yana gul" }
      ]
    },
    {
      "statement_column": "2636d800-e036-4138-a3b7-811d764e74db",
      "inners": [
        { "value": "mol" },
        { "value": "foiAWHFa" },
        { "value": "iOAHFX" },
        { "value": "AWKJLFFaKDXLnl" }
      ]
    },
    {
      "statement_column": "f4c08030-d9f9-404d-9de7-829aad620890",
      "inners": [
        { "value": "22" },
        { "value": "45" },
        { "value": "10" }
      ]
    },
    {
      "statement_column": "d9afd592-c82a-4cc3-bdf3-6dcb4e03b4ab",
      "inners": [
        { "value": "200" },
        { "value": "400" },
        { "value": "850" }
      ]
    },
    {
      "statement_column": "df28ad25-a558-45ea-b784-17978e15d85c",
      "inners": [
        { "value": "0.2" },
        { "value": "0.65" },
        { "value": "0.541" }
      ]
    }
  ]
}
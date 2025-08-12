from rest_framework import serializers
from apps.reports.models import Report, StatementColumn
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
        items = list(report.report_items.all().order_by("statement_column__id"))

        if report.is_general:
            organization_id = "general"
            organization_name = "Barcha tashkilotlar bo‘yicha umumiy"

            org_column = StatementColumn.objects.filter(
                statement=report.statement,
                is_organization=True
            ).first()

            org_column_json = {
                "statement_column_id": str(org_column.id),
                "statement_column_name": get_translated_field(org_column, "title", lang),
                "inners": [
                    {
                        "id": organization_id,
                        "value": "Jami"
                    }
                ]
            }

            other_columns = [
                {
                    "statement_column_id": str(item.statement_column.id),
                    "statement_column_name": get_translated_field(item.statement_column, "title", lang),
                    "inners": [
                        {"id": str(inner.id), "value": inner.value}
                        for inner in item.inners.all()
                    ]
                }
                for item in items
                if not item.statement_column.is_organization
            ]

            return [{
                "organization_id": organization_id,
                "organization_name": organization_name,
                "statement_columns": [org_column_json] + other_columns
            }]
        else:
            # Organization columnni ajratamiz
            org_items = [item for item in items if item.statement_column.is_organization]
            other_items = [item for item in items if not item.statement_column.is_organization]

            # Organizationni boshida qo'yamiz
            sorted_items = org_items + other_items

            return [{
                "organization_id": str(report.organization.id),
                "organization_name": get_translated_field(report.organization, "name", lang),
                "statement_columns": [
                    {
                        "statement_column_id": str(item.statement_column.id),
                        "statement_column_name": get_translated_field(item.statement_column, "title", lang),
                        "inners": [
                            {
                                "id": str(inner.id),
                                "value": get_translated_field(report.organization, "name", lang)
                            }
                            if item.statement_column.is_organization
                            else {
                                "id": str(inner.id),
                                "value": inner.value
                            }
                            for inner in item.inners.all()
                        ]
                    }
                    for item in sorted_items
                ]
            }]

    # def get_report_items(self, report):
    #     lang = get_lang_code(self.context)
    #     # ❗️ Bunda inner so‘rov ketmaydi, chunki oldindan prefetch bo‘lgan
    #     items = report.report_items.all()
    #
    #     if report.is_general:
    #         organization_id = "general"
    #         organization_name = "Barcha tashkilotlar bo‘yicha umumiy"
    #
    #         org_qs = Report.objects.filter(
    #             statement=report.statement,
    #             deadline=report.deadline,
    #             is_general=False
    #         ).values("organization_id", "organization__name").distinct()
    #
    #         org_inners = [
    #             {"id": str(o["organization_id"]), "value": o["organization__name"] or ""}
    #             for o in org_qs
    #         ]
    #
    #         org_column = StatementColumn.objects.filter(
    #             statement=report.statement,
    #             is_organization=True
    #         ).first()
    #
    #         org_column_json = {
    #             "statement_column_id": str(org_column.id),
    #             "statement_column_name": get_translated_field(org_column, "title", lang),
    #             "inners": org_inners
    #         }
    #
    #         other_columns = []
    #         for item in items:
    #             if item.statement_column.is_organization:
    #                 continue
    #             other_columns.append({
    #                 "statement_column_id": str(item.statement_column.id),
    #                 "statement_column_name": get_translated_field(item.statement_column, "title", lang),
    #                 # ❗️ Bu yerda endi query bo‘lmaydi
    #                 "inners": [
    #                     {"id": str(inner.id), "value": inner.value}
    #                     for inner in item.inners.all()
    #                 ]
    #             })
    #
    #         return [{
    #             "organization_id": organization_id,
    #             "organization_name": organization_name,
    #             "statement_columns": [org_column_json] + other_columns
    #         }]
    #     else:
    #         return [{
    #             "organization_id": str(report.organization.id),
    #             "organization_name": report.organization.name,
    #             "statement_columns": [
    #                 {
    #                     "statement_column_id": str(item.statement_column.id),
    #                     "statement_column_name": get_translated_field(item.statement_column, "title", lang),
    #                     # ❗️ Bu yerda ham query bo‘lmaydi
    #                     "inners": [
    #                         {"id": str(inner.id), "value": inner.value}
    #                         for inner in item.inners.all()
    #                     ]
    #                 }
    #                 for item in items
    #             ]
    #         }]


# XODIM HISOBI ==========================================
{
  "deadline": "793f13f7-1dfd-4d76-8953-23f50d42f8ba",
  "report_items": [
    {
      "statement_column": "7f0fcd6b-720e-4364-89ff-434c604c41f8",
      "inners": [
        { "value": "9440876a-5a92-4158-b35a-fb3d3d347fb1" }
      ]
    },
    {
      "statement_column": "ebb362ec-c23f-4e7c-8c86-735dc7b7aa2f",
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
      "statement_column": "cd7b849a-ab17-4b2d-9d5e-6777f8a97fb2",
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
      "statement_column": "aea4b522-6833-40b0-b72a-68d10f260c3b",
      "inners": [
        { "value": "11" },
        { "value": "22" },
        { "value": "33" }
      ]
    },
    {
      "statement_column": "925f9a9d-6117-4044-9800-09a2e359658a",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "f120ba8d-7721-43ae-8b97-d6215875c275",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "34552f70-9c57-4f4e-bb14-4e78d5877c5d",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "293532eb-276c-4a61-b2fd-88622bb149ab",
      "inners": [
        { "value": "10" },
        { "value": "20" },
        { "value": "30" }
      ]
    },
    {
      "statement_column": "16bd7b97-5d86-46e9-a757-19c855a432a6",
      "inners": [
        { "value": "10" },
        { "value": "20" },
        { "value": "30" }
      ]
    },
    {
      "statement_column": "ce4a777a-f708-4b95-afe3-97927c7a421b",
      "inners": [
        { "value": "15" },
        { "value": "27" },
        { "value": "39" }
      ]
    },
    {
      "statement_column": "ac66f266-a894-45de-b59e-64f846e49aa5",
      "inners": [
        { "value": "15" },
        { "value": "27" },
        { "value": "39" }
      ]
    },
    {
      "statement_column": "e975d4d4-c37e-4ab7-a5a7-1a159f6bbaf9",
      "inners": [
        { "value": "15" },
        { "value": "27" },
        { "value": "39" }
      ]
    },
    {
      "statement_column": "f8994604-4415-4642-83b2-0fd33cde1b28",
      "inners": [
        { "value": "15" },
        { "value": "27" },
        { "value": "39" }
      ]
    },
    {
      "statement_column": "1782fe73-9c2d-4151-a262-24361f62cdff",
      "inners": [
        { "value": "9440876a-5a92-4158-b35a-fb3d3d347fb1" }
      ]
    },
    {
      "statement_column": "5b83761e-dbcb-4c6f-b6ac-8d328db9228d",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "a5a10292-884c-4bea-b1b4-2c95fd0445d9",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "500" }
      ]
    },
    {
      "statement_column": "d13bcced-607e-4512-a200-0563643f4554",
      "inners": [
        { "value": "100" },
        { "value": "650" },
        { "value": "500" }
      ]
    },
    {
      "statement_column": "2a37170a-5490-493a-9164-4ffbc9685347",
      "inners": [
        { "value": "9440876a-5a92-4158-b35a-fb3d3d347fb1" }
      ]
    },
    {
      "statement_column": "7fbd76ca-4bd6-4e32-b09e-d557ff976c1b",
      "inners": [
        { "value": "112" },
        { "value": "255" },
        { "value": "320" }
      ]
    },
    {
      "statement_column": "5d22c4cc-079d-4bbe-adef-088322feb88b",
      "inners": [
        { "value": "114" },
        { "value": "310" },
        { "value": "222" }
      ]
    }
  ]
}

# DAROMAD =============================================

{
  "deadline": "6a102be3-3dda-4987-ad2c-f8eb3cffbc61",
  "report_items": [
    {
      "statement_column": "66a17616-1bfc-4e26-b5d1-86eae5a52dde",
      "inners": [
        { "value": "d3b53ed0-d5a1-4540-9104-1860c4ef90b3" }
      ]
    },
    {
      "statement_column": "ef6b158f-746d-4e80-9fc4-d1b4fd5fa72d",
      "inners": [
        { "value": "Bagryanik" },
        { "value": "Lotos" },
        { "value": "Atirgul" },
        { "value": "Jiyda" },
        { "value": "Nimadur yana gul" }
      ]
    },
    {
      "statement_column": "b9d75333-f287-4cd6-b565-c556b4cae1d3",
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
      "statement_column": "7c86baa8-56e1-40bb-8f43-128b78ad2186",
      "inners": [
        { "value": "d3b53ed0-d5a1-4540-9104-1860c4ef90b3" }
      ]
    },
    {
      "statement_column": "fc938a18-dbc3-4e46-93ca-122e3fbd7f25",
      "inners": [
        { "value": "11" },
        { "value": "22" },
        { "value": "33" }
      ]
    },
    {
      "statement_column": "e138fcb5-b1af-4f01-8941-7ea37034ae90",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    },
    {
      "statement_column": "40df2c81-1fc0-4b64-9117-f5ac8278c164",
      "inners": [
        { "value": "d3b53ed0-d5a1-4540-9104-1860c4ef90b3" }
      ]
    },
    {
      "statement_column": "8690d2cb-cdd7-4ef6-ab59-2e302da3adff",
      "inners": [
        { "value": "100" },
        { "value": "200" },
        { "value": "300" }
      ]
    }
  ]
}

# Xodimlar hisobi tahlili

{
  "deadline": "91f1eb5f-86f5-422e-98f9-10d30158f199",
  "report_items": [
    {
      "statement_column": "20981763-09d0-4ac7-9c5d-a4d0db8e1b32",
      "inners": [
        { "value": "9f92f99d-e8bd-475a-a49e-be7c4ef37093" }
      ]
    },
    {
      "statement_column": "00527516-dfe3-456e-a81e-8dc8bc806fea",
      "inners": [
        { "value": "2" },
        { "value": "2" }
      ]
    },
    {
      "statement_column": "21d21715-85c1-442c-ab29-214854cbf847",
      "inners": [
        { "value": "2" },
        { "value": "2" }
      ]
    },
    {
      "statement_column": "c65eb035-f319-483a-80fb-f19302125139",
      "inners": [
        { "value": "2" },
        { "value": "2" },
        { "value": "2" }
      ]
    },
    {
      "statement_column": "5c19968b-2342-4a94-b691-5660dce498f5",
      "inners": [
        { "value": "2" },
        { "value": "2" },
        { "value": "2" }
      ]
    },
    {
      "statement_column": "cd567acf-1078-40bb-9a9c-3e8385889d12",
      "inners": [
        { "value": "2" },
        { "value": "2" },
        { "value": "2" }
      ]
    }
  ]
}

# =============== Inson Resurslari.

{
  "deadline": "b90cf65b-253c-47a5-918c-b944c2ddad2b",
  "report_items": [
    {
      "statement_column": "df1e6a98-13c0-466a-a682-79395a6388e5",
      "inners": [
        { "value": "2b790f43-505e-4289-ae2c-f0e1a9dce1c2" }
      ]
    },
    {
      "statement_column": "aa70fbe3-542a-4fa7-bae4-fa10d65df71b",
      "inners": [
        { "value": "2" },
        { "value": "2" }
      ]
    },
    {
      "statement_column": "df3380a5-4668-455a-a788-f9b4ed41dd81",
      "inners": [
        { "value": "2" },
        { "value": "2" }
      ]
    },
    {
      "statement_column": "ba19e343-23cd-4ba9-80ce-a98ef110bce6",
      "inners": [
        { "value": "2" },
        { "value": "2" },
        { "value": "2" }
      ]
    },
    {
      "statement_column": "e982ddb4-dd8c-4c52-87fc-a3d29841d389",
      "inners": [
        { "value": "2" },
        { "value": "2" },
        { "value": "2" }
      ]
    },
    {
      "statement_column": "ab1ad789-b9b4-4477-b962-3277392d79bd",
      "inners": [
        { "value": "2" },
        { "value": "2" },
        { "value": "2" }
      ]
    },
    {
      "statement_column": "bfa4fdec-cc49-48da-9da0-9720df2af27f",
      "inners": [
        { "value": "2" },
        { "value": "2" },
        { "value": "2" }
      ]
    },
    {
      "statement_column": "a6eb4e8c-8a1e-406d-966d-8f06b3305c46",
      "inners": [
        { "value": "3" },
        { "value": "3" },
        { "value": "3" }
      ]
    },
    {
      "statement_column": "0f3e732e-ed9c-41ac-aa35-e628b692d866",
      "inners": [
        { "value": "3" },
        { "value": "3" },
        { "value": "3" }
      ]
    },
    {
      "statement_column": "002f1469-5765-4f4c-91ae-d87b5b055c83",
      "inners": [
        { "value": "3" },
        { "value": "3" },
        { "value": "3" }
      ]
    },
    {
      "statement_column": "135af0fb-aa1e-43ff-9f4d-8908da160682",
      "inners": [
        { "value": "3" },
        { "value": "3" },
        { "value": "3" }
      ]
    },
   {
      "statement_column": "b9419cea-a9a9-4ec6-a211-f70e260b8a8f",
      "inners": [
        { "value": "3" },
        { "value": "3" },
        { "value": "3" }
      ]
    },
    {
      "statement_column": "bf7ef700-fd7e-49f3-845b-eabb243cf10c",
      "inners": [
        { "value": "3" },
        { "value": "3" },
        { "value": "3" }
      ]
    },
    {
      "statement_column": "bc620cfb-a066-4e53-b4f4-c2be13ffabe9",
      "inners": [
        { "value": "2b790f43-505e-4289-ae2c-f0e1a9dce1c2" }
      ]
    },
    {
      "statement_column": "90eb83ae-8edb-4baf-9b8a-028cbe1d8285",
      "inners": [
        { "value": "4" },
        { "value": "4" },
        { "value": "4" }
      ]
    },
    {
      "statement_column": "be990097-d059-4023-b7d3-210a7931f6f0",
      "inners": [
        { "value": "4" },
        { "value": "4" },
        { "value": "4" }
      ]
    },
    {
      "statement_column": "bb43ea8d-08df-4708-b50e-0bdef121571e",
      "inners": [
        { "value": "4" },
        { "value": "4" },
        { "value": "4" }
      ]
    },
    {
      "statement_column": "ed5fdb35-25d6-4e3d-8b00-5d08f1b92386",
      "inners": [
        { "value": "2b790f43-505e-4289-ae2c-f0e1a9dce1c2" }
      ]
    },
    {
      "statement_column": "b1a1b90c-00af-4df6-b9f6-25f25f505a17",
      "inners": [
        { "value": "5" },
        { "value": "5" },
        { "value": "5" }
      ]
    },
    {
      "statement_column": "3f090310-4c1f-47e5-93ac-52eaea848f97",
      "inners": [
        { "value": "5" },
        { "value": "5" },
        { "value": "5" }
      ]
    },
    {
      "statement_column": "bd7d1420-55fb-4ff5-b859-0716ea665a5e",
      "inners": [
        { "value": "7" },
        { "value": "7" },
        { "value": "7" }
      ]
    }
  ]
}

# ========== JAMGARMA

{
  "deadline": "41e05ef2-dee1-4e27-a287-380e1061522b",
  "report_items": [
    {
      "statement_column": "1156c62b-2c7e-4105-8a18-3854475046c1",
      "inners": [
        { "value": "ebdbbaec-875e-4ef9-96a4-372f7f308c11" }
      ]
    },
    {
      "statement_column": "92024be4-6cf0-4f4e-86fe-a79a10f53a44",
      "inners": [
        { "value": "10" }
      ]
    },
    {
      "statement_column": "3a0ab140-07d0-49e0-a1ef-4374b98a2af7",
      "inners": [
        { "value": "5" }
      ]
    },
    {
      "statement_column": "768958db-f39d-4bc9-af76-e356ce498825",
      "inners": [
        { "value": "22" }
      ]
    },
    {
      "statement_column": "b8a1782e-ca72-4ea8-9f33-1cd4315d70bf",
      "inners": [
        { "value": "20" }
      ]
    },
    {
      "statement_column": "b9ba4561-40d9-4efb-8b76-d30a51eff30d",
      "inners": [
        { "value": "15" }
      ]
    },
    {
      "statement_column": "f6e50217-333f-4542-ae6c-5333c1a777b8",
      "inners": [
        { "value": "12" }
      ]
    },
    {
      "statement_column": "a65b39e9-57b4-4a99-8d66-6f43491a1ce7",
      "inners": [
        { "value": "5" }
      ]
    },
    {
      "statement_column": "47a1653e-635b-4178-a684-3181c8df3a4f",
      "inners": [
        { "value": "5" }
      ]
    },
    {
      "statement_column": "9cc0163f-c494-4945-843e-96568d3e33d4",
      "inners": [
        { "value": "30" }
      ]
    },
    {
      "statement_column": "7938926f-741c-4e22-a4ce-9f49ee30eadf",
      "inners": [
        { "value": "15" }
      ]
    },
    {
      "statement_column": "986ed56c-068d-4f4b-a690-da1fbebd552a",
      "inners": [
        { "value": "8" }
      ]
    },
    {
      "statement_column": "8e86804b-8dd7-41e4-99e6-d19f68477b4f",
      "inners": [
        { "value": "4" }
      ]
    }
  ]
}
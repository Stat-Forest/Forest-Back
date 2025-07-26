# def get_or_create_general_report(statement, deadline):
#     general_report, _ = Report.objects.get_or_create(
#         organization=None,
#         statement=statement,
#         deadline=deadline,
#         defaults={
#             "status": Report.StatusChoices.SAVED,
#             "is_general": True
#         }
#     )
#     return general_report
#
#
# def aggregate_general_report(statement, deadline):
#     # 1️⃣ Oddiy (general emas) reportlarni olamiz
#     reports = Report.objects.filter(
#         statement=statement,
#         deadline=deadline,
#         is_general=False
#     )
#
#     # 2️⃣ Tashkilotlar ro‘yxatini yig‘amiz (har doim JSON saqlash uchun)
#     org_qs = reports.values("organization_id", "organization__name")
#     org_list = [
#         {"id": str(o["organization_id"]), "name": o["organization__name"] or ""}
#         for o in org_qs.distinct()
#     ]
#
#     # 3️⃣ Faqat raqamli ustunlarni olamiz
#     numeric_columns = StatementColumn.objects.filter(
#         statement=statement,
#         is_organization=False
#     ).values_list("id", flat=True)
#
#     all_items = ReportItem.objects.filter(
#         report__in=reports,
#         statement_column_id__in=numeric_columns
#     )
#
#     # 4️⃣ Barcha ustunlar bo‘yicha yig‘indi hisoblaymiz
#     aggregated = (
#         all_items.values("statement_column")
#         .annotate(
#             total=Sum(
#                 Cast("inners__value", output_field=DecimalField(max_digits=20, decimal_places=2))
#             )
#         )
#     )
#
#     # 5️⃣ General reportni olish yoki yaratish
#     general_report = get_or_create_general_report(statement, deadline)
#
#     # Eski itemlarni tozalaymiz
#     ReportItem.objects.filter(report=general_report).delete()
#
#     # 6️⃣ Raqamli ustunlarni qo‘shamiz
#     new_items = []
#     new_inners = []
#
#     for row in aggregated:
#         col_id = row["statement_column"]
#         total_value = row["total"] or 0
#
#         report_item = ReportItem(
#             report=general_report,
#             statement_column_id=col_id
#         )
#         new_items.append(report_item)
#
#         new_inners.append(
#             ReportItemInner(
#                 report_item=report_item,
#                 value=str(total_value)
#             )
#         )
#
#     ReportItem.objects.bulk_create(new_items)
#     ReportItemInner.objects.bulk_create(new_inners)
#
#     # 7️⃣ Endi **Tashkilot nomi column** uchun JSON saqlaymiz
#     org_column = StatementColumn.objects.filter(
#         statement=statement,
#         is_organization=True
#     ).first()
#     if org_column:
#         # Bitta ReportItem yaratamiz
#         org_item = ReportItem.objects.create(
#             report=general_report,
#             statement_column=org_column
#         )
#         # ✅ Tashkilotlar ro‘yxatini JSON qilib saqlaymiz
#         ReportItemInner.objects.create(
#             report_item=org_item,
#             value=json.dumps(org_list, ensure_ascii=False)  # UTF-8 ni yo‘qotmaslik uchun
#         )
#
#     return general_report
#
#
# # ===================== LIST REPORT
#
#
#
#
# from rest_framework import serializers
# from apps.reports.models import Report, StatementColumn
# from apps.utils.services.general_values import build_columns_with_jami
# from apps.utils.translation import get_lang_code, get_translated_field
#
#
# class ReportListSerializer(serializers.ModelSerializer):
#     period = serializers.CharField(source='statement.period')
#     organization_name = serializers.SerializerMethodField()
#     report_items = serializers.SerializerMethodField()
#     statement_name = serializers.SerializerMethodField()
#     sent_by_full_name = serializers.SerializerMethodField()
#     sent_by_org_name = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Report
#         fields = (
#             'id', 'organization', 'organization_name',
#             'statement', 'statement_name',
#             'deadline', 'period', 'status',
#             'created_at', 'cancel_reason',
#             'cancelled_at', 'sent_at', 'accepted_at',
#             'report_items',
#             'sent_by_full_name', 'sent_by_org_name', 'sent_by_role',
#         )
#
#     def get_organization_name(self, obj):
#         lang = get_lang_code(self.context)
#         return get_translated_field(obj.organization, "name", lang)
#
#     def get_statement_name(self, obj):
#         lang = get_lang_code(self.context)
#         return get_translated_field(obj.statement, "name", lang)
#
#     def get_sent_by_full_name(self, obj):
#         if obj.sent_by:
#             return obj.sent_by.full_name
#         return None
#
#     def get_sent_by_org_name(self, obj):
#         lang = get_lang_code(self.context)
#         if obj.sent_by_org:
#             return get_translated_field(obj.sent_by_org, "name", lang)
#         return None
#
#     def get_report_items(self, report):
#         lang = get_lang_code(self.context)
#         items = report.report_items.select_related("statement_column")
#
#         # ✅ AGAR GENERAL REPORT BO'LSA
#         if report.is_general:
#             # General info
#             organization_id = "general"
#             organization_name = "Barcha tashkilotlar bo‘yicha umumiy"
#
#             # Barcha oddiy reportlardan organizationlarni yig‘ib olamiz
#             org_qs = Report.objects.filter(
#                 statement=report.statement,
#                 deadline=report.deadline,
#                 is_general=False
#             ).values("organization_id", "organization__name").distinct()
#
#             org_inners = [
#                 {"id": str(o["organization_id"]), "value": o["organization__name"] or ""}
#                 for o in org_qs
#             ]
#
#             # Faqat bitta organization columnni topamiz
#             org_column = StatementColumn.objects.filter(
#                 statement=report.statement,
#                 is_organization=True
#             ).first()
#
#             org_column_json = {
#                 "statement_column_id": str(org_column.id),
#                 "statement_column_name": get_translated_field(org_column, "title", lang),
#                 "inners": org_inners
#             }
#
#             # Qolgan barcha columnlarni chiqaramiz, lekin tashkilot nomini takrorlamaymiz
#             other_columns = []
#             for item in items.exclude(statement_column=org_column):
#                 # ❌ Agar yana is_organization=True bo'lsa SKIP qilamiz
#                 if item.statement_column.is_organization:
#                     continue
#
#                 other_columns.append({
#                     "statement_column_id": str(item.statement_column.id),
#                     "statement_column_name": get_translated_field(item.statement_column, "title", lang),
#                     "inners": [
#                         {"id": str(inner.id), "value": inner.value}
#                         for inner in item.inners.all()
#                     ]
#                 })
#
#             return [{
#                 "organization_id": organization_id,
#                 "organization_name": organization_name,
#                 # ❗️ Faqat 1 marta organization column, keyin boshqa columnlar
#                 "statement_columns": [org_column_json] + other_columns
#             }]
#
#         # ✅ Oddiy report bo‘lsa o‘z holicha
#         else:
#             return [{
#                 "organization_id": str(report.organization.id),
#                 "organization_name": report.organization.name,
#                 "statement_columns": [
#                     {
#                         "statement_column_id": str(item.statement_column.id),
#                         "statement_column_name": get_translated_field(item.statement_column, "title", lang),
#                         "inners": [
#                             {"id": str(inner.id), "value": inner.value}
#                             for inner in item.inners.all()
#                         ]
#                     }
#                     for item in items
#                 ]
#             }]
#
# # =============================== CREATE REPORT
#
# import uuid
#
# from django.db import transaction
# from rest_framework import serializers
#
# from apps.general.models import Organization
# from apps.reports.models import Report, ReportItem, StatementColumn, ReportItemInner
# from apps.reports.services.general_report import aggregate_general_report
# from apps.utils.translation import get_lang_code, get_translated_field
#
#
# class ReportItemInnerSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ReportItemInner
#         fields = ["id", "value"]
#
#
# class ReportItemSerializer(serializers.ModelSerializer):
#     inners = ReportItemInnerSerializer(many=True)
#
#     class Meta:
#         model = ReportItem
#         fields = ["statement_column", "inners"]
#
#
# class ReportCreateSerializer(serializers.ModelSerializer):
#     report_items = serializers.ListField(write_only=True)
#
#     class Meta:
#         model = Report
#         fields = [
#             "id", "deadline",
#             "report_items"
#         ]
#
#     def create(self, validated_data):
#         items_data = validated_data.pop("report_items")
#         deadline = validated_data["deadline"]
#
#         # columnlarni oldindan map qilamiz
#         column_ids = [item["statement_column"] for item in items_data]
#         columns_map = {
#             str(c.id): c
#             for c in StatementColumn.objects.filter(id__in=column_ids).select_related("statement")
#         }
#
#         reports_map = {}
#         current_org_id = None
#
#         # ✅ Hamma narsani bufferga yig‘amiz
#         report_items_buffer = []  # bu ReportItem bulk_create uchun
#         report_inners_buffer = []  # bu ReportItemInner bulk_create uchun
#
#         with transaction.atomic():
#             for item in items_data:
#                 col_id = item["statement_column"]
#                 column = columns_map.get(col_id)
#                 if not column:
#                     raise serializers.ValidationError({"detail": f"Invalid column {col_id}"})
#
#                 inners_data = item.get("inners", [])
#
#                 # 1️⃣ ORGANIZATION BLOKI
#                 if column.is_organization:
#                     if not inners_data or "value" not in inners_data[0]:
#                         raise serializers.ValidationError(
#                             {"detail": f"Organization inners required for column {col_id}"}
#                         )
#                     current_org_id = inners_data[0]["value"]
#
#                     # bu orgga tegishli report
#                     report_key = (current_org_id, str(column.statement.id))
#                     if report_key not in reports_map:
#                         org_instance = Organization.objects.get(id=current_org_id)
#                         report, _ = Report.objects.get_or_create(
#                             organization=org_instance,
#                             statement=column.statement,
#                             deadline=deadline,
#                             defaults={"status": Report.StatusChoices.SAVED}
#                         )
#                         reports_map[report_key] = report
#
#                     report = reports_map[report_key]
#
#                     # ✅ ReportItem ni bufferga qo‘shamiz
#                     report_item_id = uuid.uuid4()
#                     report_items_buffer.append(
#                         ReportItem(
#                             id=report_item_id,
#                             report=report,
#                             statement_column=column
#                         )
#                     )
#                     # Organization column inners
#                     for inner in inners_data:
#                         report_inners_buffer.append(
#                             ReportItemInner(
#                                 report_item_id=report_item_id,
#                                 value=inner["value"]
#                             )
#                         )
#                     continue
#
#                 # 2️⃣ Oddiy columnlar
#                 if not current_org_id:
#                     raise serializers.ValidationError({"detail": "Organization column required before data columns"})
#
#                 child_statement = column.statement
#                 report_key = (current_org_id, str(child_statement.id))
#                 if report_key not in reports_map:
#                     org_instance = Organization.objects.get(id=current_org_id)
#                     report, _ = Report.objects.get_or_create(
#                         organization=org_instance,
#                         statement=child_statement,
#                         deadline=deadline,
#                         defaults={"status": Report.StatusChoices.SAVED}
#                     )
#                     reports_map[report_key] = report
#
#                 report = reports_map[report_key]
#
#                 # ✅ ReportItem ni bufferga qo‘shamiz
#                 report_item_id = uuid.uuid4()
#                 report_items_buffer.append(
#                     ReportItem(
#                         id=report_item_id,
#                         report=report,
#                         statement_column=column
#                     )
#                 )
#                 # bu columnning barcha inners’larini bufferga qo‘shamiz
#                 for inner in inners_data:
#                     report_inners_buffer.append(
#                         ReportItemInner(
#                             report_item_id=report_item_id,
#                             value=inner["value"]
#                         )
#                     )
#
#             # ✅ Endi 1 marta DB query bilan bulk_create qilamiz
#             ReportItem.objects.bulk_create(report_items_buffer, batch_size=1000)
#             ReportItemInner.objects.bulk_create(report_inners_buffer, batch_size=2000)
#
#             # ✅ General reportni yangilaymiz (faqat 1 marta)
#             if reports_map:
#                 # barcha reportlar bitta statement bo‘yicha bo‘ladi
#                 any_report = list(reports_map.values())[0]
#                 aggregate_general_report(any_report.statement, deadline)
#
#         return Report.objects.filter(id__in=[r.id for r in reports_map.values()])
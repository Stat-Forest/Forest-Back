# def get_report_items(self, obj):
#     items = (
#         obj.report_items
#         .select_related("statement_column")
#         .prefetch_related("inners")
#         .all()
#     )
#     lang = get_lang_code(self.context)
#     org_id = str(obj.organization_id)
#     org_name = get_translated_field(obj.organization, "name", lang) if obj.organization else "Noma'lum tashkilot"
#
#     # Hamma columnlarni yig‘ib olamiz
#     columns = []
#     for item in items:
#         column = item.statement_column
#         columns.append({
#             "statement_column_id": str(column.id),
#             "statement_column_name": get_translated_field(column, "title", lang),
#             "ordering": column.ordering,  # ✅ ordering ni ham olib qo‘yamiz
#             "inners": [
#                 {"id": str(inner.id), "value": inner.value}
#                 for inner in item.inners.all()
#             ]
#         })
#
#     # ✅ ordering bo‘yicha sort qilamiz (masalan 1.1.1.1 oldin, keyin 1.1.2.1 ...)
#     columns.sort(key=lambda c: [
#         int(x) if x.isdigit() else 0 for x in c["ordering"].split(".")
#     ])
#
#     # keyin ordering fieldni olib tashlaymiz, chiqmasin
#     for c in columns:
#         c.pop("ordering", None)
#
#     normal_columns, general_columns = build_columns_with_jami(columns)
#
#     return [{
#         "organization_id": org_id,
#         "organization_name": org_name,
#         "statement_columns": normal_columns,
#         "general": general_columns
#     }]

# def aggregate_general_report(statement, deadline):
#     # 1️⃣ Avval barcha oddiy reportlarni olamiz
#     reports = Report.objects.filter(
#         statement=statement,
#         deadline=deadline,
#         is_general=False
#     )
#
#     # 2️⃣ Tashkilotlar ro‘yxatini yig‘amiz
#     org_qs = reports.values("organization_id", "organization__name")
#     org_list = [
#         {"id": str(o["organization_id"]), "name": o["organization__name"] or ""}
#         for o in org_qs
#     ]
#
#     # 3️⃣ Faqat raqamli ustunlarni olamiz (masalan, is_numeric=True bo‘lsa)
#     numeric_columns = StatementColumn.objects.filter(
#         statement=statement,
#         is_numeric=True
#     ).values_list("id", flat=True)
#
#     all_items = ReportItem.objects.filter(
#         report__in=reports,
#         statement_column_id__in=numeric_columns
#     )
#
#     # 4️⃣ Raqamlarni yig‘amiz
#     aggregated = (
#         all_items.values("statement_column")
#         .annotate(
#             total=Sum(
#                 Cast(
#                     "inners__value",
#                     output_field=DecimalField(max_digits=20, decimal_places=2)
#                 )
#             )
#         )
#     )
#
#     # 5️⃣ General reportni yaratamiz
#     general_report = get_or_create_general_report(statement, deadline)
#
#     # Eski itemlarni tozalab tashlaymiz
#     ReportItem.objects.filter(report=general_report).delete()
#
#     # 6️⃣ Yangi ReportItem va ularning inners’larini yaratamiz
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
#     # ✅ Bulk create raqamli ustunlar
#     ReportItem.objects.bulk_create(new_items)
#     ReportItemInner.objects.bulk_create(new_inners)
#
#     # 7️⃣ Endi **Tashkilot nomi column**ni qo‘shamiz (faqat bitta marta)
#     org_column = StatementColumn.objects.filter(
#         statement=statement,
#         is_organization=True
#     ).first()
#     if org_column:
#         org_item = ReportItem.objects.create(
#             report=general_report,
#             statement_column=org_column
#         )
#         ReportItemInner.objects.create(
#             report_item=org_item,
#             value=json.dumps(org_list)  # barcha tashkilotlarni JSON formatda saqlaymiz
#         )
#
#     return general_report
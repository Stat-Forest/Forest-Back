# import os
# from datetime import datetime
# from typing import List, Dict, Any, Tuple
#
# from openpyxl import Workbook
# from django.conf import settings
#
#
# def export_universal_report_to_excel(
#     reports: List[Dict[str, Any]],
#     *,
#     filename_prefix: str = "report_export",
#     lang: str = "uz"
# ) -> Tuple[str, str]:
#     print("📊 Exporting reports to Excel...")
#     print(f"🧾 Total reports: {len(reports)}")
#
#     now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
#     filename = f"{filename_prefix}_{now_str}.xlsx"
#     export_dir = getattr(settings, "EXPORT_ROOT", os.path.join(settings.BASE_DIR, "exports"))
#     os.makedirs(export_dir, exist_ok=True)
#     file_path = os.path.join(export_dir, filename)
#
#     wb = Workbook()
#     ws = wb.active
#     ws.title = "Reports"
#
#     # 1️⃣ Barcha ustunlar ordering bo‘yicha yig‘iladi
#     all_columns = dict()
#     for report in reports:
#         for item in report["report_items"]:
#             for col in item.get("statement_columns", []):
#                 ordering = col.get("statement_column_ordering")
#                 name = col.get("statement_column_name")
#                 if ordering and name:
#                     all_columns[ordering] = name
#
#     # 2️⃣ Ordering bo‘yicha sort qilamiz
#     sorted_orderings = sorted(all_columns.keys(), key=lambda x: [int(i) if i.isdigit() else i for i in x.split('.')])
#     column_names = [all_columns[ordr] for ordr in sorted_orderings]
#
#     # 3️⃣ Header yozamiz
#     header = ["№", "Tashkilot nomi"] + column_names
#     ws.append(header)
#
#     # 4️⃣ Har bir report bo‘yicha qiymatlarni qo‘shamiz
#     for idx, report in enumerate(reports, start=1):
#         org_name = report.get("organization_name", "")
#         row = [idx, org_name]
#
#         # ordering -> value
#         col_value_map = {}
#         for item in report["report_items"]:
#             for col in item.get("statement_columns", []):
#                 ordering = col.get("statement_column_ordering")
#                 inners = col.get("inners", [])
#                 value = inners[0]["value"] if inners else ""
#                 if ordering:
#                     col_value_map[ordering] = value
#
#         for ordering in sorted_orderings:
#             row.append(col_value_map.get(ordering, ""))
#
#         ws.append(row)
#
#     # 5️⃣ Ustunlarni kengaytiramiz
#     for column_cells in ws.columns:
#         length = max(len(str(cell.value or "")) for cell in column_cells)
#         ws.column_dimensions[column_cells[0].column_letter].width = length + 2
#
#     wb.save(file_path)
#     print(f"✅ Excel file saved at: {file_path}")
#     return file_path, filename
#
#

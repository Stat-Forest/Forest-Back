# from rest_framework.views import APIView
# from rest_framework.response import Response
#
# from django.utils.encoding import smart_str
# from django.http import FileResponse, Http404
#
# from apps.reports.models import Report
# from apps.reports.serializers.reports.list_reports import ReportListSerializer
# from apps.reports.exports.excel_export import export_universal_report_to_excel
#
#
# class ReportExcelExportAPIView(APIView):
#
#     def post(self, request, *args, **kwargs):
#         report_ids = request.data.get("report_ids", [])
#         lang = request.data.get("lang", "uz").lower()
#
#         print("📥 POST request received with report_ids =", report_ids)
#
#         if not report_ids:
#             print("⛔ report_ids is missing")
#             return Response(
#                 {"detail": "report_ids ro'yxati yuborilmadi."},
#                 status=400
#             )
#
#         reports = Report.objects.filter(id__in=report_ids).prefetch_related(
#             "report_items__statement_column",
#             "report_items__inners",
#             "organization"
#         )
#
#         print(f"🔎 Found {reports.count()} reports in DB")
#
#         if not reports.exists():
#             print("❌ No reports found for given IDs")
#             raise Http404("Tanlangan reportlar topilmadi.")
#
#         serializer = ReportListSerializer(reports, many=True, context={"request": request})
#         print("✅ Report serialization done.")
#
#         file_path, filename = export_universal_report_to_excel(
#             serializer.data,
#             lang=lang,
#             filename_prefix="exported_reports"
#         )
#
#         print(f"📁 Excel file generated at: {file_path}")
#
#         try:
#             return FileResponse(
#                 open(file_path, "rb"),
#                 as_attachment=True,
#                 filename=smart_str(filename),
#                 content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#             )
#         except Exception as e:
#             print("❌ File response failed:", str(e))
#             return Response(
#                 {"detail": "Excel faylni ochishda xatolik yuz berdi", "error": str(e)},
#                 status=500
#             )

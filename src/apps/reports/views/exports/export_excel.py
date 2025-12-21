import os
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response

from django.conf import settings
from django.utils.encoding import smart_str
from django.http import FileResponse, Http404

from drf_spectacular.utils import extend_schema

from apps.reports.models import Report
from apps.logs.models import HistoryActionJournal
from apps.reports.serializers.reports.list_reports import ReportListSerializer
from apps.reports.exports.excel_export import export_universal_report_to_excel_v2
from apps.reports.serializers.export.export_serializers import ReportExcelExportRequestSerializer


@extend_schema(tags=["Export-Excel"])
class ReportExcelExportAPIView(APIView):
    """
    Reportlarni Excel formatda eksport qilish API.
    """

    @extend_schema(
        request=ReportExcelExportRequestSerializer,
        responses={
            200: None,
            400: dict,
            500: dict,
        },
        description="Reportlarni Excel formatda eksport qilish"
    )
    def post(self, request, *args, **kwargs):
        """
        POST orqali Excel faylni yaratish va yuklab olish.
        Body:
        {
            "report_ids": ["uuid1", "uuid2"],
            "lang": "uz",
            "mode": "json"  // optional
        }
        """
        report_ids = request.data.get("report_ids", [])
        lang = request.data.get("lang", "uz").lower()
        mode = str(request.data.get("mode", "")).lower()

        if not report_ids:
            return Response({"detail": "report_ids ro'yxati yuborilmadi."}, status=400)

        respond_json = (mode == "json")

        try:
            return self._do_export(request, report_ids, lang, respond_json)
        except Http404:
            raise
        except Exception as e:
            return Response({"detail": "Export xatosi", "error": str(e)}, status=500)

    def get(self, request, *args, **kwargs):
        """
        Faqat test yoki Swagger UI uchun qo‘llanadi.
        Masalan:
        /api/v1/reports/export-excel/?ids=a,b,c&lang=uz&mode=json
        """
        ids_param = request.query_params.get("ids", "")
        lang = request.query_params.get("lang", "uz").lower()
        mode = request.query_params.get("mode", "").lower()

        if not ids_param:
            return Response({
                "detail": "Bu GET endpoint. Excel export qilish uchun POST so‘rov yuboring.",
                "example": {
                    "report_ids": ["uuid1", "uuid2"],
                    "lang": "uz"
                }
            }, status=200)

        report_ids = [i.strip() for i in ids_param.split(",") if i.strip()]
        respond_json = (mode == "json")

        try:
            return self._do_export(request, report_ids, lang, respond_json)
        except Http404:
            raise
        except Exception as e:
            return Response({"detail": "Export xatosi", "error": str(e)}, status=500)

    def _do_export(self, request, report_ids, lang, respond_json: bool = False):
        # Optimallashtirilgan queryset
        reports = (
            Report.objects.filter(id__in=report_ids)
            .select_related("organization", "statement")  # statement ni select_related qildik
            .prefetch_related(
                "report_items__statement_column",
                "report_items__statement_column__parent",
                "report_items__inners",
            )
        )

        if not reports.exists():
            raise Http404("Tanlangan reportlar topilmadi.")

        # Barcha reportlar bitta statementga tegishli ekanligini tekshirish
        statement_ids = set(reports.values_list("statement_id", flat=True))
        if len(statement_ids) != 1:
            return Response({
                "detail": "Barcha tanlangan hisobotlar bitta hisobot formasiga (Statement) tegishli bo‘lishi kerak."
            }, status=400)

        statement = reports.first().statement

        # Statement nomini olish (uz yoki ru ga qarab)
        statement_name = getattr(statement, f"name_{lang}", None) or statement.name

        # Sana va vaqtni chiroyli formatda
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M")

        # Fayl nomida ruxsat etilmagan belgilarni tozalash (qo'shimcha himoya)
        invalid_chars = '<>:"/\\|?*'
        safe_name = "".join(c if c not in invalid_chars else "_" for c in statement_name)
        safe_name = safe_name.strip().replace(" ", "_")

        # Yakuniy prefix — faqat fayl nomi uchun, hech qachon yo‘l emas
        filename_prefix = f"{safe_name}_{date_str}_{time_str}"

        serializer = ReportListSerializer(
            reports,
            many=True,
            context={"request": request, "lang": lang}
        )

        file_path, filename = export_universal_report_to_excel_v2(
            serializer.data,
            lang=lang,
            filename_prefix=filename_prefix,  # bu yerda yangi prefix
            statement_id=str(statement.id),
        )

        # Log yozish (statement nomi bilan boyitdik)
        try:
            HistoryActionJournal.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action="change",
                model_name="ReportExport",
                object_repr=filename,
                change_message=(
                    f"Exported {reports.count()} reports from '{statement_name}'; "
                    f"lang={lang}; date={date_str} {time_str}; "
                    f"report_ids={[str(r.id) for r in reports]}"
                ),
            )
        except Exception:
            pass

        if respond_json:
            download_url = request.build_absolute_uri(
                f"/api/v1/reports/export-excel/download/?filename={filename}"
            )
            return Response({
                "detail": "Export muvaffaqiyatli bajarildi",
                "filename": filename,
                "statement": statement_name,
                "export_date": f"{date_str} {time_str}",
                "download_url": download_url,
            })

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=smart_str(filename),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


@extend_schema(tags=["Export-Excel"])
class ReportExcelDownloadAPIView(APIView):
    def get(self, request, *args, **kwargs):
        filename = request.query_params.get("filename")
        if not filename:
            return Response({"detail": "filename query param kiritilmadi"}, status=400)

        export_dir = getattr(settings, "EXPORT_ROOT", os.path.join(settings.BASE_DIR, "exports"))
        file_path = os.path.join(export_dir, filename)

        if not os.path.exists(file_path):
            raise Http404("Fayl topilmadi")

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=smart_str(filename),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

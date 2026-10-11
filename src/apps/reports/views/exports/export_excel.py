import os
from datetime import datetime

from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response

from django.conf import settings
from django.utils.encoding import smart_str
from django.http import FileResponse, Http404

from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.billing.scope import is_billing_role
from apps.reports.models import Report
from apps.reports.permissions.report_scope import scope_reports_for_user
from apps.reports.services.kadastr import is_kadastr_child
from apps.logs.models import HistoryActionJournal
from apps.reports.serializers.reports.list_reports import ReportListSerializer
from apps.reports.serializers.plant.plant_report_list import PlantReportListSerializer
from apps.reports.models import ReportItemInner, StatementColumn
from apps.reports.exports.excel_export import export_universal_report_to_excel_v2
from apps.reports.services.report_import.columns import is_plant_based_statement
from apps.reports.serializers.export.export_serializers import ReportExcelExportRequestSerializer


def _is_safe_export_filename(filename: str) -> bool:
    return (
        filename == os.path.basename(filename)
        and "\\" not in filename
        and "\x00" not in filename
        and not filename.startswith(".")
        and filename.lower().endswith(".xlsx")
    )


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
        except (Http404, PermissionDenied):
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
        # For GET testing, allow optional aggregated and rudimentary row_numbers via query (row_numbers not practical in GET)

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
        except (Http404, PermissionDenied):
            raise
        except Exception as e:
            return Response({"detail": "Export xatosi", "error": str(e)}, status=500)

    def _do_export(self, request, report_ids, lang, respond_json: bool = False):
        # Optimallashtirilgan queryset
        reports = (
            Report.objects.filter(id__in=report_ids)
            .select_related("organization", "statement", "deadline", "sent_by", "sent_by_org")
            .prefetch_related(
                "report_items__statement_column",
                "report_items__statement_column__parent",
                "report_items__inners",
                "signatures",
            )
        )

        # Ijara billing rollari: faqat kadastr formalari va o'z ko'lamidagi hisobotlar
        if is_billing_role(request.user):
            requested_statement_ids = set(reports.values_list("statement_id", flat=True))
            if not all(is_kadastr_child(sid) for sid in requested_statement_ids):
                raise PermissionDenied("Bu hisobot formasi sizning rolingiz uchun yopiq.")
            reports = scope_reports_for_user(reports, request.user)

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

        # Preserve input order of IDs
        id_position = {rid: idx for idx, rid in enumerate(report_ids)}
        base_reports = sorted(list(reports), key=lambda r: id_position.get(str(r.id), 10**9))

        # Detect aggregated summary mode: if the incoming list contains any regional or national Jami
        aggregated_mode_detected = any(getattr(r, "is_general", False) or getattr(r, "is_republic", False) for r in base_reports)
        # Allow explicit override via request
        aggregated_flag = request.data.get("aggregated", None) if hasattr(request, 'data') else None
        if isinstance(aggregated_flag, bool):
            aggregated_mode = aggregated_flag
        else:
            aggregated_mode = aggregated_mode_detected

        # Export tarkibi: asosiy report + unga tegishli individual_general (tashkilot jami)
        combined_reports = []
        if aggregated_mode:
            # In aggregated mode we mirror rows exactly; no extra individual_general rows are appended
            combined_reports = base_reports
        else:
            # Tashkilot jami (individual_general) hisobotlari — bitta so'rov
            individual_by_key = {}
            for ind in (
                Report.objects.filter(
                    statement=statement,
                    is_individual_general=True,
                    organization_id__in={r.organization_id for r in base_reports},
                    deadline_id__in={r.deadline_id for r in base_reports},
                )
                .select_related("organization", "statement", "deadline", "sent_by", "sent_by_org")
                .prefetch_related(
                    "report_items__statement_column",
                    "report_items__statement_column__parent",
                    "report_items__inners",
                    "signatures",
                )
                .order_by("-created_at")
            ):
                individual_by_key.setdefault((ind.organization_id, ind.deadline_id), ind)
            for r in base_reports:
                combined_reports.append(r)
                ind = individual_by_key.get((r.organization_id, r.deadline_id))
                if ind:
                    combined_reports.append(ind)

        # Agar bu plantli jadval bo'lsa, maxsus serializer ishlatamiz.
        #
        # MUHIM: bu yerda "tanlangan hisobotlarda plantli qiymat bormi?" deb
        # tekshirish yetarli emas — plantlik jadvalning "Jami" hisobotida
        # plantsiz qiymatlar bo'ladi. Unda oddiy serializer tanlanib, export
        # o'simlik ustunini yo'qotardi va qiymatlarni qatorlar bo'ylab
        # tarqatib yuborardi (ilovalar zinapoya bo'lib ketardi).
        is_plant = (
            is_plant_based_statement(statement)
            or ReportItemInner.objects.filter(
                report_item__report__in=combined_reports, plant__isnull=False
            ).exists()
        )
        SerializerCls = PlantReportListSerializer if is_plant else ReportListSerializer
        # Pass row number map for hierarchical numbering if provided
        row_numbers_map = request.data.get("row_numbers", {}) if hasattr(request, 'data') else {}
        # Statement ustunlari bir marta (serializer'lar har hisobot uchun so'ramasin)
        columns = list(
            StatementColumn.objects.filter(statement_id=statement.id).select_related("parent")
        )
        serializer = SerializerCls(
            combined_reports,
            many=True,
            context={
                "request": request, "lang": lang, "aggregated_mode": aggregated_mode,
                "row_number_map": row_numbers_map,
                "columns_by_statement_id": {str(statement.id): columns},
                "statement_columns": {str(c.id): c for c in columns},
            }
        )

        file_path, filename = export_universal_report_to_excel_v2(
            serializer.data,
            lang=lang,
            filename_prefix=filename_prefix,  # bu yerda yangi prefix
            statement_id=str(statement.id),
            aggregated_mode=aggregated_mode,
        )

        # Log yozish (statement nomi bilan boyitdik)
        try:
            HistoryActionJournal.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action="change",
                model_name="ReportExport",
                object_repr=filename,
                change_message=(
                    f"Exported {len(base_reports)} reports from '{statement_name}'; "
                    f"lang={lang}; date={date_str} {time_str}; "
                    f"report_ids={[str(r.id) for r in base_reports]}"
                ),
            )
        except Exception:
            pass

        if respond_json:
            download_url = request.build_absolute_uri(
                f"/api/v1/reports/export-excel/download/?filename={filename}"
            )
            if download_url.startswith("http://"):
                download_url = download_url.replace("http://", "https://", 1)

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


@extend_schema(
    tags=["Export-Excel"],
    parameters=[
        OpenApiParameter(name="filename", required=True, type=str, location=OpenApiParameter.QUERY, description="Yaratilgan fayl nomi"),
    ],
)
class ReportExcelDownloadAPIView(APIView):
    def get(self, request, *args, **kwargs):
        filename = request.query_params.get("filename")
        if not filename:
            return Response({"detail": "filename query param kiritilmadi"}, status=400)

        # Faqat oddiy fayl nomi qabul qilinadi: "../.env" yoki "/etc/passwd"
        # kabi yo'llar orqali export papkasidan tashqariga chiqib bo'lmaydi.
        if not _is_safe_export_filename(filename):
            raise Http404("Fayl topilmadi")

        export_dir = os.path.realpath(
            getattr(settings, "EXPORT_ROOT", os.path.join(settings.BASE_DIR, "exports"))
        )
        file_path = os.path.realpath(os.path.join(export_dir, filename))
        if os.path.dirname(file_path) != export_dir or not os.path.isfile(file_path):
            raise Http404("Fayl topilmadi")

        # Fayl faqat uni eksport qilgan foydalanuvchiga beriladi
        # (eksport HistoryActionJournal'ga yoziladi).
        if not request.user.is_superuser and not HistoryActionJournal.objects.filter(
            user=request.user,
            model_name="ReportExport",
            object_repr=filename,
        ).exists():
            raise Http404("Fayl topilmadi")

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=smart_str(filename),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

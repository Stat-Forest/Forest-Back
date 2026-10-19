# apps/reports/views/plan_excel.py
from apps.reports.views.imports.import_excel import MAX_FILE_SIZE
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status, serializers

from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from drf_spectacular.types import OpenApiTypes

from apps.reports.models import Statement, Plan
from apps.reports.serializers.plan import PlanSerializer
from apps.reports.services.plan_excel import build_plan_template, parse_plan_excel, build_plan_export
from apps.reports.permissions import IsBolimAdmin
from apps.base.exceptions.exception_files import CustomExceptionError


def _owns_statement(user, statement):
    """Bo'lim admin faqat o'z bo'limiga (user.statement) tegishli statement'lar
    bilan ishlashi mumkin: plan.statement.parent === user.statement."""
    return bool(user.statement_id) and statement.parent_id == user.statement_id


# =============================================================================
# PLAN EXCEL TEMPLATE (download) — statement'ga mos, faqat kerakli ustunlar
# =============================================================================
@extend_schema(
    tags=["Plan"],
    parameters=[
        OpenApiParameter("statement", OpenApiTypes.UUID, required=True,
                          description="Qaysi bo'lim (Statement) uchun shablon kerak"),
        OpenApiParameter("lang", OpenApiTypes.STR, required=False, enum=["uz", "ru"]),
    ],
)
class PlanExcelTemplateAPIView(APIView):
    """
    GET /plan-excel/template/?statement=<uuid>&lang=uz

    Har bir statement o'z tartibida (oylik / choraklik / yillik / yillik_1+2
    / yillik_total / plant-based) shablon oladi — column ro'yxati
    `get_plan_input_columns` orqali dinamik aniqlanadi.

    Faqat bo'lim adminlari va faqat o'z bo'limiga tegishli statement uchun.
    """
    permission_classes = [IsBolimAdmin]

    def get(self, request):
        statement_id = request.query_params.get("statement")
        if not statement_id:
            return Response({"statement": _("This field is required.")}, status=400)

        try:
            statement = Statement.objects.get(id=statement_id)
        except Statement.DoesNotExist:
            return Response({"statement": _("Invalid statement.")}, status=404)

        if not _owns_statement(request.user, statement):
            return Response(
                {"detail": _("Bu statement sizning bo'limingizga tegishli emas.")},
                status=403,
            )

        lang = request.query_params.get("lang", "uz")

        try:
            wb = build_plan_template(statement, lang=lang)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="plan_template_{statement.id}.xlsx"'
        wb.save(response)
        return response


# =============================================================================
# PLAN EXCEL IMPORT — faylni yuklab, Plan yaratish yoki yangilash
# =============================================================================
@extend_schema(
    tags=["Plan"],
    parameters=[
        OpenApiParameter("organization", OpenApiTypes.UUID, required=True, location=OpenApiParameter.QUERY),
        OpenApiParameter("statement", OpenApiTypes.UUID, required=True, location=OpenApiParameter.QUERY),
        OpenApiParameter("year", OpenApiTypes.INT, required=True, location=OpenApiParameter.QUERY),
        OpenApiParameter("season", OpenApiTypes.STR, required=False, location=OpenApiParameter.QUERY),
    ],
    request={
        "multipart/form-data": inline_serializer(
            name="PlanExcelImportRequest",
            fields={
                "file": serializers.FileField(
                    help_text="Shablon asosida to'ldirilgan .xlsx fayl",
                ),
            },
        ),
    },
)
class PlanExcelImportAPIView(APIView):
    """
    POST /plan-excel/import/?organization=<uuid>&statement=<uuid>&year=2026&season=spring
    Body: multipart/form-data, file=<shablon asosida to'ldirilgan .xlsx>

    - Shu (organization, statement, year, season) uchun Plan mavjud bo'lmasa -> yaratiladi.
    - Mavjud bo'lsa -> mavjud PlanItem/PlantPlanItem qiymatlari import qilingan
      qiymatlar bilan yangilanadi (PATCH semantikasi, PlanSerializer.update orqali).

    Barcha hisoblash (oylik -> choraklik -> yillik -> yillik_total, yoki
    YILLIK_1+YILLIK_2 -> YILLIK_3) mavjud PlanSerializer._save_plan_items /
    _save_plant_plan ichida bo'ladi — bu yerda qayta yozilmaydi.

    Faqat bo'lim adminlari va faqat o'z bo'limiga tegishli statement uchun.
    """
    permission_classes = [IsBolimAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        organization_id = request.query_params.get("organization") or request.data.get("organization")
        statement_id = request.query_params.get("statement") or request.data.get("statement")
        year = request.query_params.get("year") or request.data.get("year")
        season = request.query_params.get("season") or request.data.get("season") or None

        if file_obj is not None and file_obj.size and file_obj.size > MAX_FILE_SIZE:
            # Audit B15: openpyxl butun faylni xotiraga oladi — hajm chegarasi
            return Response({"detail": f"Fayl hajmi {MAX_FILE_SIZE // (1024 * 1024)} MB dan oshmasligi kerak."},
                            status=status.HTTP_400_BAD_REQUEST)

        missing = [
            name for name, val in (
                ("file", file_obj),
                ("organization", organization_id),
                ("statement", statement_id),
                ("year", year),
            ) if not val
        ]
        if missing:
            return Response(
                {name: _("This field is required.") for name in missing},
                status=400,
            )

        try:
            statement = Statement.objects.get(id=statement_id)
        except Statement.DoesNotExist:
            return Response({"statement": _("Invalid statement.")}, status=404)

        if not _owns_statement(request.user, statement):
            return Response(
                {"detail": _("Bu statement sizning bo'limingizga tegishli emas.")},
                status=403,
            )

        try:
            payload = parse_plan_excel(file_obj, statement)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        data = {
            "organization": organization_id,
            "statement": statement_id,
            "year": year,
            **payload,
        }
        if season:
            data["season"] = season

        existing_plan = Plan.objects.filter(
            organization_id=organization_id,
            statement_id=statement_id,
            year=year,
            season=season,
        ).first()

        if existing_plan:
            serializer = PlanSerializer(
                existing_plan, data=data, partial=True,
                context={"request": request, "lang": request.query_params.get("lang", "uz")},
            )
        else:
            serializer = PlanSerializer(
                data=data,
                context={"request": request, "lang": request.query_params.get("lang", "uz")},
            )

        serializer.is_valid(raise_exception=True)
        plan = serializer.save()

        output = PlanSerializer(
            plan, context={"request": request, "lang": request.query_params.get("lang", "uz")}
        )
        return Response(
            output.data,
            status=status.HTTP_200_OK if existing_plan else status.HTTP_201_CREATED,
        )


# =============================================================================
# PLAN EXCEL EXPORT — yaratilgan rejani to'ldirilgan .xlsx sifatida yuklab olish
# =============================================================================
@extend_schema(
    tags=["Plan"],
    parameters=[
        OpenApiParameter("plan", OpenApiTypes.UUID, required=True, location=OpenApiParameter.QUERY,
                          description="Eksport qilinadigan Plan (reja) ID'si"),
        OpenApiParameter("lang", OpenApiTypes.STR, required=False, enum=["uz", "ru"],
                          location=OpenApiParameter.QUERY),
    ],
)
class PlanExcelExportAPIView(APIView):
    """
    GET /plan-excel/export/?plan=<uuid>&lang=uz

    Bo'lim admin faqat O'ZIGA tegishli (plan.statement.parent === user.statement)
    rejani Excel formatda yuklab oladi. Import shabloniga mos ustunlar, lekin
    kiritilgan qiymatlar bilan to'ldirilgan holda.
    """
    permission_classes = [IsBolimAdmin]

    def get(self, request):
        plan_id = request.query_params.get("plan")
        if not plan_id:
            return Response({"plan": _("This field is required.")}, status=400)

        plan = (
            Plan.objects
            .select_related("statement", "organization")
            .filter(id=plan_id)
            .first()
        )
        if not plan:
            return Response({"plan": _("Invalid plan.")}, status=404)

        if not _owns_statement(request.user, plan.statement):
            return Response(
                {"detail": _("Bu reja sizning bo'limingizga tegishli emas.")},
                status=403,
            )

        lang = request.query_params.get("lang", "uz")

        try:
            wb = build_plan_export(plan, lang=lang)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="plan_{plan.id}.xlsx"'
        wb.save(response)
        return response
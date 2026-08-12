# apps/reports/views/plan_excel.py
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.reports.models import Statement, Plan
from apps.reports.serializers.plan import PlanSerializer
from apps.reports.services.plan_excel import build_plan_template, parse_plan_excel
from apps.reports.permissions import CanCreatePlan, CanManagePlan
from apps.base.exceptions.exception_files import CustomExceptionError


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
    """
    permission_classes = [CanCreatePlan]

    def get(self, request):
        statement_id = request.query_params.get("statement")
        if not statement_id:
            return Response({"statement": _("This field is required.")}, status=400)

        try:
            statement = Statement.objects.get(id=statement_id)
        except Statement.DoesNotExist:
            return Response({"statement": _("Invalid statement.")}, status=404)

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
    """
    permission_classes = [CanCreatePlan, CanManagePlan]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        organization_id = request.query_params.get("organization") or request.data.get("organization")
        statement_id = request.query_params.get("statement") or request.data.get("statement")
        year = request.query_params.get("year") or request.data.get("year")
        season = request.query_params.get("season") or request.data.get("season") or None

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
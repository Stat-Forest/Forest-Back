# apps/reports/views/imports/import_excel.py
"""
Hisobot "Amalda" qiymatlarini Excel fayldan import qilish uchun
ikki endpoint:

1. ImportTemplateDownloadAPIView  — shablon yuklab olish
2. ImportParseAPIView             — faylni parse qilib JSON qaytarish

DB ga hech narsa yozilmaydi — barcha business logika
service layer da (reports/services/report_import/).
"""

import os
from io import BytesIO

from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers

from apps.reports.models import Plan, Statement
from apps.reports.services.report_import.template_generator import build_import_template
from apps.reports.services.report_import.parser import parse_import_excel
from apps.reports.services.report_import.plan_validation import PlanMismatchError


# ── Fayl hajmi limiti (bayt) ──
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@extend_schema(
    tags=["Import-Excel"],
    parameters=[
        OpenApiParameter(
            name="statement_id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Jadval (Statement) UUID'si",
        ),
        OpenApiParameter(
            name="lang",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Til: uz yoki ru",
            enum=["uz", "ru"],
        ),
    ],
    responses={200: None, 400: dict, 404: dict},
    description="Import uchun Excel shablon yuklab olish",
)
class ImportTemplateDownloadAPIView(APIView):
    """
    GET /api/v1/reports/import-template/

    Berilgan statement uchun bo'sh import shablonini (.xlsx) qaytaradi.
    Faqat Amalda ustunlar shablonga kiritiladi.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        statement_id = request.query_params.get("statement_id")
        lang = request.query_params.get("lang", "uz").lower()
        if lang not in ("uz", "ru"):
            lang = "uz"

        if not statement_id:
            return Response(
                {"detail": "statement_id query parametri majburiy."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            statement = Statement.objects.get(
                id=statement_id,
                parent__isnull=False,  # faqat child statement
            )
        except Statement.DoesNotExist:
            return Response(
                {"detail": "Statement topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            wb = build_import_template(statement, lang=lang)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Workbook ni xotiradan response ga yozamiz
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        statement_name = getattr(statement, f"name_{lang}", statement.name) or statement.name
        # Nazorat belgilari (\n, \r, \t va h.k.) ham olib tashlanadi — aks
        # holda Content-Disposition header qurishda Django BadHeaderError
        # bilan yiqiladi (statement nomida tasodifan yangi qator bo'lsa).
        safe_name = "".join(
            c if c not in '<>:"/\\|?*' and c.isprintable() else "_"
            for c in statement_name
        ).strip().replace(" ", "_")
        safe_name = safe_name or "statement"
        filename = f"{safe_name}_import_shablon.xlsx"

        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


def _organization_allowed(user, organization_id) -> bool:
    """
    Foydalanuvchi shu tashkilot rejasini ko'ra oladimi (audit N8): tashkilotga
    biriktirilgan foydalanuvchi — faqat o'z tashkiloti; hududiy — o'z viloyati
    tashkilotlari; qolganlar (super_admin, rahbariyat, bo'lim admini) — hammasi.
    """
    if user.is_superuser or user.role in ("super_admin", "rahbariyat", "bolim_admin"):
        return True
    if user.role == "hududiy_boshqarma":
        return user.region_user_orgs.filter(id=organization_id).exists()
    if user.organization_id:
        return str(user.organization_id) == str(organization_id)
    return True


class ImportParseSerializer(serializers.Serializer):
    file = serializers.FileField(help_text=".xlsx fayl")
    statement_id = serializers.UUIDField(help_text="Jadval (Statement) UUID'si")
    organization_id = serializers.UUIDField(
        required=False,
        help_text=(
            "Tashkilot UUID'si. Berilmasa Reja validatsiyasi o'tkazib yuboriladi. "
            "Faylda Reja (status_plan) ustunlariga qiymat topilsa, aynan shu "
            "tashkilot uchun bo'lim_admin tasdiqlagan Plan/PlanItem qiymati "
            "bilan solishtiriladi."
        ),
    )
    year = serializers.IntegerField(
        required=False,
        help_text="Hisobot yili — Reja (Plan) shu yil bo'yicha qidiriladi. Berilmasa Reja validatsiyasi o'tkazib yuboriladi.",
    )
    season = serializers.ChoiceField(
        choices=Plan.SeasonChoices.choices,
        required=False,
        allow_blank=True,
        help_text="Mavsum (bahorgi/kuzgi) — faqat shunga bog'liq statement'lar uchun.",
    )
    sheet_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="O'qiladigan sheet nomi (bo'sh bo'lsa active sheet)",
    )
    lang = serializers.ChoiceField(
        choices=[("uz", "uz"), ("ru", "ru")],
        default="uz",
        required=False,
        help_text="Til: uz yoki ru",
    )


@extend_schema(
    tags=["Import-Excel"],
    request=ImportParseSerializer,
    responses={
        200: dict,
        400: dict,
        404: dict,
    },
    description=(
        "Excel faylni parse qilib, Amalda ustunlar uchun "
        "{column, value} juftliklarini JSON sifatida qaytaradi. "
        "DB ga hech narsa yozilmaydi."
    ),
)
class ImportParseAPIView(GenericAPIView):
    """
    POST /api/v1/reports/import-parse/

    Yuklangan .xlsx faylni parse qilib, frontend uchun
    strukturalangan payload qaytaradi.

    Frontend bu payload bilan formdagi Amalda maydonlarini to'ldiradi.
    Foydalanuvchi ko'rib chiqib, keyin mavjud create/update flow
    orqali yuboradi.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ImportParseSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # ── Parametrlarni olish ──
        uploaded_file = serializer.validated_data.get("file")
        statement_id = serializer.validated_data.get("statement_id")
        organization_id = serializer.validated_data.get("organization_id")
        # Reja solishtiruvi faqat o'z doirasidagi tashkilot uchun — aks holda boshqa
        # tashkilotning tasdiqlangan reja qiymatlari xato matnida oshkor bo'lardi (audit N8)
        if organization_id and not _organization_allowed(request.user, organization_id):
            return Response(
                {"detail": "Bu tashkilot uchun ruxsat yo'q."},
                status=status.HTTP_403_FORBIDDEN,
            )
        year = serializer.validated_data.get("year")
        season = serializer.validated_data.get("season") or None
        sheet_name = serializer.validated_data.get("sheet_name") or None
        lang = serializer.validated_data.get("lang")

        # Fayl kengaytmasi
        file_ext = os.path.splitext(uploaded_file.name or "")[1].lower()
        if file_ext != ".xlsx":
            return Response(
                {"detail": "Faqat .xlsx formatdagi fayllar qabul qilinadi."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fayl hajmi
        if uploaded_file.size and uploaded_file.size > MAX_FILE_SIZE:
            max_mb = MAX_FILE_SIZE // (1024 * 1024)
            return Response(
                {"detail": f"Fayl hajmi {max_mb} MB dan oshmasligi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Statement
        try:
            statement = Statement.objects.get(
                id=statement_id,
                parent__isnull=False,
            )
        except Statement.DoesNotExist:
            return Response(
                {"detail": "Statement topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Parse (+ topilsa, Reja ustunlarini tasdiqlangan Plan bilan
        # solishtirish — apps/reports/services/report_import/plan_validation.py) ──
        try:
            result = parse_import_excel(
                file_obj=uploaded_file,
                statement=statement,
                sheet_name=sheet_name,
                lang=lang,
                organization=organization_id,
                year=year,
                season=season,
            )
        except PlanMismatchError as exc:
            return Response(
                {"status": "error", "detail": str(exc), "items": [], "errors": exc.issues},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response(
                {"status": "error", "detail": str(exc), "items": [], "errors": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_200_OK)

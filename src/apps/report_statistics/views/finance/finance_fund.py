from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.utils import translation
from django.db.models import Prefetch, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from apps.utils.services import RegionChoices
from apps.reports.models import ReportItem, Report, ReportItemInner, StatementColumn
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

# "Jami tushum" childlarining ordering'lari
ORDERINGS = [
    "1.1.3.1",  # Ruxsatnoma olish uchun arizalarni... - Jami tushum
    "1.1.4.1",  # Hayvonot va o'simlik dunyosiga... - Jami tushum
    "1.1.5.1",  # Ruxsat etilgan hududlarda chorva boqish... - Jami tushum
    "1.1.6.1",  # O'rmon fondi yerlaridagi bog'lar... - Jami tushum
    "1.1.7.1",  # O'rmon xo'jaligida yog'och kesishdan... - Jami tushum
    "1.1.8.1",  # Boshqa daromadlar - Jami tushum
]

FIELD_NAMES = {
    "uz": {
        "region": "hudud",
        "jamgarma": "Jamg'arma",
    },
    "ru": {
        "region": "регион",
        "jamgarma": "Фонд",
    },
}


@extend_schema(
    summary="Jamg'arma",
    description="Orderings va ORM orqali jami tushumlarni hisoblaydi",
    tags=["Statistics"],
    parameters=[
        OpenApiParameter(
            name="lang",
            description="Til parametri: uz (default) yoki ru",
            required=False,
            type=OpenApiTypes.STR,
            enum=["uz", "ru"],
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="deadline",
            description="Deadline UUID bo'yicha filter",
            required=False,
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
        )
    ],
)
class StatisticsFinanceFundAPIView(APIView):

    def safe_decimal_convert(self, value):
        """
        Qiymatni xavfsiz ravishda Decimal ga aylantirish
        """
        if value is None or value == '':
            return Decimal('0')

        try:
            # Agar string bo'lsa, vergulni nuqtaga almashtirish
            if isinstance(value, str):
                value = value.strip().replace(',', '.')
                # Bo'sh string yoki faqat bo'shliqlarni tekshirish
                if not value:
                    return Decimal('0')

            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as e:
            print(f"⚠️ Qiymatni konvertatsiya qilishda xatolik: {value} -> {e}")
            return Decimal('0')

    def aggregate_by_ordering(self, orderings, deadline_id=None, lang='uz'):
        """
        Ordering bo'yicha ma'lumotlarni aggregatsiya qilish
        """
        # Base filter
        filters = {
            "statement_column__ordering__in": orderings,
            "report__is_report": True,
        }

        # Status filter - saved, sent, accepted
        status_filter = Q(report__status=Report.StatusChoices.SAVED) | \
                        Q(report__status=Report.StatusChoices.SENT) | \
                        Q(report__status=Report.StatusChoices.ACCEPTED)

        if deadline_id:
            filters["report__deadline_id"] = deadline_id

        # Query with optimization
        qs = ReportItem.objects.filter(
            **filters
        ).filter(
            status_filter
        ).select_related(
            "report",
            "report__organization",
            "statement_column",
            "statement_column__parent"
        ).prefetch_related(
            Prefetch(
                'inners',
                queryset=ReportItemInner.objects.all()
            )
        )

        print(f"\n{'=' * 80}")
        print(f"🔍 AGREGATSIYA BOSHLANDI")
        print(f"{'=' * 80}")
        print(f"📌 Deadline ID: {deadline_id}")
        print(f"📌 Orderings: {orderings}")
        print(f"📌 Topilgan ReportItem'lar soni: {qs.count()}")

        # Debug: Show all found items
        for item in qs:
            print(f"\n🔹 ReportItem ID: {item.id}")
            print(f"   └─ Report ID: {item.report.id}")
            print(f"   └─ Organization: {item.report.organization.name_uz}")
            print(f"   └─ Region: {item.report.organization.region}")
            print(f"   └─ Column Ordering: {item.statement_column.ordering}")
            print(f"   └─ Status: {item.report.status}")

            inners = list(item.inners.all())
            print(f"   └─ Inners count: {len(inners)}")
            for inner in inners:
                print(f"      └─ Inner value: '{inner.value}'")

        # Region va column bo'yicha summalash
        grouped = defaultdict(lambda: Decimal('0'))

        for item in qs:
            try:
                region = item.report.organization.region

                # Parent title ni tilga qarab olish
                if item.statement_column.parent:
                    parent_title = getattr(
                        item.statement_column.parent,
                        f'title_{lang}',
                        item.statement_column.parent.title_uz
                    )
                else:
                    parent_title = ""

                column_name = f"{parent_title} - Jami tushum"

                # item.inners ichidagi barcha value larni yig'ish
                inners_list = list(item.inners.all())

                if not inners_list:
                    print(f"⚠️ Item {item.id} uchun inners topilmadi")
                    continue

                total = Decimal('0')
                for inner in inners_list:
                    value = self.safe_decimal_convert(inner.value)
                    total += value

                    # Debug uchun
                    print(f"\n✅ QIYMAT TOPILDI:")
                    print(f"   └─ Region: {region}")
                    print(f"   └─ Column: {column_name}")
                    print(f"   └─ Original Value: '{inner.value}'")
                    print(f"   └─ Converted Value: {value}")
                    print(f"   └─ Running Total: {total}")

                grouped[(region, column_name)] += total

                print(f"\n💰 JAMLANAYOTGAN QIYMAT:")
                print(f"   └─ Key: ({region}, {column_name})")
                print(f"   └─ Total for this item: {total}")
                print(f"   └─ Cumulative total: {grouped[(region, column_name)]}")

            except Exception as e:
                print(f"❌ XATOLIK item {item.id} da: {e}")
                import traceback
                traceback.print_exc()
                continue

        print(f"\n{'=' * 80}")
        print(f"📊 YAKUNIY GROUPED MA'LUMOTLAR:")
        print(f"{'=' * 80}")
        for key, value in grouped.items():
            print(f"   {key}: {value}")
        print(f"{'=' * 80}\n")

        return grouped

    def get_column_names_from_db(self, orderings, lang='uz'):
        """
        Database'dan parent title'larni tilga qarab olish
        """
        columns = StatementColumn.objects.filter(
            ordering__in=orderings
        ).select_related('parent')

        print(f"\n📋 COLUMN NAMES MAPPING:")
        column_names = {}
        for column in columns:
            if column.parent:
                parent_title = getattr(
                    column.parent,
                    f'title_{lang}',
                    column.parent.title_uz
                )
            else:
                parent_title = ""

            column_name = f"{parent_title} - Jami tushum"
            column_names[column.ordering] = column_name
            print(f"   {column.ordering} -> {column_name}")

        return column_names

    def get(self, request):
        lang = request.query_params.get("lang", "uz")
        deadline_id = request.query_params.get("deadline")

        print(f"\n{'#' * 80}")
        print(f"🚀 API SO'ROV BOSHLANDI")
        print(f"{'#' * 80}")
        print(f"📍 Lang: {lang}")
        print(f"📍 Deadline ID: {deadline_id}")
        print(f"{'#' * 80}\n")

        translation.activate(lang)
        field_names = FIELD_NAMES[lang]

        # Ma'lumotlarni aggregatsiya qilish
        grouped = self.aggregate_by_ordering(ORDERINGS, deadline_id, lang)

        # Database'dan column nomlarini olish
        column_names_map = self.get_column_names_from_db(ORDERINGS, lang)

        # Natijani region bo'yicha to'g'ri tuzish
        data = []
        print(f"\n📊 NATIJALARNI FORMATLASH:")
        for region_key, region_label in RegionChoices.choices:
            row = {field_names["region"]: str(region_label)}

            print(f"\n🏛️ Region: {region_label} ({region_key})")

            # Har bir ordering uchun column nomini database'dan olamiz
            for ordering in ORDERINGS:
                column_name = column_names_map.get(ordering, "Unknown - Jami tushum")
                value = grouped.get((region_key, column_name), Decimal('0'))

                # Decimal ni float ga aylantirish (JSON serialization uchun)
                row[column_name] = float(value)

                if value > 0:
                    print(f"   ✓ {column_name}: {float(value)}")

            data.append(row)

        print(f"\n{'#' * 80}")
        print(f"✅ API SO'ROV YAKUNLANDI")
        print(f"{'#' * 80}\n")

        return Response({field_names["jamgarma"]: data}, status=HTTP_200_OK)
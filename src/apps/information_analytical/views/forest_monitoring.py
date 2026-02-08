import time
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from django.db import connection
from django.core.cache import cache
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.general.models import Organization
from apps.information_analytical.serializers.aggregation import aggregate_target_maps
from apps.reports.models import Statement, StatementColumn, Report
from apps.information_analytical.mapping import MAPPING_RULES, FORMULA_BLOCKS
from apps.information_analytical.services.plan_loader import load_plan_maps
from apps.reports.services.get_two_numbers_in_percent import round_decimal
from apps.utils.translation import get_lang_code
from apps.utils.services import RegionChoices


class ForestMonitoringAPIView(APIView):
    permission_classes = [IsAuthenticated]

    # =========================================================
    # HELPER FUNCTIONS
    # =========================================================

    def is_numeric_string(self, value):
        """String numeric ekanligini tekshirish"""
        if not value or not isinstance(value, str):
            return False

        if value.strip() == "":
            return False

        cleaned = value.replace(',', '.').replace(' ', '')

        if cleaned.count('.') > 1:
            return False

        if cleaned.replace('.', '', 1).replace('-', '', 1).isdigit():
            return True

        return False

    def safe_decimal(self, value):
        """Xavfsiz Decimal konvertatsiya"""
        if value in (None, "", " "):
            return Decimal('0')

        try:
            if isinstance(value, str):
                if not self.is_numeric_string(value):
                    return Decimal('0')
                value = value.replace(',', '.')

            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal('0')

    # =========================================================
    # STATEMENT & COLUMNS
    # =========================================================

    def get_target_statement(self):
        """Target statement - cached"""
        cache_key = "forest_monitoring_target_statement"
        stmt = cache.get(cache_key)
        if not stmt:
            stmt = Statement.objects.only("id", "name_uz").get(
                name_uz="O'rmonlar kesimida"
            )
            cache.set(cache_key, stmt, 3600)
        return stmt

    def get_all_columns_data(self, statement_id):
        """Barcha column ma'lumotlari - cached"""
        cache_key = f"forest_monitoring_columns_{statement_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        cols = list(
            StatementColumn.objects.filter(statement_id=statement_id).only(
                "id", "ordering", "title", "title_uz", "title_ru",
                "parent_id", "is_organization"
            )
        )

        children = defaultdict(list)
        for c in cols:
            if c.parent_id:
                children[str(c.parent_id)].append(c.id)

        data = {
            "columns": cols,
            "columns_by_id": {str(c.id): c for c in cols},
            "children_dict": dict(children),
        }

        cache.set(cache_key, data, 3600)
        return data

    def get_title(self, col, lang):
        """Column title olish - no queries"""
        if not col:
            return ""
        if lang == "uz":
            return col.title_uz or col.title
        if lang == "ru":
            return col.title_ru or col.title_uz or col.title
        return col.title

    def build_tree_no_queries(self, data, lang):
        """Tree qurish - no database queries"""
        cols = data["columns"]

        by_parent = defaultdict(list)
        for c in cols:
            if not c.is_organization:
                by_parent[str(c.parent_id) if c.parent_id else None].append(c)

        for parent_id in by_parent:
            by_parent[parent_id].sort(
                key=lambda x: [int(n) for n in x.ordering.split(".") if n.isdigit()]
            )

        leaf_paths = {}

        def build_node(parent_id, current_path):
            result = {}
            for col in by_parent.get(parent_id, []):
                title = self.get_title(col, lang)
                new_path = current_path + [title]

                if str(col.id) in data["children_dict"]:
                    result[title] = build_node(str(col.id), new_path)
                else:
                    result[title] = ""
                    leaf_paths[col.ordering] = new_path

            return result

        skeleton = build_node(None, [])
        return skeleton, leaf_paths

    # =========================================================
    # MATERIALIZE FUNCTION
    # =========================================================

    def materialize_result_from_value_map(self, skeleton, leaf_paths, value_map):
        """
        skeleton: nested dict (titles)
        leaf_paths: ordering -> path_titles
        value_map: ordering -> value

        ✅ Har doim shunday chaqirilsin:
        materialize_result_from_value_map(
            skeleton=skeleton,
            leaf_paths=leaf_paths,
            value_map=target_value_map
        )
        """
        import copy
        result = copy.deepcopy(skeleton)

        # Faqat bo'sh bo'lmagan qiymatlarni qo'shish
        for ordering, path in leaf_paths.items():
            val = value_map.get(ordering)
            if val is not None and val != "":
                self._set_by_path(result, path, val)

        return result

    def _set_by_path(self, root: dict, path: list[str], value):
        """Path bo'yicha nested dict ga qiymat qo'yish"""
        cur = root
        for key in path[:-1]:
            if key not in cur:
                cur[key] = {}
            cur = cur[key]
        cur[path[-1]] = "" if value is None else value

    # =========================================================
    # REPORT DATA FETCHING
    # =========================================================

    def get_latest_report_ids_raw(self, org_ids, stmt_ids):
        """Eng oxirgi report ID larini olish"""
        if not org_ids or not stmt_ids:
            return []

        sql = """
              SELECT DISTINCT \
              ON (organization_id, statement_id) id
              FROM reports_report
              WHERE organization_id = ANY (%s)
                AND statement_id = ANY (%s)
                AND status = 'accepted'
              ORDER BY organization_id, statement_id, created_at DESC
              """

        with connection.cursor() as cursor:
            cursor.execute(sql, [org_ids, stmt_ids])
            return [row[0] for row in cursor.fetchall()]

    def get_report_values(self, report_ids):
        """ReportItem va ReportItemInner ma'lumotlarini olish"""
        if not report_ids:
            return {}

        sql_numeric_items = """
                            SELECT ri.report_id, sc.ordering, ri.value
                            FROM reports_reportitem ri
                                     JOIN reports_statementcolumn sc ON sc.id = ri.statement_column_id
                            WHERE ri.report_id = ANY (%s)
                              AND ri.value IS NOT NULL
                              AND ri.value != ''
                              AND ri.value ~ '^[-+]?[0-9]*[.,]?[0-9]+$'
                              AND NOT EXISTS (
                                  SELECT 1 FROM reports_reportiteminner rii
                                  WHERE rii.report_item_id = ri.id
                              )
                            """

        sql_inner_items = """
                          SELECT ri.report_id, \
                                 sc.ordering,
                                 SUM(CASE
                                         WHEN rii.value ~ '^[-+]?[0-9]*[.,]?[0-9]+$'
                                     THEN CAST(replace(rii.value, ',', '.') AS DECIMAL)
                                         ELSE 0
                                     END) as total_value
                          FROM reports_reportitem ri
                                   JOIN reports_statementcolumn sc ON sc.id = ri.statement_column_id
                                   JOIN reports_reportiteminner rii ON rii.report_item_id = ri.id
                          WHERE ri.report_id = ANY (%s)
                          GROUP BY ri.report_id, sc.ordering
                          """

        result = defaultdict(dict)

        with connection.cursor() as cursor:
            cursor.execute(sql_numeric_items, [report_ids])
            for report_id, ordering, value in cursor.fetchall():
                if value:
                    try:
                        dec_value = self.safe_decimal(value)
                        if dec_value != Decimal('0'):
                            result[report_id][ordering] = str(dec_value)
                    except:
                        pass

            cursor.execute(sql_inner_items, [report_ids])
            for report_id, ordering, total_value in cursor.fetchall():
                if total_value is not None:
                    try:
                        dec_value = Decimal(str(total_value))
                        if dec_value != Decimal('0'):
                            existing = result[report_id].get(ordering)
                            if existing:
                                existing_dec = self.safe_decimal(existing)
                                total_dec = existing_dec + dec_value
                                result[report_id][ordering] = str(total_dec)
                            else:
                                result[report_id][ordering] = str(dec_value)
                    except:
                        pass

        return dict(result)

    # =========================================================
    # MAIN METHOD WITH PLAN PRIORITY LOGIC
    # =========================================================

    @extend_schema(
        summary="Forest monitoring – analytical aggregation",
        description="""
        Region va organization bo‘yicha o‘rmon monitoring ma’lumotlarini chiqaradi.

        📌 Agar region berilsa → faqat shu hudud va uning tashkilotlari chiqadi -> not yet :) 
        📌 Agar organization berilsa → faqat respublika i viloyat i o`sha organization ni chiqaradi  
        📌 Agar hech nima berilmasa → Respublika → Regionlar → Tashkilotlar chiqadi
        """,
        parameters=[
            # OpenApiParameter(
            #     name="region",
            #     type=OpenApiTypes.STR,
            #     location=OpenApiParameter.QUERY,
            #     required=False,
            #     description="Region kodi (masalan: ANDIJON, SAMARQAND, TOSHKENT)"
            # ),
            OpenApiParameter(
                name="organization",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Organization ID bo‘yicha filter"
            ),
            OpenApiParameter(
                name="lang",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Til (uz yoki ru)"
            ),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        """Asosiy GET endpoint - PLAN PRIORITY LOGIC bilan"""
        start_time = time.time()
        lang = get_lang_code(request)

        print(f"\n{'=' * 60}")
        print(f"🚀 ForestMonitoringAPIView STARTED (PLAN PRIORITY)")
        print(f"{'=' * 60}")

        connection.queries_log.clear()

        # 1. Target statement va columns
        print(f"[1/9] Loading target statement and columns...")
        try:
            target_statement = self.get_target_statement()
            columns_data = self.get_all_columns_data(target_statement.id)
            skeleton, leaf_paths = self.build_tree_no_queries(columns_data, lang)
        except Exception as e:
            print(f"Error loading statement/columns: {e}")
            return self._build_empty_response(lang, {})

        # 2. Organizations
        print(f"[2/9] Loading organizations...")
        try:
            org_qs = Organization.objects.only(
                "id", "region", "name", "name_uz", "name_ru"
            )

            # 🔍 Query params
            region_filter = request.query_params.get("region")
            organization_filter = request.query_params.get("organization")

            # 🗺 Region bo‘yicha filter
            if region_filter:
                org_qs = org_qs.filter(region=region_filter)

            # 🏢 Organization bo‘yicha filter
            if organization_filter:
                org_qs = org_qs.filter(id=organization_filter)

            organizations = list(org_qs)

        except Exception as e:
            print(f"Error loading organizations: {e}")
            return self._build_empty_response(lang, skeleton)

        if not organizations:
            print("No organizations found after filters, returning empty response")
            return self._build_empty_response(lang, skeleton)

        # 🚀 IDs — tezkor ishlash uchun
        org_ids = [o.id for o in organizations]

        print(f"   Found {len(organizations)} organizations (after filters)")

        # 3. Source statements
        print(f"[3/9] Loading source statements...")
        try:
            source_statement_names = {r["source_statement_name_uz"] for r in MAPPING_RULES}
            source_statements = list(
                Statement.objects.filter(name_uz__in=source_statement_names).only("id", "name_uz")
            )
            statement_by_name = {s.name_uz: s.id for s in source_statements}
            statement_ids = list(statement_by_name.values())
            print(f"   Found {len(source_statements)} source statements")
        except Exception as e:
            print(f"Error loading source statements: {e}")
            statement_by_name = {}
            statement_ids = []

        if not statement_ids:
            print("No source statements found, returning empty response")
            return self._build_empty_response(lang, skeleton)

        # 4. Latest report IDs
        print(f"[4/9] Finding latest reports...")
        try:
            latest_report_ids = self.get_latest_report_ids_raw(org_ids, statement_ids)
        except Exception as e:
            print(f"Error finding latest reports: {e}")
            latest_report_ids = []

        if not latest_report_ids:
            print("No latest reports found, returning empty response")
            return self._build_empty_response(lang, skeleton)

        print(f"   Found {len(latest_report_ids)} latest reports")

        # 5. Reports basic info
        print(f"[5/9] Loading reports basic info...")
        try:
            reports = list(
                Report.objects.filter(id__in=latest_report_ids).only(
                    "id", "organization_id", "statement_id"
                )
            )
        except Exception as e:
            print(f"Error loading reports: {e}")
            reports = []

        report_map = {}
        for report in reports:
            key = (report.organization_id, report.statement_id)
            report_map[key] = report.id

        print(f"   Mapped {len(report_map)} reports")

        # 6. ✅ YANGI: PLAN DATA ni load_plan_maps orqali yuklash
        print(f"[6/9] Loading plan maps (Plan → PlantPlan priority)...")
        plan_map = {}
        plant_plan_map = {}
        try:
            plan_map, plant_plan_map = load_plan_maps(org_ids, statement_ids)
            print(f"   Plan map entries: {len(plan_map)}")
            print(f"   Plant plan map entries: {len(plant_plan_map)}")
        except Exception as e:
            print(f"Error loading plan maps: {e}")

        # 7. Report values
        print(f"[7/9] Loading report values...")
        report_values = {}
        try:
            report_values = self.get_report_values(latest_report_ids)
        except Exception as e:
            print(f"Error loading report values: {e}")

        # 8. Group organizations by region
        region_map = defaultdict(list)
        for org in organizations:
            region_map[org.region].append(org)

        print(f"   Grouped into {len(region_map)} regions")

        # 9. Build response with PLAN PRIORITY LOGIC
        print(f"[8/9] Building response with PLAN PRIORITY LOGIC...")
        regions_payload = []
        republic_maps = []
        org_counter = 0

        for region_code, orgs in region_map.items():
            region_name = dict(RegionChoices.choices).get(region_code, region_code)

            org_nodes = []
            region_target_maps = []

            for org in orgs:
                org_counter += 1
                target_value_map = {}

                # ✅ YANGI: MAPPING_RULES uchun PLAN PRIORITY LOGIC
                for rule in MAPPING_RULES:
                    statement_id = statement_by_name.get(rule["source_statement_name_uz"])
                    if not statement_id:
                        target_value_map[rule["target"]] = ""
                        continue

                    ordering = rule["source"]
                    key = (org.id, statement_id)

                    # ✅ 1️⃣ PRIORITY: ODDIY PLAN (Plan map)
                    # Agar Plan bo'lsa → doim Plan ishlaydi
                    if key in plan_map and ordering in plan_map[key]:
                        target_value_map[rule["target"]] = plan_map[key][ordering]
                        continue

                    # ✅ 2️⃣ PRIORITY: PLANT PLAN (har bir plant bo'yicha yig'indisi)
                    # Agar Plan bo'lmasa → PlantPlan yig'indisi
                    if key in plant_plan_map:
                        # Barcha plant qiymatlarini yig'ish
                        total_plant_value = Decimal('0')
                        plant_values_found = False

                        for plant_id in plant_plan_map[key]:
                            if ordering in plant_plan_map[key][plant_id]:
                                try:
                                    plant_val = self.safe_decimal(plant_plan_map[key][plant_id][ordering])
                                    total_plant_value += plant_val
                                    plant_values_found = True
                                except:
                                    pass

                        if plant_values_found and total_plant_value != Decimal('0'):
                            target_value_map[rule["target"]] = str(total_plant_value)
                            continue

                    # ✅ 3️⃣ PRIORITY: REPORT VALUE
                    # Agar ikkalasi bo'lmasa → Report value
                    report_id = report_map.get(key)
                    if report_id and ordering in report_values.get(report_id, {}):
                        target_value_map[rule["target"]] = report_values[report_id][ordering]
                    else:
                        target_value_map[rule["target"]] = ""

                # ✅ FORMULA BLOCKS ni qo'llash (faqat Reja va Amalda uchun)
                # % va (+,-) HECH QACHON yig'ilmasin — faqat qayta hisoblanadi
                for reja_ordering, amalda_ordering, percent_ordering, diff_ordering in FORMULA_BLOCKS:
                    reja_value = target_value_map.get(reja_ordering, "")
                    amalda_value = target_value_map.get(amalda_ordering, "")

                    # ✅ Faqat Reja va Amalda qiymatlari mavjud bo'lsa hisobla
                    if reja_value and reja_value != "" and amalda_value and amalda_value != "":
                        try:
                            reja_dec = self.safe_decimal(reja_value)
                            amalda_dec = self.safe_decimal(amalda_value)

                            # % hisoblash
                            if reja_dec != Decimal('0'):
                                percent_value = round_decimal((amalda_dec / reja_dec) * Decimal('100'), 1)
                                target_value_map[percent_ordering] = str(percent_value)
                            else:
                                target_value_map[percent_ordering] = ""

                            # (+,-) hisoblash
                            diff_value = reja_dec - amalda_dec
                            target_value_map[diff_ordering] = str(diff_value)
                        except Exception as e:
                            print(f"Formula error for org {org.id}: {e}")
                            target_value_map[percent_ordering] = ""
                            target_value_map[diff_ordering] = ""
                    else:
                        target_value_map[percent_ordering] = ""
                        target_value_map[diff_ordering] = ""

                # Region aggregation uchun saqlash
                region_target_maps.append(target_value_map)

                # Organization name
                org_name = ""
                try:
                    if lang == "uz":
                        org_name = getattr(org, "name_uz", None) or org.name
                    elif lang == "ru":
                        org_name = getattr(org, "name_ru", None) or getattr(org, "name_uz", None) or org.name
                    else:
                        org_name = org.name
                except:
                    org_name = org.name

                # ✅ materialize_result_from_value_map ni chaqirish
                try:
                    org_result = self.materialize_result_from_value_map(
                        skeleton=skeleton,
                        leaf_paths=leaf_paths,
                        value_map=target_value_map
                    )
                except Exception as e:
                    print(f"Error materializing organization result: {e}")
                    org_result = skeleton

                org_nodes.append({
                    "level": "ORGANIZATION",
                    "hudud": org_name,
                    "result": org_result,
                })

            # ✅ REGION AGGREGATION (faqat Reja va Amalda)
            region_aggregated = {}
            try:
                region_aggregated = aggregate_target_maps(region_target_maps)
            except Exception as e:
                print(f"Error aggregating region {region_name}: {e}")

            # ✅ REGION uchun FORMULA BLOCKS ni qayta hisoblash
            # Aggregation faqat Reja va Amalda bo'yicha bo'lsin
            # % va (+,-) HECH QACHON yig'ilmasin — faqat qayta hisoblanadi
            for reja_ordering, amalda_ordering, percent_ordering, diff_ordering in FORMULA_BLOCKS:
                reja_value = region_aggregated.get(reja_ordering, "")
                amalda_value = region_aggregated.get(amalda_ordering, "")

                if reja_value and reja_value != "" and amalda_value and amalda_value != "":
                    try:
                        reja_dec = self.safe_decimal(reja_value)
                        amalda_dec = self.safe_decimal(amalda_value)

                        # % qayta hisoblash
                        if reja_dec != Decimal('0'):
                            percent_value = round_decimal((amalda_dec / reja_dec) * Decimal('100'), 1)
                            region_aggregated[percent_ordering] = str(percent_value)
                        else:
                            region_aggregated[percent_ordering] = ""

                        # (+,-) qayta hisoblash
                        diff_value = reja_dec - amalda_dec
                        region_aggregated[diff_ordering] = str(diff_value)
                    except Exception as e:
                        print(f"Region formula error for {region_name}: {e}")
                        region_aggregated[percent_ordering] = ""
                        region_aggregated[diff_ordering] = ""
                else:
                    region_aggregated[percent_ordering] = ""
                    region_aggregated[diff_ordering] = ""

            # Republic aggregation uchun saqlash
            republic_maps.append(region_aggregated)

            # Region result
            try:
                region_result = self.materialize_result_from_value_map(
                    skeleton=skeleton,
                    leaf_paths=leaf_paths,
                    value_map=region_aggregated
                )
            except Exception as e:
                print(f"Error materializing region result: {e}")
                region_result = skeleton

            regions_payload.append({
                "level": "REGION",
                "hudud": region_name,
                "result": region_result,
                "children": org_nodes,
            })

        # ✅ REPUBLIC AGGREGATION (faqat Reja va Amalda)
        republic_aggregated = {}
        try:
            republic_aggregated = aggregate_target_maps(republic_maps)
        except Exception as e:
            print(f"Error aggregating republic: {e}")

        # ✅ REPUBLIC uchun FORMULA BLOCKS ni qayta hisoblash
        for reja_ordering, amalda_ordering, percent_ordering, diff_ordering in FORMULA_BLOCKS:
            reja_value = republic_aggregated.get(reja_ordering, "")
            amalda_value = republic_aggregated.get(amalda_ordering, "")

            if reja_value and reja_value != "" and amalda_value and amalda_value != "":
                try:
                    reja_dec = self.safe_decimal(reja_value)
                    amalda_dec = self.safe_decimal(amalda_value)

                    # % qayta hisoblash
                    if reja_dec != Decimal('0'):
                        percent_value = round_decimal((amalda_dec / reja_dec) * Decimal('100'), 1)
                        republic_aggregated[percent_ordering] = str(percent_value)
                    else:
                        republic_aggregated[percent_ordering] = ""

                    # (+,-) qayta hisoblash
                    diff_value = reja_dec - amalda_dec
                    republic_aggregated[diff_ordering] = str(diff_value)
                except Exception as e:
                    print(f"Republic formula error: {e}")
                    republic_aggregated[percent_ordering] = ""
                    republic_aggregated[diff_ordering] = ""
            else:
                republic_aggregated[percent_ordering] = ""
                republic_aggregated[diff_ordering] = ""

        # Final response
        republic_title = "Respublika Jami" if lang == "uz" else "Республиканский итог"

        try:
            republic_result = self.materialize_result_from_value_map(
                skeleton=skeleton,
                leaf_paths=leaf_paths,
                value_map=republic_aggregated
            )
        except Exception as e:
            print(f"Error materializing republic result: {e}")
            republic_result = skeleton

        payload = {
            "level": "REPUBLIC",
            "hudud": republic_title,
            "result": republic_result,
            "children": regions_payload,
        }

        # Performance stats
        total_time = time.time() - start_time
        total_queries = len(connection.queries)

        print(f"\n{'=' * 60}")
        print(f"🎉 ForestMonitoringAPIView COMPLETED")
        print(f"{'=' * 60}")
        print(f"📊 PERFORMANCE STATS:")
        print(f"   Total time: {total_time:.3f}s")
        print(f"   Total queries: {total_queries}")
        print(f"   Organizations: {org_counter}")
        print(f"   Regions: {len(region_map)}")
        print(f"   Plan map entries: {len(plan_map)}")
        print(f"   Plant plan map entries: {len(plant_plan_map)}")
        print(f"   Response size: ~{len(str(payload)) // 1024} KB")
        print(f"{'=' * 60}")

        return Response(payload)

    def _build_empty_response(self, lang, skeleton):
        """Bo'sh response"""
        republic_title = "Respublika Jami" if lang == "uz" else "Республиканский итог"

        return Response({
            "level": "REPUBLIC",
            "hudud": republic_title,
            "result": skeleton if skeleton else {},
            "children": [],
        })
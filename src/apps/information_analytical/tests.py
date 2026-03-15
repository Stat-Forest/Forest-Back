# import time
# from collections import defaultdict
# from decimal import Decimal, InvalidOperation
#
# from django.core.cache import cache
# from django.db import connection
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
# from rest_framework.views import APIView
#
# from apps.general.models import Organization
# from apps.information_analytical.mapping import MAPPING_RULES, FORMULA_BLOCKS
# from apps.information_analytical.serializers.aggregation import aggregate_target_maps
# from apps.information_analytical.services.plan_loader import load_plan_maps
# from apps.reports.models import Statement, StatementColumn, Report
# from apps.reports.services.get_two_numbers_in_percent import round_decimal
# from apps.utils.services import RegionChoices
# from apps.utils.translation import get_lang_code
#
#
# class ForestMonitoringAPIView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     # =========================================================
#     # HELPER FUNCTIONS
#     # =========================================================
#
#     def is_numeric_string(self, value):
#         if not value or not isinstance(value, str):
#             return False
#         if value.strip() == "":
#             return False
#
#         cleaned = value.replace(",", ".").replace(" ", "")
#         if cleaned.count(".") > 1:
#             return False
#
#         # allow "-12.3"
#         return cleaned.replace(".", "", 1).replace("-", "", 1).isdigit()
#
#     def safe_decimal(self, value):
#         if value in (None, "", " "):
#             return Decimal("0")
#         try:
#             if isinstance(value, str):
#                 if not self.is_numeric_string(value):
#                     return Decimal("0")
#                 value = value.replace(",", ".")
#             return Decimal(str(value))
#         except (InvalidOperation, ValueError, TypeError):
#             return Decimal("0")
#
#     # =========================================================
#     # STATEMENT & COLUMNS
#     # =========================================================
#
#     def get_target_statement(self):
#         cache_key = "forest_monitoring_target_statement"
#         stmt = cache.get(cache_key)
#         if not stmt:
#             stmt = Statement.objects.only("id", "name_uz").get(name_uz="O'rmonlar kesimida")
#             cache.set(cache_key, stmt, 3600)
#         return stmt
#
#     def get_all_columns_data(self, statement_id):
#         cache_key = f"forest_monitoring_columns_{statement_id}"
#         cached = cache.get(cache_key)
#         if cached:
#             return cached
#
#         cols = list(
#             StatementColumn.objects.filter(statement_id=statement_id).only(
#                 "id",
#                 "ordering",
#                 "title",
#                 "title_uz",
#                 "title_ru",
#                 "parent_id",
#                 "is_organization",
#             )
#         )
#
#         children = defaultdict(list)
#         for c in cols:
#             if c.parent_id:
#                 children[str(c.parent_id)].append(c.id)
#
#         data = {
#             "columns": cols,
#             "columns_by_id": {str(c.id): c for c in cols},
#             "children_dict": dict(children),
#         }
#         cache.set(cache_key, data, 3600)
#         return data
#
#     def get_title(self, col, lang):
#         if not col:
#             return ""
#         if lang == "uz":
#             return col.title_uz or col.title
#         if lang == "ru":
#             return col.title_ru or col.title_uz or col.title
#         return col.title
#
#     def build_tree_no_queries(self, data, lang):
#         cols = data["columns"]
#
#         by_parent = defaultdict(list)
#         for c in cols:
#             if not c.is_organization:
#                 by_parent[str(c.parent_id) if c.parent_id else None].append(c)
#
#         for parent_id in by_parent:
#             by_parent[parent_id].sort(
#                 key=lambda x: [int(n) for n in x.ordering.split(".") if n.isdigit()]
#             )
#
#         leaf_paths = {}
#
#         def build_node(parent_id, current_path):
#             result = {}
#             for col in by_parent.get(parent_id, []):
#                 title = self.get_title(col, lang)
#                 new_path = current_path + [title]
#
#                 if str(col.id) in data["children_dict"]:
#                     result[title] = build_node(str(col.id), new_path)
#                 else:
#                     result[title] = ""
#                     leaf_paths[col.ordering] = new_path
#             return result
#
#         skeleton = build_node(None, [])
#         return skeleton, leaf_paths
#
#     # =========================================================
#     # MATERIALIZE FUNCTION
#     # =========================================================
#
#     def materialize_result_from_value_map(self, skeleton, leaf_paths, value_map):
#         import copy
#
#         result = copy.deepcopy(skeleton)
#
#         for ordering, path in leaf_paths.items():
#             val = value_map.get(ordering)
#             if val is not None and val != "":
#                 self._set_by_path(result, path, val)
#
#         return result
#
#     def _set_by_path(self, root: dict, path: list[str], value):
#         cur = root
#         for key in path[:-1]:
#             if key not in cur:
#                 cur[key] = {}
#             cur = cur[key]
#         cur[path[-1]] = "" if value is None else value
#
#     # =========================================================
#     # REPORT DATA FETCHING (RAW SQL)
#     # =========================================================
#
#     def get_latest_report_ids_raw(self, org_ids, stmt_ids):
#         if not org_ids or not stmt_ids:
#             return []
#
#         sql = """
#             SELECT DISTINCT ON (organization_id, statement_id) id
#             FROM reports_report
#             WHERE organization_id = ANY (%s)
#               AND statement_id = ANY (%s)
#               AND status = 'accepted'
#             ORDER BY organization_id, statement_id, created_at DESC
#         """
#
#         with connection.cursor() as cursor:
#             cursor.execute(sql, [org_ids, stmt_ids])
#             return [row[0] for row in cursor.fetchall()]
#
#     def get_report_values(self, report_ids):
#         if not report_ids:
#             return {}
#
#         sql_numeric_items = """
#             SELECT ri.report_id, sc.ordering, ri.value
#             FROM reports_reportitem ri
#             JOIN reports_statementcolumn sc ON sc.id = ri.statement_column_id
#             WHERE ri.report_id = ANY (%s)
#               AND ri.value IS NOT NULL
#               AND ri.value != ''
#               AND ri.value ~ '^[-+]?[0-9]*[.,]?[0-9]+$'
#               AND NOT EXISTS (
#                   SELECT 1 FROM reports_reportiteminner rii
#                   WHERE rii.report_item_id = ri.id
#               )
#         """
#
#         sql_inner_items = """
#             SELECT
#                 ri.report_id,
#                 sc.ordering,
#                 SUM(
#                     CASE
#                         WHEN rii.value ~ '^[-+]?[0-9]*[.,]?[0-9]+$'
#                         THEN CAST(replace(rii.value, ',', '.') AS DECIMAL)
#                         ELSE 0
#                     END
#                 ) as total_value
#             FROM reports_reportitem ri
#             JOIN reports_statementcolumn sc ON sc.id = ri.statement_column_id
#             JOIN reports_reportiteminner rii ON rii.report_item_id = ri.id
#             WHERE ri.report_id = ANY (%s)
#             GROUP BY ri.report_id, sc.ordering
#         """
#
#         result = defaultdict(dict)
#
#         with connection.cursor() as cursor:
#             cursor.execute(sql_numeric_items, [report_ids])
#             for report_id, ordering, value in cursor.fetchall():
#                 dec_value = self.safe_decimal(value)
#                 if dec_value != Decimal("0"):
#                     result[report_id][ordering] = str(dec_value)
#
#             cursor.execute(sql_inner_items, [report_ids])
#             for report_id, ordering, total_value in cursor.fetchall():
#                 if total_value is None:
#                     continue
#                 try:
#                     dec_value = Decimal(str(total_value))
#                 except Exception:
#                     continue
#
#                 if dec_value == Decimal("0"):
#                     continue
#
#                 existing = result[report_id].get(ordering)
#                 if existing:
#                     result[report_id][ordering] = str(self.safe_decimal(existing) + dec_value)
#                 else:
#                     result[report_id][ordering] = str(dec_value)
#
#         return dict(result)
#
#     # =========================================================
#     # FILTER HELPERS
#     # =========================================================
#
#     def _resolve_scope(self, *, region_filter, organization_filter):
#         """
#         Qaytaradigan scope:
#         - ORGANIZATION: organization param bor
#         - REGION: region param bor
#         - REPUBLIC: hech narsa yo'q
#         """
#         if organization_filter:
#             return "ORGANIZATION"
#         if region_filter:
#             return "REGION"
#         return "REPUBLIC"
#
#     def _validate_region(self, region_code: str | None):
#         if not region_code:
#             return None
#         region_code = region_code.strip()
#         allowed = {c for c, _ in RegionChoices.choices}
#         # Query param ANDIJON kelsa — RegionChoices ham ANDIJON bo‘lishi kerak
#         if region_code not in allowed:
#             return None
#         return region_code
#
#     # =========================================================
#     # MAIN
#     # =========================================================
#
#     def get(self, request):
#         start_time = time.time()
#         lang = get_lang_code(request)
#
#         region_filter = self._validate_region(request.query_params.get("region"))
#         organization_filter = request.query_params.get("organization")
#
#         scope = self._resolve_scope(region_filter=region_filter, organization_filter=organization_filter)
#
#         connection.queries_log.clear()
#
#         # 1) Target statement & columns
#         try:
#             target_statement = self.get_target_statement()
#             columns_data = self.get_all_columns_data(target_statement.id)
#             skeleton, leaf_paths = self.build_tree_no_queries(columns_data, lang)
#         except Exception:
#             return self._build_empty_response(lang, {})
#
#         # 2) Organizations (EARLY FILTER)
#         try:
#             org_qs = Organization.objects.only("id", "region", "name", "name_uz", "name_ru")
#
#             if region_filter:
#                 org_qs = org_qs.filter(region=region_filter)
#
#             if organization_filter:
#                 org_qs = org_qs.filter(id=organization_filter)
#
#             organizations = list(org_qs)
#         except Exception:
#             return self._build_empty_response(lang, skeleton)
#
#         if not organizations:
#             # region bo‘yicha filter bo‘lsa: REGION bo‘sh qaytishi kerak
#             if scope == "REGION":
#                 region_name = dict(RegionChoices.choices).get(region_filter, region_filter or "")
#                 return Response({
#                     "level": "REGION",
#                     "hudud": region_name,
#                     "result": skeleton,
#                     "children": [],
#                 })
#
#             # org bo‘lsa: ORG bo‘sh
#             if scope == "ORGANIZATION":
#                 return Response({
#                     "level": "ORGANIZATION",
#                     "hudud": "",
#                     "result": skeleton,
#                 })
#
#             return self._build_empty_response(lang, skeleton)
#
#         org_ids = [o.id for o in organizations]
#
#         # 3) Source statements
#         source_statement_names = {r["source_statement_name_uz"] for r in MAPPING_RULES}
#         source_statements = list(
#             Statement.objects.filter(name_uz__in=source_statement_names).only("id", "name_uz")
#         )
#         statement_by_name = {s.name_uz: s.id for s in source_statements}
#         statement_ids = list(statement_by_name.values())
#
#         if not statement_ids:
#             # structure bor, data yo‘q
#             return self._build_scoped_empty(scope, lang, skeleton, region_filter)
#
#         # 4) Latest report ids (accepted)
#         latest_report_ids = self.get_latest_report_ids_raw(org_ids, statement_ids)
#         # data topilmasa ham baribir skeleton qaytarish kerak — scopega qarab
#         # (directorga structure kerak bo‘lishi mumkin)
#         reports = []
#         report_map = {}
#         if latest_report_ids:
#             reports = list(Report.objects.filter(id__in=latest_report_ids).only("id", "organization_id", "statement_id"))
#             report_map = {(r.organization_id, r.statement_id): r.id for r in reports}
#
#         # 5) Plan maps
#         plan_map, plant_plan_map = {}, {}
#         try:
#             plan_map, plant_plan_map = load_plan_maps(org_ids, statement_ids)
#         except Exception:
#             plan_map, plant_plan_map = {}, {}
#
#         # 6) Report values
#         report_values = {}
#         try:
#             report_values = self.get_report_values(latest_report_ids)
#         except Exception:
#             report_values = {}
#
#         # 7) Group organizations by region
#         region_map = defaultdict(list)
#         for org in organizations:
#             region_map[org.region].append(org)
#
#         # 8) Build payloads
#         regions_payload = []
#         republic_maps = []
#
#         for region_code, orgs in region_map.items():
#             region_name = dict(RegionChoices.choices).get(region_code, region_code)
#
#             org_nodes = []
#             region_target_maps = []
#
#             for org in orgs:
#                 target_value_map = {}
#
#                 # fill map by rules with priority Plan -> PlantPlan(sum) -> Report
#                 for rule in MAPPING_RULES:
#                     stmt_id = statement_by_name.get(rule["source_statement_name_uz"])
#                     if not stmt_id:
#                         target_value_map[rule["target"]] = ""
#                         continue
#
#                     ordering = rule["source"]
#                     key = (org.id, stmt_id)
#
#                     # 1) Plan
#                     if key in plan_map and ordering in plan_map[key]:
#                         target_value_map[rule["target"]] = plan_map[key][ordering]
#                         continue
#
#                     # 2) PlantPlan sum
#                     if key in plant_plan_map:
#                         total = Decimal("0")
#                         found = False
#                         for plant_id, plant_map in plant_plan_map[key].items():
#                             if ordering in plant_map:
#                                 total += self.safe_decimal(plant_map[ordering])
#                                 found = True
#                         if found and total != Decimal("0"):
#                             target_value_map[rule["target"]] = str(total)
#                             continue
#
#                     # 3) Report value
#                     report_id = report_map.get(key)
#                     if report_id and ordering in report_values.get(report_id, {}):
#                         target_value_map[rule["target"]] = report_values[report_id][ordering]
#                     else:
#                         target_value_map[rule["target"]] = ""
#
#                 # formula blocks only calculate, never aggregate %
#                 for reja_ordering, amalda_ordering, percent_ordering, diff_ordering in FORMULA_BLOCKS:
#                     reja_value = target_value_map.get(reja_ordering, "")
#                     amalda_value = target_value_map.get(amalda_ordering, "")
#
#                     if reja_value != "" and amalda_value != "":
#                         reja_dec = self.safe_decimal(reja_value)
#                         amalda_dec = self.safe_decimal(amalda_value)
#
#                         if reja_dec != Decimal("0"):
#                             target_value_map[percent_ordering] = str(
#                                 round_decimal((amalda_dec / reja_dec) * Decimal("100"), 1)
#                             )
#                         else:
#                             target_value_map[percent_ordering] = ""
#
#                         target_value_map[diff_ordering] = str(reja_dec - amalda_dec)
#                     else:
#                         target_value_map[percent_ordering] = ""
#                         target_value_map[diff_ordering] = ""
#
#                 region_target_maps.append(target_value_map)
#
#                 # org name
#                 if lang == "uz":
#                     org_name = getattr(org, "name_uz", None) or org.name
#                 elif lang == "ru":
#                     org_name = getattr(org, "name_ru", None) or getattr(org, "name_uz", None) or org.name
#                 else:
#                     org_name = org.name
#
#                 org_result = self.materialize_result_from_value_map(
#                     skeleton=skeleton,
#                     leaf_paths=leaf_paths,
#                     value_map=target_value_map,
#                 )
#
#                 org_nodes.append({
#                     "level": "ORGANIZATION",
#                     "hudud": org_name,
#                     "result": org_result,
#                 })
#
#             # region aggregate
#             region_aggregated = aggregate_target_maps(region_target_maps) if region_target_maps else {}
#
#             # region formula recalc
#             for reja_ordering, amalda_ordering, percent_ordering, diff_ordering in FORMULA_BLOCKS:
#                 reja_value = region_aggregated.get(reja_ordering, "")
#                 amalda_value = region_aggregated.get(amalda_ordering, "")
#
#                 if reja_value != "" and amalda_value != "":
#                     reja_dec = self.safe_decimal(reja_value)
#                     amalda_dec = self.safe_decimal(amalda_value)
#
#                     if reja_dec != Decimal("0"):
#                         region_aggregated[percent_ordering] = str(
#                             round_decimal((amalda_dec / reja_dec) * Decimal("100"), 1)
#                         )
#                     else:
#                         region_aggregated[percent_ordering] = ""
#
#                     region_aggregated[diff_ordering] = str(reja_dec - amalda_dec)
#                 else:
#                     region_aggregated[percent_ordering] = ""
#                     region_aggregated[diff_ordering] = ""
#
#             # add region to republic only if we are building republic
#             if scope == "REPUBLIC":
#                 republic_maps.append(region_aggregated)
#
#             region_result = self.materialize_result_from_value_map(
#                 skeleton=skeleton,
#                 leaf_paths=leaf_paths,
#                 value_map=region_aggregated,
#             )
#
#             regions_payload.append({
#                 "level": "REGION",
#                 "hudud": region_name,
#                 "result": region_result,
#                 "children": org_nodes,
#             })
#
#         # =========================================================
#         # ✅ SCOPE-BASED RETURN (MUHIM JOY!)
#         # =========================================================
#
#         # 1) organization scope: faqat bitta org qaytar
#         if scope == "ORGANIZATION":
#             # biz filter qilganmiz, shuning uchun 1 ta bo‘lishi kerak
#             # region_payload[0]['children'][0] eng ishonchli
#             if regions_payload and regions_payload[0]["children"]:
#                 return Response(regions_payload[0]["children"][0])
#             return Response({
#                 "level": "ORGANIZATION",
#                 "hudud": "",
#                 "result": skeleton,
#             })
#
#         # 2) region scope: faqat bitta region (ANDIJON) qaytar
#         if scope == "REGION":
#             # regions_payload ichida faqat 1 ta region bo‘ladi (early filter sabab)
#             if regions_payload:
#                 return Response(regions_payload[0])
#             region_name = dict(RegionChoices.choices).get(region_filter, region_filter or "")
#             return Response({
#                 "level": "REGION",
#                 "hudud": region_name,
#                 "result": skeleton,
#                 "children": [],
#             })
#
#         # 3) republic scope: to‘liq
#         republic_aggregated = aggregate_target_maps(republic_maps) if republic_maps else {}
#
#         for reja_ordering, amalda_ordering, percent_ordering, diff_ordering in FORMULA_BLOCKS:
#             reja_value = republic_aggregated.get(reja_ordering, "")
#             amalda_value = republic_aggregated.get(amalda_ordering, "")
#
#             if reja_value != "" and amalda_value != "":
#                 reja_dec = self.safe_decimal(reja_value)
#                 amalda_dec = self.safe_decimal(amalda_value)
#
#                 if reja_dec != Decimal("0"):
#                     republic_aggregated[percent_ordering] = str(
#                         round_decimal((amalda_dec / reja_dec) * Decimal("100"), 1)
#                     )
#                 else:
#                     republic_aggregated[percent_ordering] = ""
#
#                 republic_aggregated[diff_ordering] = str(reja_dec - amalda_dec)
#             else:
#                 republic_aggregated[percent_ordering] = ""
#                 republic_aggregated[diff_ordering] = ""
#
#         republic_title = "Respublika Jami" if lang == "uz" else "Республиканский итог"
#         republic_result = self.materialize_result_from_value_map(
#             skeleton=skeleton,
#             leaf_paths=leaf_paths,
#             value_map=republic_aggregated,
#         )
#
#         payload = {
#             "level": "REPUBLIC",
#             "hudud": republic_title,
#             "result": republic_result,
#             "children": regions_payload,
#         }
#
#         # optional perf log
#         _ = time.time() - start_time
#         return Response(payload)
#
#     # =========================================================
#     # EMPTY RESPONSE HELPERS
#     # =========================================================
#
#     def _build_empty_response(self, lang, skeleton):
#         republic_title = "Respublika Jami" if lang == "uz" else "Республиканский итог"
#         return Response({
#             "level": "REPUBLIC",
#             "hudud": republic_title,
#             "result": skeleton if skeleton else {},
#             "children": [],
#         })
#
#     def _build_scoped_empty(self, scope, lang, skeleton, region_filter):
#         if scope == "ORGANIZATION":
#             return Response({"level": "ORGANIZATION", "hudud": "", "result": skeleton})
#
#         if scope == "REGION":
#             region_name = dict(RegionChoices.choices).get(region_filter, region_filter or "")
#             return Response({"level": "REGION", "hudud": region_name, "result": skeleton, "children": []})
#
#         return self._build_empty_response(lang, skeleton)

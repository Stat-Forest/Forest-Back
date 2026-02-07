# import time
# from collections import defaultdict
# from decimal import Decimal, InvalidOperation
# from django.db import connection
# from django.core.cache import cache
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
#
# from apps.general.models import Organization
# from apps.information_analytical.serializers.aggregation import aggregate_target_maps
# from apps.reports.models import Statement, StatementColumn, Report
# from apps.information_analytical.mapping import MAPPING_RULES, FORMULA_BLOCKS
# from apps.information_analytical.services.plan_loader import load_plan_maps
# # ✅ Tuzatish: materialize_result_from_value_map ni to'g'ri import qilish
# from apps.information_analytical.services.monitoring_engine import (
#     materialize_result_from_value_map,
#     safe_percent,
#     safe_diff
# )
#
# from apps.utils.translation import get_lang_code
# from apps.utils.services import RegionChoices
#
# # ✅ Qo'shimcha: set_by_path funksiyasini import qilish yoki yaratish
# from apps.information_analytical.serializers.forest_monitoring import set_by_path
#
#
# class ForestMonitoringAPIView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     # =========================================================
#     # CUSTOM materialize_result_from_value_map (agar import bo'lmasa)
#     # =========================================================
#
#     def materialize_result_from_value_map(self, skeleton, leaf_paths, value_map):
#         """
#         skeleton: nested dict (titles)
#         leaf_paths: ordering -> path_titles
#         value_map: ordering -> value
#         """
#         import copy
#         result = copy.deepcopy(skeleton)
#
#         # Faqat bo'sh bo'lmagan qiymatlarni qo'shish
#         for ordering, path in leaf_paths.items():
#             val = value_map.get(ordering)
#             if val is not None and val != "":
#                 # set_by_path funksiyasini chaqirish
#                 self._set_by_path(result, path, val)
#
#         return result
#
#     def _set_by_path(self, root: dict, path: list[str], value):
#         """Path bo'yicha nested dict ga qiymat qo'yish"""
#         cur = root
#         for key in path[:-1]:
#             if key not in cur:
#                 cur[key] = {}
#             cur = cur[key]
#         cur[path[-1]] = "" if value is None else value
#
#     # =========================================================
#     # HELPER FUNCTIONS
#     # =========================================================
#
#     def is_numeric_string(self, value):
#         """String numeric ekanligini tekshirish"""
#         if not value or not isinstance(value, str):
#             return False
#
#         # Bo'sh string yoki faqat bo'shliq
#         if value.strip() == "":
#             return False
#
#         # Agar vergul yoki nuqta bilan raqam bo'lsa
#         cleaned = value.replace(',', '.').replace(' ', '')
#
#         # Bir nechta nuqta borligini tekshirish
#         if cleaned.count('.') > 1:
#             return False
#
#         # Raqamlar, nuqta va minus belgisi bo'lishi kerak
#         if cleaned.replace('.', '', 1).replace('-', '', 1).isdigit():
#             return True
#
#         return False
#
#     def safe_decimal(self, value):
#         """Xavfsiz Decimal konvertatsiya"""
#         if value in (None, "", " "):
#             return Decimal('0')
#
#         try:
#             # Agar string bo'lsa
#             if isinstance(value, str):
#                 # Agar numeric string bo'lmasa
#                 if not self.is_numeric_string(value):
#                     return Decimal('0')
#
#                 # Vergulni nuqtaga o'zgartirish
#                 value = value.replace(',', '.')
#
#             return Decimal(str(value))
#         except (InvalidOperation, ValueError, TypeError):
#             return Decimal('0')
#
#     # =========================================================
#     # STATEMENT & COLUMNS
#     # =========================================================
#
#     def get_target_statement(self):
#         """Target statement - cached"""
#         cache_key = "forest_monitoring_target_statement"
#         stmt = cache.get(cache_key)
#         if not stmt:
#             stmt = Statement.objects.only("id", "name_uz").get(
#                 name_uz="O'rmonlar kesimida"
#             )
#             cache.set(cache_key, stmt, 3600)
#         return stmt
#
#     def get_all_columns_data(self, statement_id):
#         """Barcha column ma'lumotlari - cached"""
#         cache_key = f"forest_monitoring_columns_{statement_id}"
#         cached = cache.get(cache_key)
#         if cached:
#             return cached
#
#         cols = list(
#             StatementColumn.objects.filter(statement_id=statement_id).only(
#                 "id", "ordering", "title", "title_uz", "title_ru",
#                 "parent_id", "is_organization"
#             )
#         )
#
#         # Children dict yasash
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
#
#         cache.set(cache_key, data, 3600)
#         return data
#
#     def get_title(self, col, lang):
#         """Column title olish - no queries"""
#         if not col:
#             return ""
#         if lang == "uz":
#             return col.title_uz or col.title
#         if lang == "ru":
#             return col.title_ru or col.title_uz or col.title
#         return col.title
#
#     def build_tree_no_queries(self, data, lang):
#         """Tree qurish - no database queries"""
#         cols = data["columns"]
#
#         # Group by parent
#         by_parent = defaultdict(list)
#         for c in cols:
#             if not c.is_organization:
#                 by_parent[str(c.parent_id) if c.parent_id else None].append(c)
#
#         # Sort by ordering
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
#                 # Check if has children
#                 if str(col.id) in data["children_dict"]:
#                     result[title] = build_node(str(col.id), new_path)
#                 else:
#                     result[title] = ""
#                     leaf_paths[col.ordering] = new_path
#
#             return result
#
#         skeleton = build_node(None, [])
#         return skeleton, leaf_paths
#
#     # =========================================================
#     # REPORT DATA FETCHING (FIXED - handles text values)
#     # =========================================================
#
#     def get_latest_report_ids_raw(self, org_ids, stmt_ids):
#         """Eng oxirgi report ID larini olish"""
#         if not org_ids or not stmt_ids:
#             return []
#
#         sql = """
#               SELECT DISTINCT \
#               ON (organization_id, statement_id) id
#               FROM reports_report
#               WHERE organization_id = ANY (%s)
#                 AND statement_id = ANY (%s)
#                 AND status = 'accepted'
#               ORDER BY organization_id, statement_id, created_at DESC \
#               """
#
#         with connection.cursor() as cursor:
#             cursor.execute(sql, [org_ids, stmt_ids])
#             return [row[0] for row in cursor.fetchall()]
#
#     def get_report_values(self, report_ids):
#         """ReportItem va ReportItemInner ma'lumotlarini olish - SAFE VERSION"""
#         if not report_ids:
#             return {}
#
#         # ✅ FIXED: Text qiymatlarni filter qilish
#         # Avval faqat numeric qiymatlarni olish
#         sql_numeric_items = """
#                             SELECT ri.report_id, \
#                                    sc.ordering, \
#                                    ri.value
#                             FROM reports_reportitem ri
#                                      JOIN reports_statementcolumn sc ON sc.id = ri.statement_column_id
#                             WHERE ri.report_id = ANY (%s)
#                               AND ri.value IS NOT NULL
#                               AND ri.value != ''
#           AND ri.value ~ '^[-+]?[0-9]*[.,]?[0-9]+$'
#           AND NOT EXISTS (
#               SELECT 1 FROM reports_reportiteminner rii
#               WHERE rii.report_item_id = ri.id
#           ) \
#                             """
#
#         # Inner bilan bog'liq itemlar
#         sql_inner_items = """
#                           SELECT ri.report_id, \
#                                  sc.ordering, \
#                                  SUM( \
#                                          CASE \
#                                              WHEN rii.value ~ '^[-+]?[0-9]*[.,]?[0-9]+$'
#                     THEN CAST(replace(rii.value, ',', '.') AS DECIMAL) \
#                                              ELSE 0 \
#                                              END \
#                                  ) as total_value
#                           FROM reports_reportitem ri
#                                    JOIN reports_statementcolumn sc ON sc.id = ri.statement_column_id
#                                    JOIN reports_reportiteminner rii ON rii.report_item_id = ri.id
#                           WHERE ri.report_id = ANY (%s)
#                           GROUP BY ri.report_id, sc.ordering \
#                           """
#
#         result = defaultdict(dict)
#
#         with connection.cursor() as cursor:
#             # 1. Faqat numeric qiymatli ReportItem lar
#             cursor.execute(sql_numeric_items, [report_ids])
#             for report_id, ordering, value in cursor.fetchall():
#                 if value:
#                     try:
#                         dec_value = self.safe_decimal(value)
#                         if dec_value != Decimal('0'):
#                             result[report_id][ordering] = str(dec_value)
#                     except:
#                         pass
#
#             # 2. Inner bilan bog'liq itemlar
#             cursor.execute(sql_inner_items, [report_ids])
#             for report_id, ordering, total_value in cursor.fetchall():
#                 if total_value is not None:
#                     try:
#                         dec_value = Decimal(str(total_value))
#                         if dec_value != Decimal('0'):
#                             # Agar allaqachon qiymat bo'lsa, qo'shamiz
#                             existing = result[report_id].get(ordering)
#                             if existing:
#                                 existing_dec = self.safe_decimal(existing)
#                                 total_dec = existing_dec + dec_value
#                                 result[report_id][ordering] = str(total_dec)
#                             else:
#                                 result[report_id][ordering] = str(dec_value)
#                     except:
#                         pass
#
#         return dict(result)
#
#     # =========================================================
#     # PLAN DATA FETCHING (SAFE VERSION)
#     # =========================================================
#
#     def get_plant_plan_values_fixed(self, org_ids, stmt_ids):
#         """PlantPlan va PlantPlanItem ma'lumotlarini olish - SAFE VERSION"""
#         if not org_ids or not stmt_ids:
#             return {}
#
#         # ✅ FIXED: Faqat numeric qiymatlarni olish
#         sql = """
#               SELECT p.organization_id, \
#                      p.statement_id, \
#                      sc.ordering, \
#                      SUM( \
#                              CASE \
#                                  WHEN ppi.plan_value ~ '^[-+]?[0-9]*[.,]?[0-9]+$'
#                     THEN CAST(replace(ppi.plan_value, ',', '.') AS DECIMAL) \
#                                  ELSE 0 \
#                                  END \
#                      ) as total_plan_value
#               FROM reports_plantplanitem ppi
#                        JOIN reports_plantplan pp ON pp.id = ppi.plant_plan_id
#                        JOIN reports_plan p ON p.id = pp.plan_id
#                        JOIN reports_statementcolumn sc ON sc.id = ppi.column_id
#               WHERE p.organization_id = ANY (%s)
#                 AND p.statement_id = ANY (%s)
#                 AND ppi.plan_value IS NOT NULL
#               GROUP BY p.organization_id, p.statement_id, sc.ordering \
#               """
#
#         result = {}
#
#         with connection.cursor() as cursor:
#             cursor.execute(sql, [org_ids, stmt_ids])
#             for org_id, stmt_id, ordering, total_plan_value in cursor.fetchall():
#                 if total_plan_value is not None and total_plan_value != 0:
#                     key = (org_id, stmt_id)
#                     if key not in result:
#                         result[key] = {}
#
#                     try:
#                         dec_value = Decimal(str(total_plan_value))
#                         if dec_value != Decimal('0'):
#                             result[key][ordering] = str(dec_value)
#                     except:
#                         pass
#
#         return result
#
#     # =========================================================
#     # MAIN METHOD (SAFE VERSION)
#     # =========================================================
#
#     def get(self, request):
#         """Asosiy GET endpoint - FULLY WORKING with SAFE TYPE CONVERSION"""
#         start_time = time.time()
#         lang = get_lang_code(request)
#
#         print(f"\n{'=' * 60}")
#         print(f"🚀 ForestMonitoringAPIView STARTED")
#         print(f"{'=' * 60}")
#
#         # Reset query log
#         connection.queries_log.clear()
#
#         # 1. Target statement va columns
#         print(f"[1/8] Loading target statement and columns...")
#         try:
#             target_statement = self.get_target_statement()
#             columns_data = self.get_all_columns_data(target_statement.id)
#             skeleton, leaf_paths = self.build_tree_no_queries(columns_data, lang)
#         except Exception as e:
#             print(f"Error loading statement/columns: {e}")
#             return self._build_empty_response(lang, {})
#
#         # 2. Organizations
#         print(f"[2/8] Loading organizations...")
#         try:
#             organizations = list(
#                 Organization.objects.only("id", "region", "name", "name_uz", "name_ru")
#             )
#         except Exception as e:
#             print(f"Error loading organizations: {e}")
#             return self._build_empty_response(lang, skeleton)
#
#         if not organizations:
#             print("No organizations found, returning empty response")
#             return self._build_empty_response(lang, skeleton)
#
#         org_ids = [o.id for o in organizations]
#         print(f"   Found {len(organizations)} organizations")
#
#         # 3. Source statements
#         print(f"[3/8] Loading source statements...")
#         try:
#             source_statement_names = {r["source_statement_name_uz"] for r in MAPPING_RULES}
#             source_statements = list(
#                 Statement.objects.filter(name_uz__in=source_statement_names).only("id", "name_uz")
#             )
#             statement_by_name = {s.name_uz: s.id for s in source_statements}
#             statement_ids = list(statement_by_name.values())
#             print(f"   Found {len(source_statements)} source statements")
#         except Exception as e:
#             print(f"Error loading source statements: {e}")
#             statement_by_name = {}
#             statement_ids = []
#
#         if not statement_ids:
#             print("No source statements found, returning empty response")
#             return self._build_empty_response(lang, skeleton)
#
#         # 4. Latest report IDs
#         print(f"[4/8] Finding latest reports...")
#         try:
#             latest_report_ids = self.get_latest_report_ids_raw(org_ids, statement_ids)
#         except Exception as e:
#             print(f"Error finding latest reports: {e}")
#             latest_report_ids = []
#
#         if not latest_report_ids:
#             print("No latest reports found, returning empty response")
#             return self._build_empty_response(lang, skeleton)
#
#         print(f"   Found {len(latest_report_ids)} latest reports")
#
#         # 5. Reports basic info
#         print(f"[5/8] Loading reports basic info...")
#         try:
#             reports = list(
#                 Report.objects.filter(id__in=latest_report_ids).only(
#                     "id", "organization_id", "statement_id"
#                 )
#             )
#         except Exception as e:
#             print(f"Error loading reports: {e}")
#             reports = []
#
#         # Report map: (org_id, stmt_id) -> report_id
#         report_map = {}
#         for report in reports:
#             key = (report.organization_id, report.statement_id)
#             report_map[key] = report.id
#
#         print(f"   Mapped {len(report_map)} reports")
#
#         # 6. Plan data
#         print(f"[6/8] Loading plan data...")
#         plan_map = {}
#         plant_plan_map = {}
#         try:
#             plan_map, plant_plan_map = load_plan_maps(org_ids, statement_ids)
#         except Exception as e:
#             print(f"Error loading plan data: {e}")
#
#         # 7. Report values
#         print(f"[7/8] Loading report values...")
#         report_values = {}
#         try:
#             report_values = self.get_report_values(latest_report_ids)
#         except Exception as e:
#             print(f"Error loading report values: {e}")
#
#         # 8. Plant plan values (aggregated)
#         print(f"[8/8] Loading plant plan values...")
#         plant_plan_values = {}
#         try:
#             plant_plan_values = self.get_plant_plan_values_fixed(org_ids, statement_ids)
#         except Exception as e:
#             print(f"Error loading plant plan values: {e}")
#
#         # 9. Group organizations by region
#         region_map = defaultdict(list)
#         for org in organizations:
#             region_map[org.region].append(org)
#
#         print(f"   Grouped into {len(region_map)} regions")
#
#         # 10. Build response with aggregation
#         print(f"Building response with aggregation...")
#         regions_payload = []
#         republic_maps = []
#         org_counter = 0
#
#         for region_code, orgs in region_map.items():
#             region_name = dict(RegionChoices.choices).get(region_code, region_code)
#
#             org_nodes = []
#             region_target_maps = []
#
#             for org in orgs:
#                 org_counter += 1
#                 target_value_map = {}
#
#                 # Apply MAPPING_RULES
#                 for rule in MAPPING_RULES:
#                     statement_id = statement_by_name.get(rule["source_statement_name_uz"])
#                     if not statement_id:
#                         target_value_map[rule["target"]] = ""
#                         continue
#
#                     ordering = rule["source"]
#                     key = (org.id, statement_id)
#
#                     # 1. Check plan map
#                     try:
#                         if ordering in plan_map.get(key, {}):
#                             target_value_map[rule["target"]] = plan_map[key][ordering]
#                             continue
#                     except:
#                         pass
#
#                     # 2. Check plant plan map (aggregated)
#                     try:
#                         if ordering in plant_plan_values.get(key, {}):
#                             target_value_map[rule["target"]] = plant_plan_values[key][ordering]
#                             continue
#                     except:
#                         pass
#
#                     # 3. Check report
#                     try:
#                         report_id = report_map.get(key)
#                         if report_id and ordering in report_values.get(report_id, {}):
#                             target_value_map[rule["target"]] = report_values[report_id][ordering]
#                         else:
#                             target_value_map[rule["target"]] = ""
#                     except:
#                         target_value_map[rule["target"]] = ""
#
#                 # Apply FORMULA_BLOCKS
#                 for reja_ordering, amalda_ordering, percent_ordering, diff_ordering in FORMULA_BLOCKS:
#                     reja_value = target_value_map.get(reja_ordering, "")
#                     amalda_value = target_value_map.get(amalda_ordering, "")
#
#                     if reja_value and reja_value != "" and amalda_value and amalda_value != "":
#                         try:
#                             # Qiymatlarni xavfsiz decimal ga o'tkazish
#                             reja_dec = self.safe_decimal(reja_value)
#                             amalda_dec = self.safe_decimal(amalda_value)
#
#                             if reja_dec != Decimal('0'):
#                                 target_value_map[percent_ordering] = str(
#                                     (amalda_dec / reja_dec) * Decimal('100')
#                                 )
#                             else:
#                                 target_value_map[percent_ordering] = ""
#
#                             target_value_map[diff_ordering] = str(reja_dec - amalda_dec)
#                         except:
#                             target_value_map[percent_ordering] = ""
#                             target_value_map[diff_ordering] = ""
#                     else:
#                         target_value_map[percent_ordering] = ""
#                         target_value_map[diff_ordering] = ""
#
#                 # Save for region aggregation
#                 region_target_maps.append(target_value_map)
#
#                 # Organization name
#                 org_name = ""
#                 try:
#                     if lang == "uz":
#                         org_name = getattr(org, "name_uz", None) or org.name
#                     elif lang == "ru":
#                         org_name = getattr(org, "name_ru", None) or getattr(org, "name_uz", None) or org.name
#                     else:
#                         org_name = org.name
#                 except:
#                     org_name = org.name
#
#                 # ✅ FIXED: materialize_result_from_value_map ni to'g'ri chaqirish
#                 try:
#                     org_result = self.materialize_result_from_value_map(
#                         skeleton, leaf_paths, target_value_map
#                     )
#                 except Exception as e:
#                     print(f"Error materializing organization result: {e}")
#                     org_result = skeleton
#
#                 org_nodes.append({
#                     "level": "ORGANIZATION",
#                     "hudud": org_name,
#                     "result": org_result,
#                 })
#
#             # REGION AGGREGATION
#             region_aggregated = {}
#             try:
#                 region_aggregated = aggregate_target_maps(region_target_maps)
#             except Exception as e:
#                 print(f"Error aggregating region {region_name}: {e}")
#
#             # Recalculate formulas for region
#             for reja_ordering, amalda_ordering, percent_ordering, diff_ordering in FORMULA_BLOCKS:
#                 reja_value = region_aggregated.get(reja_ordering, "")
#                 amalda_value = region_aggregated.get(amalda_ordering, "")
#
#                 if reja_value and reja_value != "" and amalda_value and amalda_value != "":
#                     try:
#                         reja_dec = self.safe_decimal(reja_value)
#                         amalda_dec = self.safe_decimal(amalda_value)
#
#                         if reja_dec != Decimal('0'):
#                             region_aggregated[percent_ordering] = str(
#                                 (amalda_dec / reja_dec) * Decimal('100')
#                             )
#                         else:
#                             region_aggregated[percent_ordering] = ""
#
#                         region_aggregated[diff_ordering] = str(reja_dec - amalda_dec)
#                     except:
#                         region_aggregated[percent_ordering] = ""
#                         region_aggregated[diff_ordering] = ""
#                 else:
#                     region_aggregated[percent_ordering] = ""
#                     region_aggregated[diff_ordering] = ""
#
#             # Save for republic aggregation
#             republic_maps.append(region_aggregated)
#
#             # Region result
#             region_result = {}
#             try:
#                 region_result = self.materialize_result_from_value_map(
#                     skeleton, leaf_paths, region_aggregated
#                 )
#             except:
#                 region_result = skeleton
#
#             regions_payload.append({
#                 "level": "REGION",
#                 "hudud": region_name,
#                 "result": region_result,
#                 "children": org_nodes,
#             })
#
#         # REPUBLIC AGGREGATION
#         republic_aggregated = {}
#         try:
#             republic_aggregated = aggregate_target_maps(republic_maps)
#         except Exception as e:
#             print(f"Error aggregating republic: {e}")
#
#         # Recalculate formulas for republic
#         for reja_ordering, amalda_ordering, percent_ordering, diff_ordering in FORMULA_BLOCKS:
#             reja_value = republic_aggregated.get(reja_ordering, "")
#             amalda_value = republic_aggregated.get(amalda_ordering, "")
#
#             if reja_value and reja_value != "" and amalda_value and amalda_value != "":
#                 try:
#                     reja_dec = self.safe_decimal(reja_value)
#                     amalda_dec = self.safe_decimal(amalda_value)
#
#                     if reja_dec != Decimal('0'):
#                         republic_aggregated[percent_ordering] = str(
#                             (amalda_dec / reja_dec) * Decimal('100')
#                         )
#                     else:
#                         republic_aggregated[percent_ordering] = ""
#
#                     republic_aggregated[diff_ordering] = str(reja_dec - amalda_dec)
#                 except:
#                     republic_aggregated[percent_ordering] = ""
#                     republic_aggregated[diff_ordering] = ""
#             else:
#                 republic_aggregated[percent_ordering] = ""
#                 republic_aggregated[diff_ordering] = ""
#
#         # Final response
#         republic_title = "Respublika Jami" if lang == "uz" else "Республиканский итог"
#
#         # Republic result
#         republic_result = {}
#         try:
#             republic_result = self.materialize_result_from_value_map(
#                 skeleton, leaf_paths, republic_aggregated
#             )
#         except:
#             republic_result = skeleton
#
#         payload = {
#             "level": "REPUBLIC",
#             "hudud": republic_title,
#             "result": republic_result,
#             "children": regions_payload,
#         }
#
#         # Performance stats
#         total_time = time.time() - start_time
#         total_queries = len(connection.queries)
#
#         print(f"\n{'=' * 60}")
#         print(f"🎉 ForestMonitoringAPIView COMPLETED")
#         print(f"{'=' * 60}")
#         print(f"📊 PERFORMANCE STATS:")
#         print(f"   Total time: {total_time:.3f}s")
#         print(f"   Total queries: {total_queries}")
#         print(f"   Organizations: {org_counter}")
#         print(f"   Regions: {len(region_map)}")
#         print(f"   Response size: ~{len(str(payload)) // 1024} KB")
#         print(f"{'=' * 60}")
#
#         return Response(payload)
#
#     def _build_empty_response(self, lang, skeleton):
#         """Bo'sh response"""
#         republic_title = "Respublika Jami" if lang == "uz" else "Республиканский итог"
#
#         return Response({
#             "level": "REPUBLIC",
#             "hudud": republic_title,
#             "result": skeleton if skeleton else {},
#             "children": [],
#         })
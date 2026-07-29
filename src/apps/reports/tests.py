# from __future__ import annotations
#
# import logging
# from functools import lru_cache
# from dataclasses import dataclass
# from collections import defaultdict
# from decimal import Decimal, DecimalException
# from typing import Dict, List, Tuple, Optional, Set, Any
#
# from django.db import transaction
# from django.db.models import Prefetch, Q
#
# from apps.utils.services import RegionChoices
# from apps.utils.translation import get_translated_field
# from apps.reports.services.get_calculation_for_generals import calculate_general_report
# from apps.reports.services.report_calculate_expressions import calculate_by_expressions
# from apps.reports.models import Report, ReportItem, ReportItemInner, StatementColumn, Plant, Deadline
#
# logger = logging.getLogger(__name__)
#
# PLAN_FROM_INDIVIDUAL_GENERAL_STATEMENTS = {
#     "Urug' xarakati Reja",
#     "Og'ir mahalla",
# }
#
#
# def should_use_individual_general_plan_source(statement) -> bool:
#     statement_names = {
#         (getattr(statement, "name", "") or "").strip(),
#         (getattr(statement, "name_uz", "") or "").strip(),
#     }
#     return bool(statement_names & PLAN_FROM_INDIVIDUAL_GENERAL_STATEMENTS)
#
#
# # ============================================================
# # Period parsing
# # ============================================================
#
# @dataclass
# class PeriodRange:
#     kind: str  # "year" | "quarter"
#     year: int
#     quarter: int | None = None
#
#
# def parse_period(period: str) -> PeriodRange:
#     p = (period or "").strip()
#     if not p:
#         raise ValueError("period is required")
#     if "-Q" in p:
#         year_s, q_s = p.split("-Q", 1)
#         year = int(year_s)
#         q = int(q_s)
#         if q not in (1, 2, 3, 4):
#             raise ValueError("quarter must be 1..4")
#         return PeriodRange(kind="quarter", year=year, quarter=q)
#     return PeriodRange(kind="year", year=int(p))
#
#
# # ============================================================
# # Daromad helpers
# # ============================================================
#
# DAROMAD_NAMES = {"Daromad"}
#
# # Har bir quarter uchun barcha Amalda ordering'lar:
# # - X.Y.2.Z.2  → oylik Amalda (Yanvar, Fevral, ... Dekabr)
# # - X.Y.1.2    → chorak reja section'idagi Amalda (1.3.1.2, 1.4.1.2, ...)
# # - 1.1.3      → yillik umumiy Amalda
# DAROMAD_QUARTER_AMALDA_ORDERINGS: dict[str, frozenset[str]] = {
#     "q1": frozenset([
#         "1.3.2.1.2",  # Yanvar   Amalda
#         "1.3.2.2.2",  # Fevral   Amalda
#         "1.3.2.3.2",  # Mart     Amalda
#         "1.3.1.2",    # 1-chorak reja → Amalda
#     ]),
#     "q2": frozenset([
#         "1.4.2.1.2",  # Aprel    Amalda
#         "1.4.2.2.2",  # May      Amalda
#         "1.4.2.3.2",  # Iyun     Amalda
#         "1.4.1.2",    # 2-chorak reja → Amalda
#     ]),
#     "q3": frozenset([
#         "1.5.2.1.2",  # Iyul     Amalda
#         "1.5.2.2.2",  # Avgust   Amalda
#         "1.5.2.3.2",  # Sentabr  Amalda
#         "1.5.1.2",    # 3-chorak reja → Amalda
#     ]),
#     "q4": frozenset([
#         "1.6.2.1.2",  # Oktabr   Amalda
#         "1.6.2.2.2",  # Noyabr   Amalda
#         "1.6.2.3.2",  # Dekabr   Amalda
#         "1.6.1.2",    # 4-chorak reja → Amalda
#     ]),
# }
#
# # Yillik umumiy Amalda (1.1.3) va Farqi (1.1.4), Foizda (1.1.5) —
# # bular calculated column bo'lgani uchun is_calculated_column() orqali
# # avtomatik filter'dan chiqariladi. Hech qanday qo'shimcha amal shart emas.
#
#
# def _is_daromad_statement(statement) -> bool:
#     """Statement Daromad ekanligini tekshiradi."""
#     name_uz = (getattr(statement, "name_uz", "") or "").strip()
#     name = (getattr(statement, "name", "") or "").strip()
#     return name_uz in DAROMAD_NAMES or name in DAROMAD_NAMES
#
#
# def _get_accepted_quarters(report: Report) -> list[str]:
#     """
#     Report'dan ACCEPTED bo'lgan quarter'lar ro'yxatini qaytaradi.
#     Faqat Daromad reportlari uchun ishlatiladi.
#
#     Masalan: Q1=ACCEPTED, Q2=SAVED → ["q1"]
#     """
#     accepted = []
#     for q in ("q1", "q2", "q3", "q4"):
#         quarter_num = q[-1]
#         status_field = f"quarter_{quarter_num}_status"
#         status = getattr(report, status_field, None)
#         if status == Report.StatusChoices.ACCEPTED:
#             accepted.append(q)
#     return accepted
#
#
# def _build_daromad_allowed_column_ids(
#     report: Report,
#     cache: "StatementDataCache",
#     accepted_quarters: list[str],
# ) -> set[str]:
#     """
#     Daromad uchun: faqat ACCEPTED bo'lgan quarter'larning
#     amalda ordering'lariga tegishli column ID'larini qaytaradi.
#
#     Reja (status_plan) columnlar va is_organization columnlar
#     har doim ruxsat etiladi — ular quarter-specific emas.
#
#     Bu funksiya aggregation paytida qaysi column'larni SUM qilish
#     kerakligini aniqlab beradi.
#     """
#     allowed_orderings: set[str] = set()
#     for q in accepted_quarters:
#         allowed_orderings.update(DAROMAD_QUARTER_AMALDA_ORDERINGS.get(q, frozenset()))
#
#     allowed_col_ids: set[str] = set()
#     for col_id, col in cache.all_columns.items():
#         # is_organization — har doim ruxsat
#         if getattr(col, "is_organization", False):
#             allowed_col_ids.add(col_id)
#             continue
#
#         # Reja (status_plan) — har doim ruxsat
#         if getattr(col, "status_plan", None):
#             allowed_col_ids.add(col_id)
#             continue
#
#         # Amalda column'lar — faqat ACCEPTED quarter'lar uchun
#         if (col.ordering or "") in allowed_orderings:
#             allowed_col_ids.add(col_id)
#
#     return allowed_col_ids
#
#
# # ============================================================
# # Column rules with caching
# # ============================================================
#
# @lru_cache(maxsize=128)
# def is_calculated_column(col) -> bool:
#     """
#     Aggregation paytida SUM qilinmasligi kerak bo'lgan ustunlar:
#     - calculate_expression bor columnlar
#     - is_user_input=False columnlar
#     - title ichida % / foiz / percent / процент bor columnlar
#
#     Lekin status_plan/Reja columnlar aggregatsiya qilinishi kerak.
#     """
#     if getattr(col, "status_plan", None):
#         return False
#
#     if getattr(col, "calculate_expression", None):
#         return True
#
#     if getattr(col, "is_user_input", True) is False:
#         return True
#
#     titles = [
#         getattr(col, "title", None),
#         getattr(col, "title_uz", None),
#         getattr(col, "title_ru", None),
#     ]
#     title_text = " ".join([x for x in titles if x]).lower()
#
#     if (
#         "%" in title_text
#         or "foiz" in title_text
#         or "percent" in title_text
#         or "процент" in title_text
#     ):
#         return True
#
#     return False
#
#
# def is_aggregatable_column(col) -> bool:
#     return not is_calculated_column(col)
#
#
# @lru_cache(maxsize=128)
# def _is_org_name_column_calc(col_data: tuple) -> bool:
#     if len(col_data) < 3:
#         return False
#
#     is_organization = col_data[0]
#     title_uz = col_data[1] if len(col_data) > 1 else ""
#     title_ru = col_data[2] if len(col_data) > 2 else ""
#
#     if is_organization:
#         return True
#
#     titles = [
#         (title_uz or "").strip().lower(),
#         (title_ru or "").strip().lower(),
#     ]
#     keys = [
#         "tashkilot nomi",
#         "нaименование организации".lower(),
#         "название организации",
#     ]
#     return any(any(k in t for k in keys) for t in titles)
#
#
# def _is_org_name_column(col: StatementColumn) -> bool:
#     try:
#         if getattr(col, "is_organization", False):
#             return True
#     except Exception:
#         pass
#
#     titles = [
#         (getattr(col, "title_uz", "") or "").strip().lower(),
#         (getattr(col, "title_ru", "") or "").strip().lower(),
#     ]
#     keys = [
#         "tashkilot nomi",
#         "нaименование организации".lower(),
#         "название организации",
#     ]
#     return any(any(k in t for k in keys) for t in titles)
#
#
# # ============================================================
# # Statement data cache
# # ============================================================
#
# class StatementDataCache:
#     """Statement ma'lumotlarini cache qiluvchi klass"""
#
#     _instances: Dict[str, 'StatementDataCache'] = {}
#
#     def __new__(cls, statement_id: str):
#         if statement_id not in cls._instances:
#             cls._instances[statement_id] = super().__new__(cls)
#         return cls._instances[statement_id]
#
#     def __init__(self, statement_id: str):
#         if not hasattr(self, '_initialized'):
#             self.statement_id = str(statement_id)
#             self.by_id: Dict[str, StatementColumn] = {}
#             self.by_parent: Dict[str | None, List[StatementColumn]] = defaultdict(list)
#             self.col_data_cache: Dict[str, tuple] = {}
#             self.org_name_cols: List[str] = []
#             self._loaded = False
#             self._initialized = True
#
#     def load(self):
#         if self._loaded:
#             return
#
#         cols = list(
#             StatementColumn.objects
#             .filter(statement_id=self.statement_id)
#             .select_related("parent")
#             .only(
#                 "id", "parent_id", "ordering",
#                 "title_uz", "title_ru", "title",
#                 "is_organization", "is_user_input",
#                 "status_plan"
#             )
#         )
#
#         for c in cols:
#             cid = str(c.id)
#             self.by_id[cid] = c
#
#             self.col_data_cache[cid] = (
#                 getattr(c, "is_user_input", True),
#                 getattr(c, "title_uz", ""),
#                 getattr(c, "title_ru", ""),
#                 getattr(c, "title", ""),
#                 getattr(c, "is_organization", False),
#             )
#
#             parent_key = str(c.parent_id) if c.parent_id else None
#             self.by_parent[parent_key].append(c)
#
#         for cid, data in self.col_data_cache.items():
#             if self._is_org_name_column_from_cache(cid, data):
#                 self.org_name_cols.append(cid)
#
#         for k in self.by_parent:
#             self.by_parent[k].sort(key=lambda x: self._ord_key(x))
#
#         self._loaded = True
#
#     def _ord_key(self, col: StatementColumn):
#         parts = (col.ordering or "").split(".")
#         out = []
#         for p in parts:
#             if p.isdigit():
#                 out.append(int(p))
#             else:
#                 out.append(p)
#         return out
#
#     def _is_org_name_column_from_cache(self, col_id: str, data: tuple = None) -> bool:
#         if data is None:
#             if col_id not in self.col_data_cache:
#                 return False
#             data = self.col_data_cache[col_id]
#
#         if len(data) < 5:
#             return False
#
#         return _is_org_name_column_calc((
#             data[4],  # is_organization
#             data[1],  # title_uz
#             data[2],  # title_ru
#         ))
#
#     def is_aggregatable_from_cache(self, col_id: str) -> bool:
#         col = self.by_id.get(col_id)
#         if not col:
#             return False
#         return not is_calculated_column(col)
#
#     def is_plan_column(self, col_id: str) -> bool:
#         col = self.by_id.get(str(col_id))
#         if not col:
#             return False
#         return bool(getattr(col, "status_plan", None))
#
#     def get_column_path(self, col_id: str, lang: str) -> str:
#         col = self.by_id.get(col_id)
#         if not col:
#             return ""
#
#         parts = []
#         cur = col
#         while cur:
#             title = get_translated_field(cur, "title", lang) or ""
#             parts.append(title)
#             pid = getattr(cur, "parent_id", None)
#             cur = self.by_id.get(str(pid)) if pid else None
#
#         return " – ".join(reversed([p for p in parts if p]))
#
#     @property
#     def all_columns(self) -> Dict[str, StatementColumn]:
#         return self.by_id
#
#
# # ============================================================
# # Deadline cache
# # ============================================================
#
# class DeadlineCache:
#     _instances: Dict[str, 'DeadlineCache'] = {}
#
#     def __new__(cls, deadline_id: str):
#         if deadline_id not in cls._instances:
#             cls._instances[deadline_id] = super().__new__(cls)
#         return cls._instances[deadline_id]
#
#     def __init__(self, deadline_id: str):
#         if not hasattr(self, '_deadline'):
#             self.deadline_id = deadline_id
#             self._deadline = None
#             self._loaded = False
#
#     def get(self):
#         if not self._loaded:
#             self._deadline = Deadline.objects.filter(id=self.deadline_id).first()
#             self._loaded = True
#         return self._deadline
#
#
# # ============================================================
# # Plant data cache
# # ============================================================
#
# class PlantCache:
#     _instance = None
#     _plant_map: Dict[str, str] = {}
#     _loaded = False
#
#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super().__new__(cls)
#         return cls._instance
#
#     def load_plants(self, plant_ids: Set[str]):
#         new_ids = plant_ids - set(self._plant_map.keys())
#         if new_ids:
#             new_plants = dict(
#                 Plant.objects.filter(id__in=new_ids).values_list("id", "name")
#             )
#             self._plant_map.update(new_plants)
#
#     def get_plant_name(self, plant_id: str) -> str:
#         return self._plant_map.get(plant_id, "")
#
#     def get_plant_map(self, plant_ids: Set[str]) -> Dict[str, str]:
#         self.load_plants(plant_ids)
#         return {pid: self._plant_map.get(pid, "") for pid in plant_ids}
#
#
# # ============================================================
# # Helpers
# # ============================================================
#
# def _safe_decimal(v) -> Decimal:
#     try:
#         return Decimal(str(v))
#     except Exception:
#         return Decimal("0")
#
#
# def _prefetch_items_qs():
#     return Prefetch(
#         "report_items",
#         queryset=(
#             ReportItem.objects
#             .select_related("statement_column")
#             .prefetch_related(
#                 Prefetch(
#                     "inners",
#                     queryset=ReportItemInner.objects.select_related("plant")
#                 )
#             )
#         ),
#     )
#
#
# # ============================================================
# # FIX #1: filter_reports_by_deadline — Daromad uchun yangi logika
# # ============================================================
#
# def filter_reports_by_deadline(statement, deadline_id: str):
#     """
#     Deadline bo'yicha individual reportlarni yuklaydi.
#
#     ODDIY STATEMENTLAR:
#         faqat status=ACCEPTED reportlar olinadi.
#
#     DAROMAD STATEMENTI:
#         status=ACCEPTED bo'lmasa ham, kamida bitta
#         quarter_X_status=ACCEPTED bo'lgan reportlar olinadi.
#         Chunki Daromadda bitta Report object'da 4 chorak saqlanadi,
#         va joriy chorak SAVED/SENT tursa ham oldingi choraklar
#         ACCEPTED bo'lib qolishi mumkin.
#
#     Masalan: Q1=ACCEPTED, Q2=SAVED → bu report olinadi,
#     lekin aggregation paytida faqat Q1 qiymatlari summalanadi.
#     """
#     base_qs = (
#         Report.objects
#         .filter(
#             statement=statement,
#             deadline_id=deadline_id,
#             is_report=True,
#             is_general=False,
#             is_individual_general=False,
#             is_republic=False,
#         )
#         .select_related("organization")
#         .prefetch_related(_prefetch_items_qs())
#         .order_by("organization__name")
#     )
#
#     if _is_daromad_statement(statement):
#         # Kamida bitta quarter ACCEPTED bo'lgan reportlarni ol
#         return base_qs.filter(
#             Q(quarter_1_status=Report.StatusChoices.ACCEPTED) |
#             Q(quarter_2_status=Report.StatusChoices.ACCEPTED) |
#             Q(quarter_3_status=Report.StatusChoices.ACCEPTED) |
#             Q(quarter_4_status=Report.StatusChoices.ACCEPTED)
#         )
#
#     # Oddiy statement — faqat to'liq ACCEPTED reportlar
#     return base_qs.filter(status=Report.StatusChoices.ACCEPTED)
#
#
# def filter_individual_general_reports_by_deadline(statement, deadline_id: str):
#     return (
#         Report.objects.filter(
#             statement=statement,
#             deadline_id=deadline_id,
#             is_individual_general=True,
#             is_general=False,
#             is_republic=False,
#             organization__isnull=False,
#         )
#         .select_related("organization")
#         .prefetch_related(_prefetch_items_qs())
#         .order_by("organization__name", "-created_at")
#     )
#
#
# def build_individual_general_by_org(individual_generals: list[Report]) -> dict[str, Report]:
#     result: dict[str, Report] = {}
#     for report in individual_generals:
#         if not report.organization_id:
#             continue
#         org_id = str(report.organization_id)
#         if org_id not in result:
#             result[org_id] = report
#     return result
#
#
# # ============================================================
# # FIX #2: _sum_reports_for_general — Daromad quarter-aware aggregation
# # ============================================================
#
# def _sum_reports_for_general(
#     reports: List[Report],
#     cache: StatementDataCache,
#     individual_general_by_org: dict[str, Report] | None = None,
#     statement=None,
# ):
#     """
#     Region jami uchun qiymatlarni yig'adi.
#
#     DAROMAD LOGIKASI (yangi):
#         - Har bir report uchun qaysi quarter'lar ACCEPTED ekanligini aniqlaymiz.
#         - Faqat ACCEPTED quarter'larning amalda ordering'lariga tegishli
#           column'larni summalashga ruxsat beramiz.
#         - Reja (status_plan) va is_organization column'lar har doim o'tadi.
#
#     ODDIY STATEMENT LOGIKASI (o'zgarmagan):
#         - Barcha aggregatable column'lar summalanadi.
#
#     returns:
#         totals[column_id][plant_id_or_None] = Decimal
#     """
#     totals: Dict[str, Dict[str | None, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
#     individual_general_by_org = individual_general_by_org or {}
#
#     is_daromad = _is_daromad_statement(statement) if statement else False
#
#     for report in reports:
#         org_id = str(report.organization_id) if report.organization_id else None
#
#         # --- Daromad: faqat ACCEPTED quarter column'larini ruxsat et ---
#         daromad_allowed_col_ids: set[str] | None = None
#         if is_daromad:
#             accepted_quarters = _get_accepted_quarters(report)
#             if not accepted_quarters:
#                 # Bu report'da birorta ham ACCEPTED quarter yo'q — o'tkazib yubor
#                 logger.warning(
#                     f"[DAROMAD] Report {report.id} uchun ACCEPTED quarter topilmadi, "
#                     f"aggregation'dan o'tkazib yuborildi."
#                 )
#                 continue
#             daromad_allowed_col_ids = _build_daromad_allowed_column_ids(
#                 report, cache, accepted_quarters
#             )
#
#         # --- Items to'plash ---
#         main_items_by_column = {
#             str(item.statement_column_id): item
#             for item in report.report_items.all()
#         }
#
#         individual_items_by_column = {}
#         individual_general = individual_general_by_org.get(org_id)
#         if individual_general:
#             individual_items_by_column = {
#                 str(item.statement_column_id): item
#                 for item in individual_general.report_items.all()
#             }
#
#         all_column_ids = set(main_items_by_column.keys()) | set(individual_items_by_column.keys())
#
#         for column_id in all_column_ids:
#             # Oddiy aggregation filtr
#             if not cache.is_aggregatable_from_cache(column_id):
#                 continue
#
#             # Daromad: faqat ruxsat etilgan column'lar
#             if daromad_allowed_col_ids is not None and column_id not in daromad_allowed_col_ids:
#                 continue
#
#             # Reja source: individual_general'dan yoki asosiy report'dan
#             if cache.is_plan_column(column_id) and column_id in individual_items_by_column:
#                 source_item = individual_items_by_column[column_id]
#             else:
#                 source_item = main_items_by_column.get(column_id)
#
#             if not source_item:
#                 continue
#
#             for inner in source_item.inners.all():
#                 plant_key = str(inner.plant_id) if inner.plant_id else None
#                 totals[column_id][plant_key] += _safe_decimal(inner.value)
#
#     return totals
#
#
# # ============================================================
# # General/Republic ensure helpers (o'zgarmagan)
# # ============================================================
#
# def _ensure_general_report(statement, deadline_id: str, region_key: str,
#                            deadline_cache: DeadlineCache) -> Optional[Report]:
#     deadline = deadline_cache.get()
#     if not deadline:
#         return None
#
#     try:
#         general = Report.objects.get(
#             statement=statement,
#             deadline_id=deadline_id,
#             region=region_key,
#             is_general=True,
#             organization__isnull=True,
#         )
#     except Report.DoesNotExist:
#         general = None
#     except Report.MultipleObjectsReturned:
#         generals = list(Report.objects.filter(
#             statement=statement,
#             deadline_id=deadline_id,
#             region=region_key,
#             is_general=True,
#             organization__isnull=True,
#         ).order_by("-created_at"))
#         general = generals[0]
#         if len(generals) > 1:
#             Report.objects.filter(id__in=[g.id for g in generals[1:]]).delete()
#
#     if not general:
#         general = Report.objects.create(
#             organization=None,
#             statement=statement,
#             deadline=deadline,
#             region=region_key,
#             is_general=True,
#             is_republic=False,
#             is_individual_general=False,
#             is_report=False,
#             status=Report.StatusChoices.SAVED,
#         )
#     else:
#         updates = {}
#         if general.is_report:
#             updates["is_report"] = False
#         if general.status != Report.StatusChoices.SAVED:
#             updates["status"] = Report.StatusChoices.SAVED
#         if str(general.deadline_id) != deadline_id:
#             updates["deadline_id"] = deadline_id
#         if updates:
#             for k, v in updates.items():
#                 setattr(general, k, v)
#             general.save(update_fields=list(updates.keys()))
#
#     return general
#
#
# def _ensure_republic_report(statement, deadline_id: str, deadline_cache: DeadlineCache) -> Optional[Report]:
#     deadline = deadline_cache.get()
#     if not deadline:
#         return None
#
#     try:
#         rep = Report.objects.get(
#             statement=statement,
#             deadline_id=deadline_id,
#             is_republic=True,
#             organization__isnull=True,
#         )
#     except Report.DoesNotExist:
#         rep = None
#     except Report.MultipleObjectsReturned:
#         reps = list(Report.objects.filter(
#             statement=statement,
#             deadline_id=deadline_id,
#             is_republic=True,
#             organization__isnull=True,
#         ).order_by("-created_at"))
#         rep = reps[0]
#         if len(reps) > 1:
#             Report.objects.filter(id__in=[r.id for r in reps[1:]]).delete()
#
#     if not rep:
#         rep = Report.objects.create(
#             organization=None,
#             statement=statement,
#             deadline=deadline,
#             region=RegionChoices.REPUBLIC if hasattr(RegionChoices, "REPUBLIC") else None,
#             is_republic=True,
#             is_general=False,
#             is_individual_general=False,
#             is_report=False,
#             status=Report.StatusChoices.SAVED,
#         )
#     else:
#         updates = {}
#         if rep.is_report:
#             updates["is_report"] = False
#         if rep.status != Report.StatusChoices.SAVED:
#             updates["status"] = Report.StatusChoices.SAVED
#         if str(rep.deadline_id) != deadline_id:
#             updates["deadline_id"] = deadline_id
#         if updates:
#             for k, v in updates.items():
#                 setattr(rep, k, v)
#             rep.save(update_fields=list(updates.keys()))
#
#     return rep
#
#
# def _create_report_items(report: Report, totals: Dict[str, Dict[str | None, Decimal]],
#                          org_name_cols: List[str], org_name_value: str,
#                          plant_cache: PlantCache) -> None:
#     items_to_create = []
#     inners_to_create = []
#
#     for col_id in org_name_cols:
#         item = ReportItem(
#             report=report,
#             statement_column_id=col_id
#         )
#         items_to_create.append(item)
#
#     if items_to_create:
#         created_items = ReportItem.objects.bulk_create(items_to_create)
#         for item in created_items:
#             inners_to_create.append(
#                 ReportItemInner(
#                     report_item=item,
#                     value=org_name_value
#                 )
#             )
#
#     all_plant_ids = set()
#     for per_plant in totals.values():
#         all_plant_ids.update(k for k in per_plant.keys() if k)
#
#     plant_map = plant_cache.get_plant_map(all_plant_ids)
#
#     numeric_items = []
#     numeric_cids = []
#
#     for cid, per_plant in totals.items():
#         if cid in org_name_cols:
#             continue
#         numeric_items.append(
#             ReportItem(
#                 report=report,
#                 statement_column_id=cid
#             )
#         )
#         numeric_cids.append(cid)
#
#     created_numeric_items = ReportItem.objects.bulk_create(numeric_items)
#
#     for item, cid in zip(created_numeric_items, numeric_cids):
#         per_plant = totals[cid]
#
#         plant_keys = sorted(
#             [k for k in per_plant.keys() if k],
#             key=lambda k: plant_map.get(k, "")
#         )
#
#         for pk in plant_keys:
#             inners_to_create.append(
#                 ReportItemInner(
#                     report_item=item,
#                     plant_id=pk,
#                     value=str(per_plant[pk])
#                 )
#             )
#
#         if None in per_plant:
#             inners_to_create.append(
#                 ReportItemInner(
#                     report_item=item,
#                     value=str(per_plant[None])
#                 )
#             )
#
#     if inners_to_create:
#         ReportItemInner.objects.bulk_create(inners_to_create, batch_size=1000)
#
#
# # ============================================================
# # Rebuild functions — statement parametri qo'shildi
# # ============================================================
#
# @transaction.atomic
# def rebuild_general_for_deadline(
#     statement,
#     deadline_id: str,
#     region_key: str,
#     region_reports: List[Report],
#     cache: StatementDataCache,
#     deadline_cache: DeadlineCache,
#     plant_cache: PlantCache,
#     individual_general_by_org: dict[str, Report] | None = None,
# ) -> Optional[Report]:
#     """
#     Region general reportni rebuild qilish.
#     statement parametri _sum_reports_for_general'ga uzatiladi
#     (Daromad quarter-aware logikasi uchun kerak).
#     """
#     general = _ensure_general_report(statement, deadline_id, region_key, deadline_cache)
#     if not general:
#         return None
#
#     ReportItem.objects.filter(report=general).delete()
#
#     # FIX: statement uzatiladi
#     totals = _sum_reports_for_general(
#         reports=region_reports,
#         cache=cache,
#         individual_general_by_org=individual_general_by_org,
#         statement=statement,
#     )
#
#     region_label = dict(RegionChoices.choices).get(str(region_key), str(region_key))
#     org_name_value = f"{region_label} – Viloyat Jami"
#
#     _create_report_items(
#         report=general,
#         totals=totals,
#         org_name_cols=cache.org_name_cols,
#         org_name_value=org_name_value,
#         plant_cache=plant_cache
#     )
#
#     try:
#         calculate_general_report(general)
#     except Exception as e:
#         logger.error(f"[FILTERED][GENERAL] calculate_general_report error: {e}")
#     try:
#         if getattr(general.statement, "calculate_expression", None):
#             calculate_by_expressions(general)
#     except Exception as e:
#         logger.error(f"[FILTERED][GENERAL] calculate_by_expressions error: {e}")
#
#     return Report.objects.filter(id=general.id).prefetch_related(_prefetch_items_qs()).first()
#
#
# @transaction.atomic
# def rebuild_republic_for_deadline(statement, deadline_id: str, general_reports: List[Report],
#                                   cache: StatementDataCache, deadline_cache: DeadlineCache,
#                                   plant_cache: PlantCache) -> Optional[Report]:
#     rep = _ensure_republic_report(statement, deadline_id, deadline_cache)
#     if not rep:
#         return None
#
#     ReportItem.objects.filter(report=rep).delete()
#
#     totals: Dict[str, Dict[str | None, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
#
#     for gr in general_reports:
#         for it in gr.report_items.all():
#             cid = str(it.statement_column_id)
#
#             if not cache.is_aggregatable_from_cache(cid):
#                 continue
#
#             for inn in it.inners.all():
#                 plant_key = str(inn.plant_id) if inn.plant_id else None
#                 totals[cid][plant_key] += _safe_decimal(inn.value)
#
#     _create_report_items(
#         report=rep,
#         totals=totals,
#         org_name_cols=cache.org_name_cols,
#         org_name_value="Respublika Jami",
#         plant_cache=plant_cache
#     )
#
#     try:
#         calculate_general_report(rep)
#     except Exception as e:
#         logger.error(f"[FILTERED][REPUBLIC] calculate_general_report error: {e}")
#     try:
#         if getattr(rep.statement, "calculate_expression", None):
#             calculate_by_expressions(rep)
#     except Exception as e:
#         logger.error(f"[FILTERED][REPUBLIC] calculate_by_expressions error: {e}")
#
#     return Report.objects.filter(id=rep.id).prefetch_related(_prefetch_items_qs()).first()
#
#
# # ============================================================
# # Serialization helpers (o'zgarmagan)
# # ============================================================
#
# def _serialize_report_like(rep: Report, cache: StatementDataCache, lang: str,
#                            plant_cache: PlantCache, org_name_override: Optional[str] = None) -> Dict:
#     org_name = org_name_override
#     if org_name is None:
#         if getattr(rep, "organization", None):
#             org_name = get_translated_field(rep.organization, "name", lang) or ""
#         else:
#             org_name = ""
#
#     plant_ids_all: set[str] = set()
#     for it in rep.report_items.all():
#         for inn in it.inners.all():
#             if inn.plant_id:
#                 plant_ids_all.add(str(inn.plant_id))
#
#     plant_map_all = plant_cache.get_plant_map(plant_ids_all)
#
#     statement_columns_payload = []
#     for it in rep.report_items.all():
#         col_id = str(it.statement_column_id)
#         col_name = cache.get_column_path(col_id, lang)
#
#         inners_payload = []
#         inners = list(it.inners.all())
#         inners.sort(key=lambda x: (0, plant_map_all.get(str(x.plant_id), "")) if x.plant_id else (1, ""))
#
#         for inn in inners:
#             payload = {"value": inn.value}
#             if inn.plant_id:
#                 payload["plant_id"] = str(inn.plant_id)
#                 payload["plant_name"] = plant_map_all.get(str(inn.plant_id), "")
#             inners_payload.append(payload)
#
#         statement_columns_payload.append({
#             "statement_column_id": col_id,
#             "statement_column_name": col_name,
#             "inners": inners_payload,
#         })
#
#     return {
#         "id": str(rep.id),
#         "organization": str(rep.organization_id) if rep.organization_id else None,
#         "organization_name": org_name,
#         "statement": str(rep.statement_id),
#         "deadline": str(rep.deadline_id) if rep.deadline_id else None,
#         "report_items": [
#             {
#                 "organization_id": str(rep.organization_id) if rep.organization_id else None,
#                 "organization_name": org_name,
#                 "statement_columns": statement_columns_payload,
#             }
#         ],
#         "is_general": rep.is_general,
#         "is_individual_general": rep.is_individual_general,
#         "is_republic": rep.is_republic,
#     }
#
#
# # ============================================================
# # Main payload builder (o'zgarmagan — ichida fix avtomatik ishlaydi)
# # ============================================================
#
# def build_filtered_payload(statement, deadline_id: str, lang: str) -> Dict:
#     """
#     Fully optimized version.
#     Daromad uchun quarter-aware aggregation avtomatik ishlaydi.
#     """
#     cache = StatementDataCache(str(statement.id))
#     cache.load()
#
#     deadline_cache = DeadlineCache(deadline_id)
#     plant_cache = PlantCache()
#
#     # FIX: filter_reports_by_deadline endi Daromad uchun to'g'ri ishlaydi
#     individuals = list(filter_reports_by_deadline(statement, deadline_id))
#
#     use_individual_general_plan_source = should_use_individual_general_plan_source(statement)
#     individual_general_by_org: dict[str, Report] = {}
#
#     if use_individual_general_plan_source:
#         individual_generals = list(
#             filter_individual_general_reports_by_deadline(statement, deadline_id)
#         )
#         individual_general_by_org = build_individual_general_by_org(individual_generals)
#
#     by_region: Dict[str, List[Report]] = defaultdict(list)
#     for rep in individuals:
#         region_key = str(getattr(rep.organization, "region", ""))
#         if region_key:
#             by_region[region_key].append(rep)
#
#     results = []
#     region_general_reports: List[Report] = []
#
#     for region_key, reps in by_region.items():
#         general_rep = rebuild_general_for_deadline(
#             statement=statement,
#             deadline_id=deadline_id,
#             region_key=region_key,
#             region_reports=reps,
#             cache=cache,
#             deadline_cache=deadline_cache,
#             plant_cache=plant_cache,
#             individual_general_by_org=individual_general_by_org,
#         )
#         if general_rep:
#             region_general_reports.append(general_rep)
#
#         children_payload = []
#         for r in reps:
#             r_serialized = _serialize_report_like(r, cache, lang, plant_cache)
#             children_payload.append({
#                 "id": r_serialized["id"],
#                 "organization_name": r_serialized["organization_name"],
#                 "report_items": r_serialized["report_items"],
#                 "sent_by_full_name": None,
#                 "sent_by_org_name": r_serialized["organization_name"],
#                 "sent_by_role": None,
#             })
#
#         if general_rep:
#             parent_payload = _serialize_report_like(
#                 general_rep, cache, lang, plant_cache,
#                 org_name_override=f"{region_key} – Viloyat Jami"
#             )
#             results.append({
#                 "id": parent_payload["id"],
#                 "organization_name": parent_payload["organization_name"] or f"{region_key} – Viloyat Jami",
#                 "report_items": parent_payload["report_items"],
#                 "children_reports": children_payload,
#             })
#         else:
#             results.append({
#                 "id": None,
#                 "organization_name": f"{region_key} – Viloyat Jami",
#                 "report_items": [{
#                     "organization_id": "general",
#                     "organization_name": f"{region_key} – Viloyat Jami",
#                     "statement_columns": []
#                 }],
#                 "children_reports": children_payload,
#             })
#
#     if region_general_reports:
#         republic_rep = rebuild_republic_for_deadline(
#             statement, deadline_id, region_general_reports, cache, deadline_cache, plant_cache
#         )
#         if republic_rep:
#             rep_payload = _serialize_report_like(
#                 republic_rep, cache, lang, plant_cache,
#                 org_name_override="Respublika Jami"
#             )
#             results.append({
#                 "id": rep_payload["id"],
#                 "organization_name": rep_payload["organization_name"] or "Respublika Jami",
#                 "report_items": rep_payload["report_items"],
#                 "children_reports": [],
#             })
#         else:
#             results.append({
#                 "id": None,
#                 "organization_name": "Respublika Jami",
#                 "report_items": [{
#                     "organization_id": "republic",
#                     "organization_name": "Respublika Jami",
#                     "statement_columns": []
#                 }],
#                 "children_reports": [],
#             })
#
#     return {
#         "count": len(results),
#         "next": None,
#         "previous": None,
#         "results": results,
#     }
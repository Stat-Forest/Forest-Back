import re
from uuid import UUID
from datetime import date
from collections import defaultdict

from django.db import transaction
from django.db.models import Prefetch
from rest_framework import serializers
from rest_framework.serializers import ValidationError as DRFValidationError

from apps.general.models import Organization
from apps.base.serializers import CustomSerializer
from apps.reports.models import (
    Report,
    ReportItem,
    ReportItemInner,
    StatementColumn,
    Plant,
)
from apps.reports.report_calculate import ALL_CALCULATORS
from apps.reports.serializers.plant.plant_report_list import PlantReportListSerializer
from apps.reports.services.change_coma_to_dote import normalize_decimal_input_dote
from apps.reports.services.individual_general_report import aggregate_individual_report
from apps.reports.services.quarter_validator import DaromadQuarterService
from apps.reports.services.report_calculate_expressions import calculate_by_expressions
from apps.reports.services.simple_ensure_plans import ensure_plant_plans_exist
from apps.utils.services import PeriodChoices


class PlantBasedReportItemSerializer(CustomSerializer):
    statement_column = serializers.UUIDField()
    source_report = serializers.UUIDField(required=False)
    inners = serializers.ListField(child=serializers.DictField())


class UniversalPlantReportCreateSerializer(CustomSerializer):
    deadline = serializers.UUIDField()
    quarter = serializers.ChoiceField(
        choices=Report.QuarterChoices.choices,
        required=False,
        allow_null=True,
        error_messages={
            "invalid_choice": "Noto'g'ri chorak tanlandi. I-chorak (q1), II-chorak (q2), III-chorak (q3) yoki IV-chorak (q4) ni tanlang.",
            "null": "Chorak bo'sh bo'lishi mumkin emas.",
        },
        help_text="Chorak faqat Daromad hisoboti uchun ishlatiladi. CREATE paytida faqat q1 mumkin.",
    )
    report_items = PlantBasedReportItemSerializer(many=True)

    def validate(self, attrs):
        deadline_id = attrs["deadline"]
        quarter = attrs.get("quarter")
        user = self.context["request"].user
        organization = user.organization

        from apps.reports.models import Deadline

        try:
            deadline = Deadline.objects.select_related("statement").get(id=deadline_id)
        except Deadline.DoesNotExist:
            raise DRFValidationError({"deadline": "Berilgan deadline mavjud emas."})

        statement = deadline.statement
        submit_at = deadline.submit_at
        today = date.today()

        ensure_plant_plans_exist(statement=statement, organization=organization)
        self._validate_submit_period(statement.period, submit_at, today)

        report_items = attrs.get("report_items", [])
        is_daromad = DaromadQuarterService.is_daromad_statement(statement)

        if is_daromad:
            DaromadQuarterService.validate_create(
                statement=statement,
                organization=organization,
                deadline=deadline,
                quarter=quarter,
            )

            DaromadQuarterService.validate_columns_for_quarter(
                statement=statement,
                quarter=quarter,
                column_ids=[item["statement_column"] for item in report_items],
                allow_common=True,
            )
            attrs["quarter"] = quarter
        else:
            if quarter:
                raise DRFValidationError({"quarter": "Bu hisobot uchun chorak tanlash shart emas."})

            if Report.objects.filter(
                organization=organization,
                statement=statement,
                deadline=deadline,
                is_report=True,
            ).exists():
                raise DRFValidationError({"report": "Bu hisobot allaqachon mavjud."})

        attrs["_deadline_obj"] = deadline
        attrs["_statement_obj"] = statement
        attrs["_is_daromad"] = is_daromad
        return attrs

    @staticmethod
    def _validate_submit_period(period: str, submit_at: str, today: date) -> None:
        from rest_framework.serializers import ValidationError as DRFValidationError

        def get_week_of_month(d: date) -> int:
            first_day = d.replace(day=1)
            adjusted_dom = d.day + first_day.weekday()
            return (adjusted_dom - 1) // 7 + 1

        if period == PeriodChoices.KUNLIK:
            try:
                parts = submit_at.split("-")
                report_day = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except Exception:
                raise DRFValidationError({"submit_at": "Noto'g'ri sana formati. YYYY-MM-DD bo'lishi kerak."})
            if report_day >= today:
                raise DRFValidationError({"submit_at": "Faqat o'tgan kunlar uchun topshirish mumkin."})

        elif period == PeriodChoices.HAFTALIK:
            match = re.match(r"^(?P<year>\d{4})-(?P<month>\d{2})-HAFTALIK_(?P<week>[1-4])$", submit_at)
            if not match:
                raise DRFValidationError({"submit_at": "Noto'g'ri format. YYYY-MM-HAFTALIK_x bo'lishi kerak."})
            year = int(match.group("year"))
            month = int(match.group("month"))
            week = int(match.group("week"))
            if year > today.year or (year == today.year and month > today.month):
                raise DRFValidationError({"submit_at": "Faqat o'tgan haftalar uchun topshirish mumkin."})
            if year == today.year and month == today.month and week >= get_week_of_month(today):
                raise DRFValidationError({"submit_at": "Faqat o'tgan haftalar uchun topshirish mumkin."})

        elif period == PeriodChoices.OYLIK:
            try:
                year, month = map(int, submit_at.split("-"))
            except Exception:
                raise DRFValidationError({"submit_at": "Noto'g'ri oylik format. YYYY-MM bo'lishi kerak."})
            if year > today.year or (year == today.year and month >= today.month):
                raise DRFValidationError({"submit_at": "Faqat o'tgan oylar uchun topshirish mumkin."})

        elif period == PeriodChoices.CHORAKLIK:
            match = re.match(r"^(?P<year>\d{4})-CHORAK_(?P<q>[1-4])$", submit_at)
            if not match:
                raise DRFValidationError({"submit_at": "Noto'g'ri chorak format. YYYY-CHORAK_x bo'lishi kerak."})
            year = int(match.group("year"))
            q_num = int(match.group("q"))
            cur_q = (today.month - 1) // 3 + 1
            if year > today.year or (year == today.year and q_num >= cur_q):
                raise DRFValidationError({"submit_at": "Faqat o'tgan choraklar uchun topshirish mumkin."})

        elif period == PeriodChoices.YILLIK:
            try:
                year = int(submit_at)
            except Exception:
                raise DRFValidationError({"submit_at": "Noto'g'ri yillik format. YYYY bo'lishi kerak."})
            if year >= today.year:
                raise DRFValidationError({"submit_at": "Faqat o'tgan yillar uchun topshirish mumkin."})

    @staticmethod
    def _drop_other_quarter_manual_items_from_payload(
        items_data: list,
        columns_map: dict,
        selected_quarter: str | None,
        is_daromad: bool,
    ) -> list:
        if not is_daromad or selected_quarter != "q1":
            return items_data

        current_quarter_orderings = set(
            DaromadQuarterService.get_manual_input_orderings(selected_quarter)
        )
        other_quarter_orderings = set(
            DaromadQuarterService.get_other_quarter_manual_input_orderings(selected_quarter)
        )

        filtered_items = []

        for item in items_data:
            col_id = str(item["statement_column"])
            column = columns_map.get(col_id)

            if not column:
                filtered_items.append(item)
                continue

            if getattr(column, "is_organization", False):
                filtered_items.append(item)
                continue

            if getattr(column, "status_plan", None):
                filtered_items.append(item)
                continue

            ordering = getattr(column, "ordering", None)

            if ordering in current_quarter_orderings:
                filtered_items.append(item)
                continue

            if ordering in other_quarter_orderings:
                continue

            filtered_items.append(item)

        return filtered_items

    @staticmethod
    def _normalize_plan_items_with_selected_plant(
        items_data: list,
        columns_map: dict,
        selected_plant_ids: list[str],
        is_daromad: bool,
    ) -> list:
        if not is_daromad or not selected_plant_ids:
            return items_data

        selected_plant_id = selected_plant_ids[0]
        normalized_items = []

        for item in items_data:
            col_id = str(item["statement_column"])
            column = columns_map.get(col_id)

            if not column or not getattr(column, "status_plan", None):
                normalized_items.append(item)
                continue

            normalized_inners = []
            for inner in item.get("inners", []):
                inner_copy = dict(inner)
                if not inner_copy.get("plant"):
                    inner_copy["plant"] = selected_plant_id
                normalized_inners.append(inner_copy)

            normalized_items.append({**item, "inners": normalized_inners})

        return normalized_items

    @staticmethod
    def _copy_daromad_plan_items_to_report(
        *,
        report: Report,
        statement,
        organization,
        selected_plant_ids: list[str],
    ) -> None:
        if not selected_plant_ids:
            return

        plan_columns = list(
            StatementColumn.objects.filter(
                statement=statement,
                status_plan__isnull=False,
                is_organization=False,
            ).only("id")
        )
        if not plan_columns:
            return

        plan_column_ids = [c.id for c in plan_columns]
        selected_plant_ids_set = {str(pid) for pid in selected_plant_ids}

        source_items = list(
            ReportItem.objects
            .filter(
                report__statement=statement,
                report__organization=organization,
                statement_column_id__in=plan_column_ids,
            )
            .exclude(report=report)
            .select_related("report")
            .prefetch_related(
                Prefetch(
                    "inners",
                    queryset=ReportItemInner.objects.only("id", "report_item_id", "plant_id", "value"),
                )
            )
            .only("id", "report_id", "statement_column_id", "value")
            .order_by("created_at")
        )
        if not source_items:
            return

        existing_items = {
            ri.statement_column_id: ri
            for ri in ReportItem.objects.filter(
                report=report,
                statement_column_id__in=plan_column_ids,
            ).only("id", "statement_column_id")
        }

        items_to_create = []
        for item in source_items:
            if item.statement_column_id not in existing_items:
                items_to_create.append(
                    ReportItem(
                        report=report,
                        statement_column_id=item.statement_column_id,
                        value=item.value,
                    )
                )

        if items_to_create:
            ReportItem.objects.bulk_create(items_to_create)

        report_items_map = {
            ri.statement_column_id: ri
            for ri in ReportItem.objects.filter(
                report=report,
                statement_column_id__in=plan_column_ids,
            ).only("id", "statement_column_id")
        }

        existing_inner_keys = set(
            ReportItemInner.objects.filter(
                report_item__report=report,
                report_item__statement_column_id__in=plan_column_ids,
            ).values_list("report_item__statement_column_id", "plant_id")
        )

        inners_to_create = []
        for item in source_items:
            target_report_item = report_items_map[item.statement_column_id]

            for inner in item.inners.all():
                if inner.plant_id is None:
                    continue
                if str(inner.plant_id) not in selected_plant_ids_set:
                    continue

                key = (item.statement_column_id, inner.plant_id)
                if key in existing_inner_keys:
                    continue

                inners_to_create.append(
                    ReportItemInner(
                        report_item=target_report_item,
                        plant_id=inner.plant_id,
                        value=inner.value,
                    )
                )

        if inners_to_create:
            ReportItemInner.objects.bulk_create(inners_to_create)

    @staticmethod
    def _build_calc_preloaded_data(reports: list[Report]) -> dict:
        if not reports:
            return {}

        report_ids = [r.id for r in reports]
        statement_ids = {r.statement_id for r in reports}

        columns = list(
            StatementColumn.objects
            .filter(statement_id__in=statement_ids)
            .only("id", "statement_id", "ordering", "is_organization")
        )

        columns_by_statement = defaultdict(dict)
        for c in columns:
            columns_by_statement[c.statement_id][c.ordering] = c

        report_items = list(
            ReportItem.objects
            .filter(report_id__in=report_ids)
            .only("id", "report_id", "statement_column_id")
        )

        item_ids = [it.id for it in report_items]
        inners = list(
            ReportItemInner.objects
            .filter(report_item_id__in=item_ids)
            .only("id", "report_item_id", "plant_id", "value")
        )

        items_by_report = defaultdict(dict)
        ordering_by_item_id_by_report = defaultdict(dict)

        column_lookup = {c.id: c for c in columns}
        for it in report_items:
            items_by_report[it.report_id][it.statement_column_id] = it
            col = column_lookup.get(it.statement_column_id)
            if col:
                ordering_by_item_id_by_report[it.report_id][it.id] = col.ordering

        inners_by_report = defaultdict(list)
        item_id_to_report_id = {it.id: it.report_id for it in report_items}
        for inner in inners:
            rid = item_id_to_report_id.get(inner.report_item_id)
            if rid:
                inners_by_report[rid].append(inner)

        result = {}
        for r in reports:
            result[r.id] = {
                "columns_by_ordering": columns_by_statement.get(r.statement_id, {}),
                "items_by_column_id": items_by_report.get(r.id, {}),
                "ordering_by_item_id": ordering_by_item_id_by_report.get(r.id, {}),
                "inners": inners_by_report.get(r.id, []),
            }
        return result

    @staticmethod
    def _reload_reports_for_response(report_ids: list) -> list[Report]:
        reports = list(
            Report.objects
            .filter(id__in=report_ids)
            .select_related("statement", "deadline", "organization")
            .prefetch_related(
                Prefetch(
                    "report_items",
                    queryset=ReportItem.objects
                    .select_related("statement_column")
                    .prefetch_related(
                        Prefetch(
                            "inners",
                            queryset=ReportItemInner.objects.select_related("plant"),
                        )
                    ),
                )
            )
        )

        report_by_id = {r.id: r for r in reports}
        return [report_by_id[rid] for rid in report_ids if rid in report_by_id]

    @staticmethod
    def _create_zero_quarter_items(
        report: Report,
        statement,
        selected_plant_ids: list[str],
        selected_quarter: str = "q1",
    ) -> None:
        if not selected_plant_ids:
            return

        other_orderings = DaromadQuarterService.get_other_quarter_manual_input_orderings(selected_quarter)
        if not other_orderings:
            return

        columns = list(
            StatementColumn.objects.filter(
                statement=statement,
                ordering__in=other_orderings,
                is_user_input=True,
                is_organization=False,
                status_plan__isnull=True,
            ).only("id", "ordering")
        )
        if not columns:
            return

        column_ids = [c.id for c in columns]

        existing_items = {
            ri.statement_column_id: ri
            for ri in ReportItem.objects.filter(
                report=report,
                statement_column_id__in=column_ids,
            ).only("id", "statement_column_id")
        }

        items_to_create = []
        for column in columns:
            if column.id not in existing_items:
                items_to_create.append(
                    ReportItem(
                        report=report,
                        statement_column=column,
                    )
                )

        if items_to_create:
            ReportItem.objects.bulk_create(items_to_create)

        item_map = {
            ri.statement_column_id: ri
            for ri in ReportItem.objects.filter(
                report=report,
                statement_column_id__in=column_ids,
            ).only("id", "statement_column_id")
        }

        selected_plant_ids_set = {str(pid) for pid in selected_plant_ids}

        existing_inner_keys = set(
            ReportItemInner.objects.filter(
                report_item__report=report,
                report_item__statement_column_id__in=column_ids,
            ).values_list("report_item__statement_column_id", "plant_id")
        )

        inners_to_create = []
        for column in columns:
            report_item = item_map[column.id]

            for plant_id in selected_plant_ids_set:
                key = (column.id, plant_id)
                if key in existing_inner_keys:
                    continue

                inners_to_create.append(
                    ReportItemInner(
                        report_item=report_item,
                        plant_id=plant_id,
                        value="0",
                    )
                )

        if inners_to_create:
            ReportItemInner.objects.bulk_create(inners_to_create)

    def create(self, validated_data):
        user = self.context["request"].user
        items_data = validated_data.pop("report_items")
        deadline_id = validated_data.get("deadline")
        quarter = validated_data.get("quarter")
        foot_note = validated_data.get("foot_note")

        validated_data.pop("_deadline_obj", None)
        validated_data.pop("_statement_obj", None)
        is_daromad = validated_data.pop("_is_daromad", False)

        column_ids = [item["statement_column"] for item in items_data]
        columns = list(
            StatementColumn.objects
            .filter(id__in=column_ids)
            .select_related("statement")
            .only(
                "id",
                "is_organization",
                "status_plan",
                "statement_id",
                "ordering",
                "statement__name",
                "statement__name_uz",
            )
        )
        columns_map = {str(col.id): col for col in columns}

        selected_plant_ids = set()
        plant_ids = set()
        for item in items_data:
            for inner in item.get("inners", []):
                pid = inner.get("plant")
                if pid:
                    try:
                        uid = UUID(str(pid))
                        plant_ids.add(uid)
                        selected_plant_ids.add(str(uid))
                    except Exception:
                        raise serializers.ValidationError({
                            "plant": f"Noto'g'ri plant ID formati: {pid}"
                        })

        items_data = self._normalize_plan_items_with_selected_plant(
            items_data=items_data,
            columns_map=columns_map,
            selected_plant_ids=list(selected_plant_ids),
            is_daromad=is_daromad,
        )

        items_data = self._drop_other_quarter_manual_items_from_payload(
            items_data=items_data,
            columns_map=columns_map,
            selected_quarter=quarter,
            is_daromad=is_daromad,
        )

        if plant_ids:
            existing = set(
                Plant.objects.filter(id__in=list(plant_ids)).values_list("id", flat=True)
            )
            missing = [str(p) for p in plant_ids if p not in existing]
            if missing:
                raise serializers.ValidationError({
                    "plant": f"Quyidagi plant ID(lar) topilmadi: {', '.join(missing)}"
                })

        pending_items_map = {}
        inners_by_key = {}
        reports_map = {}
        org_cache = {}
        report_ids_in_order = []

        with transaction.atomic():
            for item in items_data:
                col_id = str(item["statement_column"])
                column = columns_map.get(col_id)
                if not column:
                    raise serializers.ValidationError(f"Column {col_id} topilmadi.")

                inners = item.get("inners", [])

                if column.is_organization:
                    if any(inner.get("plant") for inner in inners):
                        raise serializers.ValidationError({
                            "plant": "Tashkilot ustunida plant yuborish taqiqlanadi."
                        })

                    if not inners or not inners[0].get("value"):
                        raise serializers.ValidationError("Tashkilot ID kiritilishi kerak.")

                    org_id = inners[0]["value"]
                    try:
                        UUID(str(org_id))
                    except Exception:
                        raise serializers.ValidationError(f"Noto'g'ri tashkilot ID formati: {org_id}")

                    # Tashkilot body'dan olinadi, lekin faqat foydalanuvchining o'z
                    # tashkiloti bo'lishi mumkin (audit N1: boshqa tashkilot nomidan hisobot)
                    if (
                        not user.is_superuser
                        and getattr(user, "organization_id", None)
                        and str(org_id) != str(user.organization_id)
                    ):
                        raise serializers.ValidationError(
                            "Hisobotni faqat o'z tashkilotingiz uchun yaratish mumkin."
                        )

                    current_org = org_cache.get(str(org_id))
                    if current_org is None:
                        try:
                            current_org = Organization.objects.only("id", "region").get(id=org_id)
                            org_cache[str(org_id)] = current_org
                        except Organization.DoesNotExist:
                            raise serializers.ValidationError(f"Tashkilot topilmadi: {org_id}")

                    report_key = (current_org.id, column.statement_id)
                    if report_key not in reports_map:
                        report = self._create_report(
                            user=user,
                            org=current_org,
                            statement=column.statement,
                            deadline_id=deadline_id,
                            foot_note=foot_note,
                            quarter=quarter,
                            is_daromad=DaromadQuarterService.is_daromad_statement(column.statement),
                        )
                        reports_map[report_key] = report
                        report_ids_in_order.append(report.id)

                    report = reports_map[report_key]
                    key = (report.id, column.id)

                    if key not in pending_items_map:
                        pending_items_map[key] = ReportItem(
                            report=report,
                            statement_column_id=column.id,
                        )

                    inners_by_key.setdefault(key, []).append({
                        "value": str(org_id),
                        "plant_id": None,
                    })
                    continue

                if not org_cache:
                    raise serializers.ValidationError(
                        "Tashkilot aniqlanmagan. Iltimos, avval 'Tashkilot nomi' column'ini yuboring."
                    )

                current_org = next(iter(org_cache.values()))
                report_key = (current_org.id, column.statement_id)

                if report_key not in reports_map:
                    report = self._create_report(
                        user=user,
                        org=current_org,
                        statement=column.statement,
                        deadline_id=deadline_id,
                        foot_note=foot_note,
                        quarter=quarter,
                        is_daromad=DaromadQuarterService.is_daromad_statement(column.statement),
                    )
                    reports_map[report_key] = report
                    report_ids_in_order.append(report.id)

                report = reports_map[report_key]
                key = (report.id, column.id)

                if key not in pending_items_map:
                    pending_items_map[key] = ReportItem(
                        report=report,
                        statement_column_id=column.id,
                    )

                for inner in inners:
                    normalized = normalize_decimal_input_dote(inner.get("value"))
                    inners_by_key.setdefault(key, []).append({
                        "value": normalized,
                        "plant_id": inner.get("plant"),
                    })

            if pending_items_map:
                ReportItem.objects.bulk_create(list(pending_items_map.values()))

            if pending_items_map:
                keys = list(pending_items_map.keys())
                report_ids = {rid for rid, _ in keys}
                col_ids_set = {cid for _, cid in keys}

                item_map = {
                    (ri.report_id, ri.statement_column_id): ri
                    for ri in ReportItem.objects.filter(
                        report_id__in=report_ids,
                        statement_column_id__in=col_ids_set,
                    ).only("id", "report_id", "statement_column_id")
                }

                inners_buffer = []
                for key, inners_list in inners_by_key.items():
                    report_item = item_map[key]
                    for inner in inners_list:
                        inners_buffer.append(
                            ReportItemInner(
                                report_item=report_item,
                                plant_id=inner.get("plant_id"),
                                value=inner.get("value"),
                            )
                        )

                if inners_buffer:
                    ReportItemInner.objects.bulk_create(inners_buffer)

            for report in reports_map.values():
                if DaromadQuarterService.is_daromad_statement(report.statement):
                    self._copy_daromad_plan_items_to_report(
                        report=report,
                        statement=report.statement,
                        organization=report.organization,
                        selected_plant_ids=list(selected_plant_ids),
                    )

            for report in reports_map.values():
                if DaromadQuarterService.is_daromad_statement(report.statement) and quarter == "q1":
                    self._create_zero_quarter_items(
                        report=report,
                        statement=report.statement,
                        selected_plant_ids=list(selected_plant_ids),
                        selected_quarter="q1",
                    )

            calc_pre_map = self._build_calc_preloaded_data(list(reports_map.values()))

            for report in reports_map.values():
                statement = report.statement
                if func := ALL_CALCULATORS.get(statement.name_uz):
                    if statement.name_uz == "Daromad":
                        func(report, pre=calc_pre_map.get(report.id))
                    else:
                        func(report)
                elif statement.calculate_expression:
                    calculate_by_expressions(report)

                aggregate_individual_report(report)

        self.instance = self._reload_reports_for_response(report_ids_in_order)
        return self.instance

    @staticmethod
    def _create_report(
        user,
        org,
        statement,
        deadline_id,
        foot_note,
        quarter,
        is_daromad: bool,
    ) -> Report:
        report = Report(
            organization=org,
            statement=statement,
            deadline_id=deadline_id,
            region=org.region,
            status=Report.StatusChoices.SAVED,
            is_plant_based=True,
            created_by=user,
            foot_note=foot_note,
        )

        if is_daromad and quarter:
            DaromadQuarterService.prepare_report_for_create(report=report, quarter=quarter)

        if is_daromad:
            report.save(update_fields=[
                "organization",
                "statement",
                "deadline",
                "region",
                "status",
                "is_plant_based",
                "created_by",
                "foot_note",
                "quarter",
                "current_quarter",
                "quarter_1_status",
                "quarter_status_dates",
            ])
        else:
            report.save()

        return report

    def to_representation(self, instance_list):
        return [
            PlantReportListSerializer(
                report,
                context={"request": self.context.get("request")},
            ).data
            for report in instance_list
        ]
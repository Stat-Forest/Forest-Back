from rest_framework import serializers


class ReportExcelExportRequestSerializer(serializers.Serializer):
    report_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="Export qilinadigan report ID lar ro‘yxati"
    )
    lang = serializers.ChoiceField(
        choices=["uz", "ru"],
        default="uz",
        help_text="Til (uz / ru)"
    )
    mode = serializers.ChoiceField(
        choices=["json"],
        required=False,
        help_text="Agar 'json' bo‘lsa, download_url qaytariladi"
    )
    # Optional: hierarchical row numbers mapping for aggregated summary screens
    # Example: {"<report_id>": "1", "<child_report_id>": "1.1"}
    row_numbers = serializers.DictField(
        child=serializers.CharField(), required=False, help_text="Hisoblangan ierarxik qator raqamlari"
    )
    # Optional: explicitly tell backend that this is aggregated (regional/national) screen
    aggregated = serializers.BooleanField(required=False, default=None)

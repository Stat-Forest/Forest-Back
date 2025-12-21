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

from rest_framework import serializers
from apps.base.serializers import CustomSerializer


class MonitoringExportSerializer(CustomSerializer):
    region = serializers.CharField(
        required=False,
        help_text="Region kodi (ANDIJON, TOSHKENT, ...)"
    )
    organization = serializers.UUIDField(
        required=False,
        help_text="Organization UUID"
    )
    period = serializers.CharField(
        required=False,
        help_text="Davr: 2025, 2025-CHORAKLIK_1, 2025-01"
    )
    lang = serializers.ChoiceField(
        choices=["uz", "ru"],
        default="uz",
        required=False,
        help_text="Til (uz/ru)"
    )
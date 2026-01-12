from rest_framework import serializers

from apps.base.serializers import CustomSerializer


class PlantSvodkaQuerySerializer(CustomSerializer):
    """
    Query serializer for Plant Svodka API.

    Used only for:
    - Browsable API (HTML form)
    - Query params validation
    """

    statement = serializers.UUIDField(
        required=True,
        help_text="Statement ID (UUID)"
    )

    plant = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Optional Plant ID (UUID)"
    )

    lang = serializers.ChoiceField(
        choices=["uz", "ru"],
        required=False,
        allow_null=True,
        help_text="Language code (uz or ru)"
    )

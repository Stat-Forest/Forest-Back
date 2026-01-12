from rest_framework import serializers

from apps.base.serializers import CustomSerializer


class StatementAppendicesQuerySerializer(CustomSerializer):
    statement = serializers.UUIDField(
        required=True,
        help_text="Statement ID (UUID)",
    )
    lang = serializers.ChoiceField(
        choices=["uz", "ru"],
        required=False,
        allow_null=True,
        help_text="Language code (uz or ru)",
    )

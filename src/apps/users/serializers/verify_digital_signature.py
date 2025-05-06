from datetime import datetime

from django.utils.timezone import make_aware
from rest_framework import serializers

from apps.users.models import Position, DigitalSignatureProfile
from apps.general.models import Organization
from apps.base.serializers import CustomSerializer
from apps.base.exceptions.exception_files import CustomExceptionError
from apps.utils.integration_users.verify_mygov import verify_signature_with_my_gov


class VerifyDigitalSignatureSerializer(CustomSerializer):
    pinfl = serializers.CharField(min_length=14, max_length=14)
    sign_data = serializers.CharField()
    signature = serializers.CharField()

    def validate(self, attrs):
        response_data = verify_signature_with_my_gov(
            signature=attrs["signature"],
            sign_data=attrs["sign_data"],
            pinfl=attrs["pinfl"]
        )

        if not response_data.get("valid"):
            raise CustomExceptionError(code=400, detail="Digital signature is invalid")

        attrs["my_gov_data"] = response_data
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        data = self.validated_data["my_gov_data"]

        org, _ = Organization.objects.get_or_create(name=data.get("organization"))

        position = None

        if data.get("position"):
            profile, _ = Position.objects.get_or_create(name=data.get("position"))


        profile, _ = DigitalSignatureProfile.objects.update_or_create(
            user=user,
            defaults={
                "tin": data["pinfl"],
                "certificate_serial_number": data["serialNumber"],
                "certificate_expiry": make_aware(datetime.strptime(data["validTo"], "%Y-%m-%d")),
                "organization_name": org,
                "position": position,
            }
        )
        return profile

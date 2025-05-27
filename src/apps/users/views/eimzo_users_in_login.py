from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.users.serializers.verify_digital_signature import VerifyDigitalSignatureSerializer


class VerifyDigitalSignatureAPIView(APIView):

    def post(self, request):
        serializer = VerifyDigitalSignatureSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()

        return Response({
            "message": "Successfully verified and saved",
            "tin": profile.tin,
            "organization": profile.organization_name.name,
            "expires_at": profile.certificate_expiry.strftime('%Y-%m-%d'),
        }, status=status.HTTP_200_OK)
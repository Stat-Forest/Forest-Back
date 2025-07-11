from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import EimzoLoginSerializer
from .services import verify_pkcs7
from .utils import generate_user_email_and_password_fn
from apps.general.models import Organization
from apps.users.models import CustomUser


User = get_user_model()


class EimzoJWTLoginView(APIView):
    def post(self, request):
        serializer = EimzoLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vo = serializer.validated_data['vo']
        pkcs7 = serializer.validated_data['pkcs7']

        if not verify_pkcs7(pkcs7, vo):
            return Response({"detail": "Imzo noto‘g‘ri yoki noto‘liq."}, status=status.HTTP_400_BAD_REQUEST)

        full_name = vo.get("cn", "")
        name = vo.get("name", "")
        surname = vo.get("surname", "")
        uid = vo.get("uid") or vo.get("1.2.860.3.16.1.2")
        legal_stir = vo.get("1.2.860.3.16.1.1", "")
        legal_name = vo.get("o", "").upper()

        email = f"{uid}@example.com"
        logpass = generate_user_email_and_password_fn(name, surname)

        mid_name = ""
        full_parts = full_name.split()
        if len(full_parts) > 2:
            mid_name = " ".join(full_parts[2:])

        organization = None
        if legal_stir and legal_name:
            organization = Organization.objects.filter(stir=legal_stir).first()
            if not organization:
                return Response({'detail': gettext_lazy('Tashkilot topilmadi')}, status=404)


        user, _ = User.objects.update_or_create(
            email=email,
            defaults={
                "pin": vo.get("1.2.860.3.16.1.2"),
                "first_name": name.upper(),
                "last_name": surname.upper(),
                "father_name": mid_name.upper(),
                "full_name": full_name.upper(),
                "nationality": vo.get("c", "").upper(),
                "is_legal_entity": bool(legal_stir),
                "organization": organization,
                "is_active": True,
                "role": CustomUser.Role.BOLIM_ADMIN,
            }
        )

        user.set_password(logpass["password"])
        user.save()

        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "organization":user.organization
            }
        }, status=status.HTTP_200_OK)

from django.urls import path

from apps.users.views.eimzo_users_in_login import VerifyDigitalSignatureAPIView


urlpatterns = [
    path("verify-digital-signature/", VerifyDigitalSignatureAPIView.as_view())
]
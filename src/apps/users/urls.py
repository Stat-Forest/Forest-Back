from django.urls import path

from apps.base.views import CustomListAPIView
from apps.users.views.eimzo_users_in_login import VerifyDigitalSignatureAPIView


urlpatterns = [
    path("verify-digital-signature/", VerifyDigitalSignatureAPIView.as_view()),
    path("user-test/", CustomListAPIView.as_view())
]
from django.urls import path

from rest_framework_simplejwt.views import TokenObtainPairView

from apps.authentications.views import LoginAPIView


urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="login")
]
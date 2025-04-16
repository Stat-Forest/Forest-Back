from django.urls import path

from apps.authentications.views import LoginAPIView

urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="login")
]
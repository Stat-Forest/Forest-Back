from django.urls import path

from apps.authentications.views.logins import LoginAPIView
from apps.authentications.views.change_passwords import ChangePasswordAPIView
from apps.authentications.views.forgot_passwords import (
    SendResetCodeAPIView,
    VerifyCodeAPIView,
    NewPasswordAPIView,
)


urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),

    # Forgot password flow:
    path('forgot-password/send-code/', SendResetCodeAPIView.as_view(), name='send_reset_code'),
    path('forgot-password/verify-code/', VerifyCodeAPIView.as_view(), name='verify_reset_code'),
    path('forgot-password/new-password/', NewPasswordAPIView.as_view(), name='set_new_password'),

    path("change-password/", ChangePasswordAPIView.as_view(), name="change-password"),
]

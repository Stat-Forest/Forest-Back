# src/apps/e_imzo/urls.py
from django.urls import path
from .views import (
    EimzoChallengeView,
    EimzoLoginView,
    SavePkcsView,
    PkcsVerify,
)

urlpatterns = [
    # Login flow
    path("challenge/", EimzoChallengeView.as_view(), name="e-imzo-challenge"),
    path("login/", EimzoLoginView.as_view(), name="e-imzo-login"),

    # Qo'shimcha
    path("save-pkcs7/", SavePkcsView.as_view(), name="save-pkcs7"),
    path("verify-pkcs7/", PkcsVerify.as_view(), name="verify-pkcs7"),
]
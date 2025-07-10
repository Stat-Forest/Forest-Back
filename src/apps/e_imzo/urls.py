from django.urls import path
from .views import EimzoJWTLoginView

urlpatterns = [
    path("", EimzoJWTLoginView.as_view(), name="eimzo-jwt-login")
]

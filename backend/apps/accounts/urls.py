"""Account-domain routes — Step 3.01 auth + Step 3.02 driver assets."""

from django.urls import path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import (
    AccreditationViewSet,
    LoginView,
    MeView,
    OtpRequestView,
    OtpVerifyView,
    RegisterView,
    VehicleViewSet,
)

router = SimpleRouter()
router.register("driver/vehicles", VehicleViewSet, basename="driver-vehicles")
router.register("driver/accreditations", AccreditationViewSet, basename="driver-accreditations")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/otp/request/", OtpRequestView.as_view(), name="otp-request"),
    path("auth/otp/verify/", OtpVerifyView.as_view(), name="otp-verify"),
    *router.urls,
]
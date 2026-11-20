"""Account-API views. Thin wrappers over RegistrationService and OtpService."""

from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.models import Accreditation, Vehicle
from apps.accounts.permissions import IsDriver
from apps.accounts.serializers import (
    AccreditationSerializer,
    OtpRequestSerializer,
    OtpVerifySerializer,
    RegisterSerializer,
    SakayTokenObtainPairSerializer,
    VehicleSerializer,
)
from apps.accounts.services import (
    OtpError,
    OtpService,
    RegistrationError,
    RegistrationService,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = RegistrationService.register(**serializer.validated_data)
        except RegistrationError as exc:
            return Response({exc.field: [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        refresh = SakayTokenObtainPairSerializer.get_token(user)
        return Response(
            {
                "user": {
                    "id": str(user.id),
                    "phone": user.phone,
                    "full_name": user.full_name,
                    "user_role": user.user_role,
                },
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """Phone + password in, JWT pair out.

    The default `IsAuthenticated` permission does not apply — SimpleJWT's own
    views ship `AllowAny`.
    """

    serializer_class = SakayTokenObtainPairSerializer


class MeView(APIView):
    """The authenticated caller's own account, with its subtype profile."""

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        user = request.user
        data = {
            "id": str(user.id),
            "phone": user.phone,
            "full_name": user.full_name,
            "user_role": user.user_role,
            "account_status": user.account_status,
        }
        if user.is_passenger:
            pax = user.passenger_profile
            data["profile"] = {
                "home_address": pax.home_address,
                "gcash_number": pax.gcash_number,
            }
        elif user.is_driver:
            drv = user.driver_profile
            data["profile"] = {
                "license_number": drv.license_number,
                "accreditation_status": drv.accreditation_status,
                "is_online": drv.is_online,
            }
        return Response(data)


class OtpRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=OtpRequestSerializer,
        responses={200: OpenApiTypes.OBJECT, 429: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = OtpRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            code = OtpService.request_code(serializer.validated_data["phone"])
        except OtpError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        payload = {
            "detail": "A verification code was sent.",
            "expires_in": settings.OTP_TTL_SECONDS,
        }
        # D-14: the simulated gateway hands the code back — but only in DEBUG,
        # so a production deployment never leaks codes into responses.
        if settings.DEBUG and settings.SIMULATE_OTP:
            payload["debug_code"] = code
        return Response(payload)


class OtpVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=OtpVerifySerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = OtpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verified = OtpService.verify(**serializer.validated_data)
        if not verified:
            return Response(
                {"code": ["Invalid or expired code."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"verified": True})


class VehicleViewSet(viewsets.ModelViewSet):
    """A driver's vehicle. The driver is always the caller — never a body field."""

    permission_classes = [IsDriver]
    serializer_class = VehicleSerializer

    def get_queryset(self):
        return Vehicle.objects.filter(driver=self.request.user.driver_profile)

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user.driver_profile)


class AccreditationViewSet(viewsets.ModelViewSet):
    """Sertipikadong Manong — a driver's own LGU badges."""

    permission_classes = [IsDriver]
    serializer_class = AccreditationSerializer

    def get_queryset(self):
        return Accreditation.objects.filter(driver=self.request.user.driver_profile)

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user.driver_profile)
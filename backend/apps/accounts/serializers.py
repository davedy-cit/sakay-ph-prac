"""Account-API serializers.

A serializer validates input *shape*. The role-conditional "a driver needs a
license number" checks here are shape checks — the rules about *what a valid
account is* (password policy, uniqueness, profile creation) live in
RegistrationService.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import PHONE_VALIDATOR, Accreditation, LGUUnit, Vehicle
from apps.core.enums import UserRole
from apps.rides.models import RideModeLookup


class SakayTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login by phone (the USERNAME_FIELD) with domain claims in the payload."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["user_role"] = user.user_role
        token["full_name"] = user.full_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": str(self.user.id),
            "phone": self.user.phone,
            "full_name": self.user.full_name,
            "user_role": self.user.user_role,
        }
        return data


class RegisterSerializer(serializers.Serializer):
    """Shape of a registration request. `role` picks the subtype profile."""

    phone = serializers.CharField(max_length=15)
    password = serializers.CharField(min_length=8, write_only=True)
    full_name = serializers.CharField(max_length=120)
    role = serializers.ChoiceField(choices=[UserRole.PASSENGER, UserRole.DRIVER])

    home_address = serializers.CharField(max_length=255, required=False)
    gcash_number = serializers.CharField(max_length=15, required=False)
    license_number = serializers.CharField(max_length=30, required=False)

    def validate_phone(self, value):
        PHONE_VALIDATOR(value)  # raises ValidationError on a bad number
        return value

    def validate(self, attrs):
        role = attrs["role"]
        if role == UserRole.PASSENGER and not all(
            attrs.get(f) for f in ("home_address", "gcash_number")
        ):
            raise serializers.ValidationError(
                {"home_address": "A passenger registration needs home_address and gcash_number."}
            )
        if role == UserRole.DRIVER and not attrs.get("license_number"):
            raise serializers.ValidationError(
                {"license_number": "A driver registration needs license_number."}
            )
        # Password policy is also shape here — the service re-checks it.
        # Wrapped so the 400 is keyed to `password`, not `non_field_errors`.
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs


class OtpRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)

    def validate_phone(self, value):
        PHONE_VALIDATOR(value)
        return value


class OtpVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(min_length=6, max_length=6)


class VehicleSerializer(serializers.ModelSerializer):
    mode = serializers.SlugRelatedField(
        slug_field="mode_code", queryset=RideModeLookup.objects.all()
    )
    driver = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = ["id", "driver", "mode", "plate_number", "model",
                  "capacity", "route_info"]
        read_only_fields = ["id", "driver"]

    def get_driver(self, obj):
        return obj.driver.user.full_name


class AccreditationSerializer(serializers.ModelSerializer):
    lgu = serializers.SlugRelatedField(
        slug_field="lgu_code", queryset=LGUUnit.objects.all()
    )
    driver = serializers.SerializerMethodField()
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Accreditation
        fields = ["id", "driver", "lgu", "badge_no", "status",
                  "expiry_date", "badge_visible", "is_valid"]
        read_only_fields = ["id", "driver"]

    def get_driver(self, obj):
        return obj.driver.user.full_name

    def validate_expiry_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("The badge's expiry date is in the past.")
        return value

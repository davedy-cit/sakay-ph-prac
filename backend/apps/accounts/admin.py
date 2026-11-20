from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm

from .models import Accreditation, Driver, LGUUnit, Passenger, User, Vehicle


class UserAdminCreationForm(UserCreationForm):
    """Admin form for creating users: phone is the identifier, not username."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("phone", "full_name", "user_role")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """USER uses phone, not username, so the base class's fieldsets need
    rewriting — the defaults reference fields this model does not have."""

    add_form = UserAdminCreationForm

    ordering = ["full_name"]
    list_display = ["full_name", "phone", "user_role", "account_status", "is_staff"]
    list_filter = ["user_role", "account_status", "is_staff"]
    search_fields = ["full_name", "phone", "email"]
    readonly_fields = ["id", "last_login", "registration_date"]

    fieldsets = (
        (None, {"fields": ("id", "phone", "password")}),
        ("Personal", {"fields": ("full_name", "email")}),
        ("Sakay.ph", {"fields": ("user_role", "account_status", "registration_date")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups")}),
        ("Dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "full_name", "user_role", "password1", "password2"),
            },
        ),
    )


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = ["user", "home_address", "gcash_number", "verified_at"]
    search_fields = ["user__full_name", "user__phone", "gcash_number"]
    autocomplete_fields = ["user"]


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ["user", "license_number", "accreditation_status", "is_online",
                    "rating", "total_trips"]
    list_filter = ["accreditation_status", "is_online"]
    search_fields = ["user__full_name", "user__phone", "license_number"]
    autocomplete_fields = ["user"]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["plate_number", "model", "mode", "driver", "capacity"]
    list_filter = ["mode"]
    search_fields = ["plate_number", "model", "driver__user__full_name"]
    autocomplete_fields = ["driver"]


@admin.register(LGUUnit)
class LGUUnitAdmin(admin.ModelAdmin):
    list_display = ["lgu_code", "lgu_name", "province", "region"]
    list_filter = ["region", "province"]
    search_fields = ["lgu_code", "lgu_name"]


@admin.register(Accreditation)
class AccreditationAdmin(admin.ModelAdmin):
    list_display = ["badge_no", "driver", "lgu", "status", "expiry_date", "badge_visible"]
    list_filter = ["status", "lgu", "badge_visible"]
    search_fields = ["badge_no", "driver__user__full_name"]
    autocomplete_fields = ["driver", "lgu"]

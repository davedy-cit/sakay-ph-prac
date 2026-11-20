from django.contrib import admin

from .models import (
    Cancellation, Location, PakyawanGroup, PassengerPreferredMode, Rating,
    Ride, RideLeg, RideModeLookup, SurgePeriod, TripTracking,
)


@admin.register(RideModeLookup)
class RideModeLookupAdmin(admin.ModelAdmin):
    list_display = ["mode_code", "mode_name", "base_fare", "per_km_rate",
                    "seat_capacity", "is_shared"]
    list_filter = ["is_shared"]
    search_fields = ["mode_code", "mode_name"]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["street", "barangay", "city", "province", "landmark"]
    list_filter = ["city", "province"]
    search_fields = ["street", "barangay", "city", "landmark"]


class RideLegInline(admin.TabularInline):
    """Legs are edited inside the ride — a leg has no standalone identity,
    which is exactly what a weak entity means in a UI."""
    model = RideLeg
    extra = 0
    fields = ["leg_no", "mode", "driver", "origin_location", "dest_location",
              "fare", "distance_km", "eta_minutes", "surge", "status"]


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ["short_id", "passenger", "driver", "mode", "status",
                    "is_trip_chain", "leg_count", "fare_estimate", "request_time"]
    list_filter = ["status", "mode", "is_trip_chain"]
    search_fields = ["id", "passenger__user__full_name", "passenger__user__phone"]
    readonly_fields = ["id", "request_time"]
    autocomplete_fields = ["passenger", "driver", "vehicle", "mode",
                           "pickup_location", "dropoff_location"]
    inlines = [RideLegInline]
    date_hierarchy = "request_time"

    @admin.display(description="Ride")
    def short_id(self, obj):
        return str(obj.id)[:8]


@admin.register(RideLeg)
class RideLegAdmin(admin.ModelAdmin):
    list_display = ["ride", "leg_no", "mode", "driver", "fare", "status"]
    list_filter = ["status", "mode"]
    autocomplete_fields = ["ride", "mode", "driver", "origin_location",
                           "dest_location", "surge"]


@admin.register(SurgePeriod)
class SurgePeriodAdmin(admin.ModelAdmin):
    list_display = ["surge_label", "trigger_type", "multiplier", "lgu",
                    "starts_at", "ends_at", "is_active"]
    list_filter = ["trigger_type", "is_active", "lgu"]
    search_fields = ["surge_label"]


@admin.register(PakyawanGroup)
class PakyawanGroupAdmin(admin.ModelAdmin):
    list_display = ["direction", "ride", "matched_seats", "max_seats", "group_status"]
    list_filter = ["group_status"]
    search_fields = ["ride__id"]
    autocomplete_fields = ["ride"]


@admin.register(PassengerPreferredMode)
class PassengerPreferredModeAdmin(admin.ModelAdmin):
    list_display = ["passenger", "mode", "preferred_rank"]
    autocomplete_fields = ["passenger", "mode"]


@admin.register(TripTracking)
class TripTrackingAdmin(admin.ModelAdmin):
    list_display = ["track_id", "ride", "latitude", "longitude", "recorded_at"]
    list_filter = ["recorded_at"]
    autocomplete_fields = ["ride"]


@admin.register(Cancellation)
class CancellationAdmin(admin.ModelAdmin):
    list_display = ["ride", "cancelled_by", "reason_code", "fee_amount",
                    "refund_amount", "cancelled_at"]
    list_filter = ["reason_code"]
    autocomplete_fields = ["ride", "cancelled_by"]


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ["ride", "rater_user", "ratee_user", "stars", "rated_at"]
    list_filter = ["stars"]
    search_fields = ["rater_user__full_name", "ratee_user__full_name"]
    autocomplete_fields = ["ride", "rater_user", "ratee_user"]

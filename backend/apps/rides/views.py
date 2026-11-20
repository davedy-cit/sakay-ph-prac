"""Ride-domain endpoints — thin CRUD over the Phase 2 models."""

from django.db.models import ProtectedError
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.accounts.models import LGUUnit
from apps.rides.models import Location, RideModeLookup
from apps.rides.serializers import (
    LGUUnitSerializer, LocationSerializer, RideModeSerializer,
)


class ProtectedDestroyMixin:
    """Turns the models' PROTECT foreign keys into a clean 409.

    LOCATION is referenced by RIDE with on_delete=PROTECT. Without this
    mixin, deleting a referenced location surfaces Django's raw 500; with
    it, the client learns the row is load-bearing.
    """

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "This row is referenced by other records and cannot be deleted."},
                status=status.HTTP_409_CONFLICT,
            )


class LocationViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class RideModeViewSet(viewsets.ReadOnlyModelViewSet):
    """The rate card. Lookup by mode_code — /api/modes/TRICYCLE/."""

    queryset = RideModeLookup.objects.all()
    serializer_class = RideModeSerializer
    lookup_field = "mode_code"


class LGUUnitViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LGUUnit.objects.all()
    serializer_class = LGUUnitSerializer
    lookup_field = "lgu_code"
"""Core-entity API tests — Step 3.02: locations, modes, LGUs, driver assets."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Accreditation, Vehicle


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def pax_api(api, passenger_user):
    api.force_authenticate(user=passenger_user)
    return api


@pytest.fixture
def driver_api(api, driver_user):
    api.force_authenticate(user=driver_user)
    return api


LOCATION_PAYLOAD = {
    "street": "12 Rizal St", "barangay": "Poblacion", "city": "Cabuyao",
    "province": "Laguna", "latitude": "14.276400", "longitude": "121.124500",
}


# ── Locations ─────────────────────────────────────────────────

def test_locations_require_authentication(api):
    assert api.post("/api/locations/", LOCATION_PAYLOAD, format="json").status_code == 401


def test_location_create_and_retrieve(pax_api):
    response = pax_api.post("/api/locations/", LOCATION_PAYLOAD, format="json")
    assert response.status_code == 201, response.data
    detail = pax_api.get(f"/api/locations/{response.data['id']}/")
    assert detail.status_code == 200
    assert detail.data["city"] == "Cabuyao"


def test_location_rejects_an_out_of_range_latitude(pax_api):
    payload = {**LOCATION_PAYLOAD, "latitude": "999"}
    response = pax_api.post("/api/locations/", payload, format="json")
    assert response.status_code == 400
    assert "latitude" in response.data


def test_location_delete_without_references(pax_api):
    created = pax_api.post("/api/locations/", LOCATION_PAYLOAD, format="json")
    assert pax_api.delete(f"/api/locations/{created.data['id']}/").status_code == 204


def test_location_delete_referenced_by_a_ride(pax_api, locations, ride):
    home, _, _ = locations
    response = pax_api.delete(f"/api/locations/{home.id}/")
    assert response.status_code == 409
    assert "referenced" in response.data["detail"]


# ── Lookups are read-only ─────────────────────────────────────

def test_ride_modes_are_listed_but_not_writable(pax_api, tricycle):
    assert pax_api.get("/api/modes/").status_code == 200
    assert pax_api.post("/api/modes/", {}, format="json").status_code == 405


def test_ride_mode_retrieves_by_code_with_the_booking_fee(pax_api, tricycle):
    response = pax_api.get("/api/modes/TRICYCLE/")
    assert response.status_code == 200
    assert response.data["booking_fee"] == "3.00"   # D-64, read from the row


def test_lgus_are_listed(pax_api, lgu):
    response = pax_api.get("/api/lgus/")
    assert response.status_code == 200
    assert response.data["count"] == 1


# ── Driver-scoped assets ──────────────────────────────────────

def test_passenger_cannot_create_a_vehicle(pax_api, tricycle):
    payload = {"mode": tricycle.mode_code, "plate_number": "PAX 0001", "model": "Honda TMX"}
    assert pax_api.post("/api/driver/vehicles/", payload, format="json").status_code == 403


def test_driver_registers_a_vehicle_with_driver_assigned(driver_api, driver, tricycle):
    payload = {"mode": tricycle.mode_code, "plate_number": "ABC 1234",
               "model": "Honda TMX", "capacity": 3}
    response = driver_api.post("/api/driver/vehicles/", payload, format="json")
    assert response.status_code == 201, response.data
    vehicle = Vehicle.objects.get(plate_number="ABC 1234")
    assert vehicle.driver == driver
    listed = driver_api.get("/api/driver/vehicles/").data["results"]
    assert [v["plate_number"] for v in listed] == ["ABC 1234"]


def test_driver_records_an_lgu_badge(driver_api, driver, lgu):
    payload = {"lgu": lgu.lgu_code, "badge_no": "BDG-9001", "status": "VERIFIED",
               "expiry_date": str(timezone.localdate() + timedelta(days=365))}
    response = driver_api.post("/api/driver/accreditations/", payload, format="json")
    assert response.status_code == 201, response.data
    assert response.data["is_valid"] is True
    assert Accreditation.objects.filter(driver=driver, badge_no="BDG-9001").exists()


def test_accreditation_rejects_a_past_expiry(driver_api, lgu):
    payload = {"lgu": lgu.lgu_code, "badge_no": "BDG-9002", "status": "VERIFIED",
               "expiry_date": str(timezone.localdate() - timedelta(days=1))}
    response = driver_api.post("/api/driver/accreditations/", payload, format="json")
    assert response.status_code == 400
    assert "expiry_date" in response.data


def test_accreditation_rejects_an_unknown_lgu(driver_api):
    payload = {"lgu": "NOPE-XX", "badge_no": "BDG-9003",
               "expiry_date": str(timezone.localdate() + timedelta(days=30))}
    response = driver_api.post("/api/driver/accreditations/", payload, format="json")
    assert response.status_code == 400


# ── The M3 proof surface ──────────────────────────────────────

def test_the_schema_and_swagger_render(pax_api):
    schema = pax_api.get("/api/schema/")
    assert schema.status_code == 200
    assert schema["Content-Type"].startswith("application/vnd.oai.openapi")
    # The auth endpoints from Step 3.01 must appear with their request bodies.
    assert "/api/auth/login/" in schema.content.decode()
    assert pax_api.get("/api/docs/").status_code == 200
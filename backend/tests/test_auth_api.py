"""Auth-API tests — Step 3.01's acceptance checks, over HTTP."""

from django.core.cache import cache
from rest_framework.test import APIClient

import pytest

from apps.accounts.models import Driver, Passenger, User

PAX_PAYLOAD = {
    "phone": "09171110000",
    "password": "sakay-test-1234",
    "full_name": "Maria Santos",
    "role": "PASSENGER",
    "home_address": "12 Rizal St",
    "gcash_number": "09171110000",
}


@pytest.fixture(autouse=True)
def clean_cache():
    """Redis is not a database — pytest-django cannot roll it back, so every
    test starts with an empty cache (codes, cooldowns)."""
    cache.clear()
    yield


@pytest.fixture
def api():
    return APIClient()


def _register(api, **overrides):
    return api.post("/api/auth/register/", {**PAX_PAYLOAD, **overrides}, format="json")


# ── Registration ───────────────────────────────────────────────


@pytest.mark.django_db
def test_register_passenger_creates_user_and_profile(api):
    response = _register(api)
    assert response.status_code == 201, response.data
    assert "access" in response.data and "refresh" in response.data
    user = User.objects.get(phone=PAX_PAYLOAD["phone"])
    assert user.is_passenger
    assert Passenger.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_register_driver_creates_driver_profile(api):
    # The passenger keys ride along unused — the service ignores them for a driver.
    response = _register(api, role="DRIVER", license_number="N01-11-111111")
    assert response.status_code == 201, response.data
    assert Driver.objects.filter(user__phone=PAX_PAYLOAD["phone"]).exists()


@pytest.mark.django_db
def test_register_rejects_a_duplicate_phone(api):
    assert _register(api).status_code == 201
    response = _register(api, full_name="Impostor")
    assert response.status_code == 400
    assert "phone" in response.data


@pytest.mark.django_db
def test_register_rejects_a_weak_password(api):
    response = _register(api, password="12345678")
    assert response.status_code == 400
    assert "password" in response.data


@pytest.mark.django_db
def test_register_rejects_a_malformed_phone(api):
    response = _register(api, phone="12345")
    assert response.status_code == 400


@pytest.mark.django_db
def test_register_admin_role_is_refused(api):
    response = _register(api, role="ADMIN")
    assert response.status_code == 400


# ── Login, refresh, me ─────────────────────────────────────────


@pytest.mark.django_db
def test_login_by_phone_returns_tokens_and_claims(api):
    _register(api)
    response = api.post(
        "/api/auth/login/",
        {"phone": PAX_PAYLOAD["phone"], "password": PAX_PAYLOAD["password"]},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["user"]["user_role"] == "PASSENGER"


@pytest.mark.django_db
def test_access_token_opens_me(api):
    access = _register(api).data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = api.get("/api/auth/me/")
    assert response.status_code == 200
    assert response.data["profile"]["home_address"] == "12 Rizal St"


@pytest.mark.django_db
def test_me_requires_authentication(api):
    assert api.get("/api/auth/me/").status_code == 401


@pytest.mark.django_db
def test_refresh_rotates_the_pair(api):
    refresh = _register(api).data["refresh"]
    response = api.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
    assert response.status_code == 200
    assert "access" in response.data


@pytest.mark.django_db
def test_suspended_user_cannot_login(api):
    _register(api)
    User.objects.filter(phone=PAX_PAYLOAD["phone"]).update(account_status="SUSPENDED")
    response = api.post(
        "/api/auth/login/",
        {"phone": PAX_PAYLOAD["phone"], "password": PAX_PAYLOAD["password"]},
        format="json",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_wrong_password_is_a_401_not_a_500(api):
    _register(api)
    response = api.post(
        "/api/auth/login/",
        {"phone": PAX_PAYLOAD["phone"], "password": "wrong-password"},
        format="json",
    )
    assert response.status_code == 401


# ── OTP ────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_otp_request_stores_a_code_in_redis(api):
    response = api.post("/api/auth/otp/request/", {"phone": "09172220000"}, format="json")
    assert response.status_code == 200
    assert response.data["expires_in"] > 0
    assert cache.get("otp:09172220000")  # six digits, sitting in Redis


@pytest.mark.django_db
def test_otp_request_enforces_the_cooldown(api):
    first = api.post("/api/auth/otp/request/", {"phone": "09172220000"}, format="json")
    assert first.status_code == 200
    response = api.post("/api/auth/otp/request/", {"phone": "09172220000"}, format="json")
    assert response.status_code == 429


@pytest.mark.django_db
def test_otp_verify_accepts_and_consumes_the_code(api):
    api.post("/api/auth/otp/request/", {"phone": "09172220000"}, format="json")
    code = cache.get("otp:09172220000")
    first = api.post("/api/auth/otp/verify/", {"phone": "09172220000", "code": code}, format="json")
    assert first.status_code == 200
    # One attempt per code: verification consumed it.
    second = api.post("/api/auth/otp/verify/", {"phone": "09172220000", "code": code}, format="json")
    assert second.status_code == 400


@pytest.mark.django_db
def test_otp_verify_rejects_a_wrong_code(api):
    api.post("/api/auth/otp/request/", {"phone": "09172220000"}, format="json")
    response = api.post(
        "/api/auth/otp/verify/", {"phone": "09172220000", "code": "000000"}, format="json"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_otp_verify_rejects_an_expired_code(api):
    api.post("/api/auth/otp/request/", {"phone": "09172220000"}, format="json")
    cache.delete("otp:09172220000")  # simulate the TTL elapsing
    response = api.post(
        "/api/auth/otp/verify/", {"phone": "09172220000", "code": "123456"}, format="json"
    )
    assert response.status_code == 400

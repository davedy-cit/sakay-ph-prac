"""Accounts-domain tests.

Each test restates a claim from schema_listing.md or consistency_report.md.
"""

import pytest
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import Accreditation, Driver, Passenger, User, Vehicle
from apps.core.enums import AccountStatus, AccredStatus, UserRole


# ── The auth integration ───────────────────────────────────────

def test_phone_is_the_login_identifier(passenger_user):
    """USER has no username column; phone is the USERNAME_FIELD."""
    assert User.USERNAME_FIELD == "phone"
    assert User._meta.label == "accounts.User"
    assert User._meta.db_table == "USER"


def test_password_is_stored_hashed(passenger_user):
    """A plaintext password in the database is the worst bug in the project."""
    assert passenger_user.password.startswith("pbkdf2_sha256$")
    assert "sakay-test-1234" not in passenger_user.password
    assert passenger_user.check_password("sakay-test-1234")


def test_authenticate_by_phone(passenger_user):
    assert authenticate(phone="09171234567", password="sakay-test-1234") == passenger_user


@pytest.mark.parametrize(
    "status,expected",
    [
        (AccountStatus.ACTIVE, True),
        (AccountStatus.SUSPENDED, False),
        (AccountStatus.DEACTIVATED, False),
    ],
)
def test_is_active_is_derived_from_account_status(passenger_user, status, expected):
    """is_active is a property, not a column — the two cannot disagree."""
    passenger_user.account_status = status
    assert passenger_user.is_active is expected


def test_suspended_user_cannot_authenticate(passenger_user):
    passenger_user.account_status = AccountStatus.SUSPENDED
    passenger_user.save(update_fields=["account_status"])
    assert authenticate(phone="09171234567", password="sakay-test-1234") is None


def test_phone_must_be_unique(db):
    User.objects.create_user(phone="09170000001", password="x", full_name="A")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            User.objects.create_user(phone="09170000001", password="y", full_name="B")


def test_phone_format_is_validated(db):
    """The schema's VARCHAR(15) is not a format check; the validator is."""
    u = User(phone="not-a-number", full_name="X", user_role=UserRole.PASSENGER)
    with pytest.raises(ValidationError):
        u.full_clean()


# ── Class-table inheritance ────────────────────────────────────

def test_subtype_pk_is_the_supertype_pk(passenger, passenger_user):
    """PASSENGER.passenger_id is a FK to USER and the primary key."""
    assert passenger.pk == passenger_user.pk
    assert Passenger._meta.pk.column == "passenger_id"
    assert passenger.user == passenger_user


def test_passenger_profile_requires_passenger_role(driver_user):
    """clean() enforces the discriminator — a DRIVER cannot hold a profile."""
    bad = Passenger(user=driver_user, home_address="X", gcash_number="09179876543")
    with pytest.raises(ValidationError):
        bad.full_clean()


def test_driver_profile_requires_driver_role(passenger_user):
    bad = Driver(user=passenger_user, license_number="N99-99-999999")
    with pytest.raises(ValidationError):
        bad.full_clean()


def test_license_number_is_unique(driver, driver_user):
    other = User.objects.create_user(
        phone="09170000002", password="x", full_name="C", user_role=UserRole.DRIVER
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Driver.objects.create(user=other, license_number=driver.license_number)


# ── Availability and accreditation ─────────────────────────────

def test_driver_availability_needs_online_and_verified(driver):
    assert driver.is_available
    driver.accreditation_status = AccredStatus.PENDING
    assert not driver.is_available
    driver.accreditation_status = AccredStatus.VERIFIED
    driver.is_online = False
    assert not driver.is_available


def test_suspended_driver_is_not_available(driver, driver_user):
    driver_user.account_status = AccountStatus.SUSPENDED
    driver_user.save(update_fields=["account_status"])
    driver.refresh_from_db()
    assert not driver.is_available


def test_one_vehicle_per_driver(driver, tricycle):
    Vehicle.objects.create(driver=driver, mode=tricycle, plate_number="ABC 1234",
                           model="Honda TMX", capacity=3)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Vehicle.objects.create(driver=driver, mode=tricycle,
                                   plate_number="XYZ 9876", model="Kawasaki")


def test_driver_holds_no_accreditation_until_issued(driver):
    """DRIVER -> ACCREDITATION is 1 : 0..*; a new driver holds none."""
    assert driver.accreditations.count() == 0


def test_accreditation_is_unique_per_driver_and_lgu(driver, lgu):
    Accreditation.objects.create(
        driver=driver, lgu=lgu, badge_no="BDG-0001",
        status=AccredStatus.VERIFIED, expiry_date="2027-12-31",
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Accreditation.objects.create(
                driver=driver, lgu=lgu, badge_no="BDG-0002",
                status=AccredStatus.VERIFIED, expiry_date="2028-12-31",
            )


def test_passenger_rating_avg_is_derived_not_stored():
    """schema_listing.md marks it DERIVED — so it must not be a column."""
    column_names = {f.column for f in Passenger._meta.get_fields() if hasattr(f, "column")}
    assert "rating_avg" not in column_names
    assert isinstance(Passenger.rating_avg, property)

"""Safety-domain tests — the SOS fan-out and its associative entity."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.enums import DeliveryStatus, SOSStatus
from apps.safety.models import SOSAlert, SOSNotification, TrustedContact


@pytest.fixture
def contacts(passenger):
    return [
        TrustedContact.objects.create(passenger=passenger, contact_name="Mama",
                                      contact_mobile="09171111111",
                                      relationship="Mother"),
        TrustedContact.objects.create(passenger=passenger, contact_name="Ate Joy",
                                      contact_mobile="09172222222",
                                      relationship="Sister"),
        TrustedContact.objects.create(passenger=passenger,
                                      contact_name="Barangay Hall",
                                      contact_mobile="09173333333",
                                      relationship="Barangay"),
    ]


@pytest.fixture
def alert(ride, passenger_user):
    return SOSAlert.objects.create(
        ride=ride, raised_by=passenger_user, alert_type="harassment",
        alert_lat=Decimal("14.261000"), alert_long=Decimal("121.115000"),
    )


def test_trusted_contact_mobile_is_unique_per_passenger(passenger, contacts):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            TrustedContact.objects.create(passenger=passenger, contact_name="Dup",
                                          contact_mobile="09171111111")


def test_alert_snapshots_the_position(alert):
    """The position at trigger time is evidence; it must not track later."""
    assert alert.coordinates == (14.261, 121.115)


def test_one_sos_per_ride(alert, ride, passenger_user):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SOSAlert.objects.create(ride=ride, raised_by=passenger_user,
                                    alert_type="second",
                                    alert_lat=Decimal("14.26"),
                                    alert_long=Decimal("121.11"))


def test_fan_out_creates_one_notification_per_contact(alert, contacts):
    for c in contacts:
        SOSNotification.objects.create(alert=alert, contact=c)
    assert alert.notifications.count() == 3
    assert alert.notified_count == 0  # all still SENT


def test_notification_is_unique_per_alert_and_contact(alert, contacts):
    SOSNotification.objects.create(alert=alert, contact=contacts[0])
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SOSNotification.objects.create(alert=alert, contact=contacts[0])


def test_notified_count_counts_only_delivered(alert, contacts):
    for c in contacts:
        SOSNotification.objects.create(alert=alert, contact=c)
    alert.notifications.filter(contact__in=contacts[:2]).update(
        delivery_status=DeliveryStatus.FAILED
    )
    alert.notifications.get(contact=contacts[2]).mark_delivered()
    assert alert.notified_count == 1
    assert alert.notifications.filter(delivery_status=DeliveryStatus.FAILED).count() == 2


def test_alert_is_open_until_resolved(alert):
    assert alert.is_open
    alert.status = SOSStatus.RESOLVED
    alert.resolved_at = timezone.now()
    alert.save(update_fields=["status", "resolved_at"])
    assert not alert.is_open
    assert alert.response_seconds is not None


def test_open_alert_has_no_response_time(alert):
    assert alert.response_seconds is None


def test_resolved_at_cannot_precede_triggered_at(alert):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SOSAlert.objects.filter(pk=alert.pk).update(
                triggered_at=timezone.now(),
                resolved_at=timezone.now() - timedelta(hours=1),
            )


def test_deleting_a_contact_removes_its_notification(alert, contacts):
    """CASCADE here is deliberate — see the model docstring."""
    SOSNotification.objects.create(alert=alert, contact=contacts[0])
    contacts[0].delete()
    assert alert.notifications.count() == 0


def test_alert_survives_a_ride_delete_attempt(alert, ride):
    """SOSAlert.ride is PROTECT — an alert is evidence."""
    with pytest.raises(Exception):
        with transaction.atomic():
            ride.delete()

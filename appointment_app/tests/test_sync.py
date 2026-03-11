"""
Unit tests for DataSyncHandler.

Strategy:
- BookingSystemClient is fully mocked via MagicMock — zero network calls.
- All tests use test database via pytest-django.
- Each test class covers one sync method independently.
- Fixtures are composable: booking_system → handler → synced_dependencies.

Test coverage:
    TestSyncProviders       — create, update, dedup, bad record, empty list
    TestSyncCustomers       — create, update, null coercion, empty list
    TestSyncServices        — create, update, price coercion, null price, zero duration
    TestSyncAppointments    — create, update, missing FK refs, dedup, field mapping
    TestSyncAll             — ordering, summary keys, counts
    TestEdgeCases           — empty responses, all-bad batches, mixed valid/invalid
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

from appointment_app.models import (
    BookingSystem, Provider, Customer, Service, Appointment
)
from appointment_app.sync import DataSyncHandler



# Raw API payload factories


def make_raw_provider(id=1, first_name="Sarah", last_name="Johnson",
                      email="sarah@test.com", phone="+1-555-0101"):
    return {
        "id": id,
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "phone": phone,
        "timezone": "America/New_York",
        "services": [1, 2],
    }


def make_raw_customer(id=10, first_name="Alice", last_name="Brown",
                      email="alice@test.com", phone=None):
    return {
        "id": id,
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "phone": phone,
        "address": None,
        "notes": None,
    }


def make_raw_service(id=3, name="Men's Haircut", duration=30,
                     price="35.00", currency="USD"):
    return {
        "id": id,
        "name": name,
        "duration": duration,
        "price": price,
        "currency": currency,
    }


def make_raw_appointment(id=42, provider_id=1, customer_id=10, service_id=3,
                         start="2026-01-10 09:00:00", end="2026-01-10 09:30:00",
                         status="Booked", location="Test Salon - Main Branch"):
    return {
        "id": id,
        "start": start,
        "end": end,
        "location": location,
        "notes": None,
        "status": status,
        "providerId": provider_id,
        "customerId": customer_id,
        "serviceId": service_id,
    }



# Shared fixtures


@pytest.fixture
def booking_system(db):
    """A real BookingSystem row in the test DB."""
    return BookingSystem.objects.create(
        name="Test Salon",
        base_url="http://localhost:8888",
        credentials={"username": "admin", "password": "admin123"},
    )


@pytest.fixture
def handler(booking_system):
    """DataSyncHandler with a fully mocked client — no network calls."""
    h = DataSyncHandler(booking_system)
    h.client = MagicMock()
    return h


@pytest.fixture
def synced_dependencies(handler):
    """
    Pre-sync provider, customer, service so appointment tests
    have valid FK references to work with.
    """
    handler.client.get_providers.return_value = [make_raw_provider(id=1)]
    handler.client.get_customers.return_value = [make_raw_customer(id=10)]
    handler.client.get_services.return_value = [make_raw_service(id=3)]
    handler.sync_providers()
    handler.sync_customers()
    handler.sync_services()



# TestSyncProviders


class TestSyncProviders:

    def test_creates_new_provider(self, handler, booking_system):
        """A new external provider is inserted into the DB."""
        handler.client.get_providers.return_value = [make_raw_provider(id=1)]
        count = handler.sync_providers()
        assert count == 1
        assert Provider.objects.filter(
            booking_system=booking_system, external_id="1"
        ).exists()

    def test_returns_correct_count(self, handler, booking_system):
        """Return value equals the number of records upserted."""
        handler.client.get_providers.return_value = [
            make_raw_provider(id=1),
            make_raw_provider(id=2, first_name="Mike", email="mike@test.com"),
        ]
        count = handler.sync_providers()
        assert count == 2

    def test_updates_existing_provider(self, handler, booking_system):
        """An existing provider record is updated, not duplicated."""
        Provider.objects.create(
            booking_system=booking_system,
            external_id="1",
            first_name="Old",
            last_name="Name",
            email="old@test.com",
        )
        handler.client.get_providers.return_value = [
            make_raw_provider(id=1, first_name="Sarah", last_name="Johnson")
        ]
        handler.sync_providers()
        provider = Provider.objects.get(booking_system=booking_system, external_id="1")
        assert provider.first_name == "Sarah"
        assert provider.last_name == "Johnson"

    def test_no_duplicates_on_repeated_sync(self, handler, booking_system):
        """Running sync twice does not create duplicate rows."""
        handler.client.get_providers.return_value = [make_raw_provider(id=1)]
        handler.sync_providers()
        handler.sync_providers()
        assert Provider.objects.filter(booking_system=booking_system).count() == 1

    def test_skips_record_missing_id_continues_rest(self, handler, booking_system):
        """A record without 'id' is skipped; subsequent valid records still process."""
        handler.client.get_providers.return_value = [
            {"firstName": "No ID"},           
            make_raw_provider(id=2),           
        ]
        count = handler.sync_providers()
        assert count == 1
        assert Provider.objects.filter(booking_system=booking_system).count() == 1

    def test_empty_list_returns_zero(self, handler):
        """Empty API response returns 0 and creates nothing."""
        handler.client.get_providers.return_value = []
        count = handler.sync_providers()
        assert count == 0

    def test_stores_extra_data(self, handler, booking_system):
        """The full raw payload is saved into extra_data for audit purposes."""
        raw = make_raw_provider(id=1)
        handler.client.get_providers.return_value = [raw]
        handler.sync_providers()
        provider = Provider.objects.get(booking_system=booking_system, external_id="1")
        assert provider.extra_data["timezone"] == "America/New_York"

    def test_coerces_null_phone_to_empty_string(self, handler, booking_system):
        """None phone from API is stored as '' not NULL (CharField is NOT NULL)."""
        handler.client.get_providers.return_value = [
            make_raw_provider(id=1, phone=None)
        ]
        handler.sync_providers()
        provider = Provider.objects.get(booking_system=booking_system, external_id="1")
        assert provider.phone == ""

    def test_external_id_is_stored_as_string(self, handler, booking_system):
        """external_id is always a string even when API returns integer id."""
        handler.client.get_providers.return_value = [make_raw_provider(id=99)]
        handler.sync_providers()
        assert Provider.objects.filter(
            booking_system=booking_system, external_id="99"
        ).exists()



# TestSyncCustomers


class TestSyncCustomers:

    def test_creates_customer(self, handler, booking_system):
        """A new customer is created from a valid API payload."""
        handler.client.get_customers.return_value = [make_raw_customer(id=5)]
        count = handler.sync_customers()
        assert count == 1
        assert Customer.objects.filter(
            booking_system=booking_system, external_id="5"
        ).exists()

    def test_updates_existing_customer(self, handler, booking_system):
        """An existing customer is updated on re-sync."""
        Customer.objects.create(
            booking_system=booking_system,
            external_id="5",
            first_name="Old",
            last_name="Name",
            email="old@test.com",
        )
        handler.client.get_customers.return_value = [
            make_raw_customer(id=5, first_name="Alice", email="alice@test.com")
        ]
        handler.sync_customers()
        customer = Customer.objects.get(booking_system=booking_system, external_id="5")
        assert customer.first_name == "Alice"
        assert customer.email == "alice@test.com"

    def test_coerces_null_phone_to_empty_string(self, handler, booking_system):
        """None phone is coerced to '' — NOT NULL constraint is never violated."""
        handler.client.get_customers.return_value = [
            make_raw_customer(id=10, phone=None)
        ]
        handler.sync_customers()
        customer = Customer.objects.get(booking_system=booking_system, external_id="10")
        assert customer.phone == ""

    def test_no_duplicates_on_repeated_sync(self, handler, booking_system):
        """Repeated sync does not create duplicate customer rows."""
        handler.client.get_customers.return_value = [make_raw_customer(id=10)]
        handler.sync_customers()
        handler.sync_customers()
        assert Customer.objects.filter(booking_system=booking_system).count() == 1

    def test_empty_list_returns_zero(self, handler):
        """Empty API response returns 0."""
        handler.client.get_customers.return_value = []
        assert handler.sync_customers() == 0

    def test_skips_bad_record_continues_rest(self, handler, booking_system):
        """A record missing 'id' is skipped; valid records still process."""
        handler.client.get_customers.return_value = [
            {"firstName": "Bad"},
            make_raw_customer(id=20),
        ]
        count = handler.sync_customers()
        assert count == 1


# TestSyncServices


class TestSyncServices:

    def test_creates_service(self, handler, booking_system):
        """A new service is created from a valid API payload."""
        handler.client.get_services.return_value = [make_raw_service(id=3)]
        count = handler.sync_services()
        assert count == 1
        assert Service.objects.filter(
            booking_system=booking_system, external_id="3"
        ).exists()

    def test_converts_string_price_to_decimal(self, handler, booking_system):
        """API returns price as string — must be stored as Decimal."""
        handler.client.get_services.return_value = [make_raw_service(id=3, price="35.00")]
        handler.sync_services()
        service = Service.objects.get(booking_system=booking_system, external_id="3")
        assert service.price == Decimal("35.00")

    def test_converts_integer_price_to_decimal(self, handler, booking_system):
        """Integer price from API is safely converted to Decimal."""
        handler.client.get_services.return_value = [make_raw_service(id=3, price=50)]
        handler.sync_services()
        service = Service.objects.get(booking_system=booking_system, external_id="3")
        assert service.price == Decimal("50")

    def test_null_price_defaults_to_zero(self, handler, booking_system):
        """None price is coerced to Decimal('0.00') — no crash."""
        raw = make_raw_service(id=4)
        raw["price"] = None
        handler.client.get_services.return_value = [raw]
        handler.sync_services()
        service = Service.objects.get(booking_system=booking_system, external_id="4")
        assert service.price == Decimal("0.00")

    def test_null_duration_defaults_to_zero(self, handler, booking_system):
        """None duration is stored as 0 — PositiveIntegerField never crashes."""
        raw = make_raw_service(id=5)
        raw["duration"] = None
        handler.client.get_services.return_value = [raw]
        handler.sync_services()
        service = Service.objects.get(booking_system=booking_system, external_id="5")
        assert service.duration_minutes == 0

    def test_updates_existing_service(self, handler, booking_system):
        """An existing service price is updated on re-sync."""
        Service.objects.create(
            booking_system=booking_system,
            external_id="3",
            name="Old Service",
            duration_minutes=30,
            price=Decimal("10.00"),
        )
        handler.client.get_services.return_value = [
            make_raw_service(id=3, name="Women's Haircut", price="75.00")
        ]
        handler.sync_services()
        service = Service.objects.get(booking_system=booking_system, external_id="3")
        assert service.name == "Women's Haircut"
        assert service.price == Decimal("75.00")

    def test_no_duplicates_on_repeated_sync(self, handler, booking_system):
        """Repeated sync does not create duplicate service rows."""
        handler.client.get_services.return_value = [make_raw_service(id=3)]
        handler.sync_services()
        handler.sync_services()
        assert Service.objects.filter(booking_system=booking_system).count() == 1

    def test_empty_list_returns_zero(self, handler):
        """Empty API response returns 0."""
        handler.client.get_services.return_value = []
        assert handler.sync_services() == 0

    def test_null_currency_defaults_to_usd(self, handler, booking_system):
        """None currency falls back to 'USD' default."""
        raw = make_raw_service(id=6)
        raw["currency"] = None
        handler.client.get_services.return_value = [raw]
        handler.sync_services()
        service = Service.objects.get(booking_system=booking_system, external_id="6")
        assert service.currency == "USD"



# TestSyncAppointments


class TestSyncAppointments:

    def test_creates_appointment_with_valid_references(
        self, handler, booking_system, synced_dependencies
    ):
        """A valid appointment is created when all FK refs exist locally."""
        handler.client.get_appointments.return_value = [make_raw_appointment()]
        count = handler.sync_appointments()
        assert count == 1
        assert Appointment.objects.filter(
            booking_system=booking_system, external_id="42"
        ).exists()

    def test_links_correct_provider_customer_service(
        self, handler, booking_system, synced_dependencies
    ):
        """Appointment FK fields are resolved to correct local DB rows."""
        handler.client.get_appointments.return_value = [make_raw_appointment()]
        handler.sync_appointments()
        appt = Appointment.objects.select_related(
            "provider", "customer", "service"
        ).get(booking_system=booking_system, external_id="42")
        assert appt.provider.external_id == "1"
        assert appt.customer.external_id == "10"
        assert appt.service.external_id == "3"

    def test_skips_appointment_with_missing_provider(
        self, handler, booking_system, synced_dependencies
    ):
        """Appointment is skipped when provider external_id not found locally."""
        handler.client.get_appointments.return_value = [
            make_raw_appointment(provider_id=999)  
        ]
        count = handler.sync_appointments()
        assert count == 0
        assert Appointment.objects.filter(booking_system=booking_system).count() == 0

    def test_skips_appointment_with_missing_customer(
        self, handler, booking_system, synced_dependencies
    ):
        """Appointment is skipped when customer external_id not found locally."""
        handler.client.get_appointments.return_value = [
            make_raw_appointment(customer_id=999)
        ]
        count = handler.sync_appointments()
        assert count == 0

    def test_skips_appointment_with_missing_service(
        self, handler, booking_system, synced_dependencies
    ):
        """Appointment is skipped when service external_id not found locally."""
        handler.client.get_appointments.return_value = [
            make_raw_appointment(service_id=999)
        ]
        count = handler.sync_appointments()
        assert count == 0

    def test_no_duplicates_on_repeated_sync(
        self, handler, booking_system, synced_dependencies
    ):
        """Running appointment sync twice produces exactly one row."""
        handler.client.get_appointments.return_value = [make_raw_appointment()]
        handler.sync_appointments()
        handler.sync_appointments()
        assert Appointment.objects.filter(booking_system=booking_system).count() == 1

    def test_updates_existing_appointment_status(
        self, handler, booking_system, synced_dependencies
    ):
        """An existing appointment status is updated on re-sync."""
        handler.client.get_appointments.return_value = [
            make_raw_appointment(status="Booked")
        ]
        handler.sync_appointments()

        handler.client.get_appointments.return_value = [
            make_raw_appointment(status="Completed")
        ]
        handler.sync_appointments()

        appt = Appointment.objects.get(booking_system=booking_system, external_id="42")
        assert appt.status == "Completed"

    def test_stores_start_and_end_time(
        self, handler, booking_system, synced_dependencies
    ):
        """start_time and end_time are persisted correctly from raw payload."""
        handler.client.get_appointments.return_value = [
            make_raw_appointment(
                start="2026-01-10 09:00:00",
                end="2026-01-10 09:30:00",
            )
        ]
        handler.sync_appointments()
        appt = Appointment.objects.get(booking_system=booking_system, external_id="42")
        assert str(appt.start_time).startswith("2026-01-10")
        assert str(appt.end_time).startswith("2026-01-10")

    def test_stores_location(self, handler, booking_system, synced_dependencies):
        """Location field is stored from raw payload."""
        handler.client.get_appointments.return_value = [
            make_raw_appointment(location="Branch B")
        ]
        handler.sync_appointments()
        appt = Appointment.objects.get(booking_system=booking_system, external_id="42")
        assert appt.location == "Branch B"

    def test_empty_list_returns_zero(self, handler, synced_dependencies):
        """Empty API response returns 0."""
        handler.client.get_appointments.return_value = []
        assert handler.sync_appointments() == 0

    def test_mixed_valid_and_missing_refs(
        self, handler, booking_system, synced_dependencies
    ):
        """Only appointments with all valid refs are created; bad ones are skipped."""
        handler.client.get_appointments.return_value = [
            make_raw_appointment(id=42),          
            make_raw_appointment(id=43, provider_id=999),  
            make_raw_appointment(id=44, customer_id=999),  
        ]
        count = handler.sync_appointments()
        assert count == 1
        assert Appointment.objects.filter(booking_system=booking_system).count() == 1



# TestSyncAll


class TestSyncAll:

    def test_returns_summary_with_all_keys(self, handler, synced_dependencies):
        """sync_all() returns a dict with keys for all four resource types."""
        handler.client.get_providers.return_value = [make_raw_provider(id=1)]
        handler.client.get_customers.return_value = [make_raw_customer(id=10)]
        handler.client.get_services.return_value = [make_raw_service(id=3)]
        handler.client.get_appointments.return_value = [make_raw_appointment()]
        summary = handler.sync_all()
        assert set(summary.keys()) == {"providers", "customers", "services", "appointments"}

    def test_summary_counts_match_records(self, handler, synced_dependencies):
        """Counts in summary dict match actual records returned by the API."""
        handler.client.get_providers.return_value = [
            make_raw_provider(id=1),
            make_raw_provider(id=2, email="mike@test.com"),
        ]
        handler.client.get_customers.return_value = [make_raw_customer(id=10)]
        handler.client.get_services.return_value = [make_raw_service(id=3)]
        handler.client.get_appointments.return_value = [make_raw_appointment()]
        summary = handler.sync_all()
        assert summary["providers"] == 2
        assert summary["customers"] == 1
        assert summary["services"] == 1
        assert summary["appointments"] == 1

    def test_calls_client_methods_in_order(self, handler):
        """Client methods are called in dependency order: providers first, appointments last."""
        handler.client.get_providers.return_value = []
        handler.client.get_customers.return_value = []
        handler.client.get_services.return_value = []
        handler.client.get_appointments.return_value = []

        handler.sync_all()

        call_order = [c[0] for c in handler.client.method_calls]
        assert call_order.index("get_providers") < call_order.index("get_appointments")
        assert call_order.index("get_customers") < call_order.index("get_appointments")
        assert call_order.index("get_services") < call_order.index("get_appointments")



# TestEdgeCases


class TestEdgeCases:

    def test_all_bad_providers_returns_zero(self, handler):
        """If every record in a batch is invalid, returns 0 and nothing is saved."""
        handler.client.get_providers.return_value = [
            {"firstName": "No ID"},
            {"lastName": "Also No ID"},
        ]
        count = handler.sync_providers()
        assert count == 0
        assert Provider.objects.count() == 0

    def test_multiple_booking_systems_do_not_cross_contaminate(self, db):
        """Records for one booking system are never visible to another."""
        bs1 = BookingSystem.objects.create(
            name="Salon A", base_url="http://a.com",
            credentials={"username": "a", "password": "a"},
        )
        bs2 = BookingSystem.objects.create(
            name="Salon B", base_url="http://b.com",
            credentials={"username": "b", "password": "b"},
        )
        h1 = DataSyncHandler(bs1)
        h1.client = MagicMock()
        h1.client.get_providers.return_value = [make_raw_provider(id=1)]
        h1.sync_providers()

        # bs2 should see no providers
        assert Provider.objects.filter(booking_system=bs2).count() == 0
        assert Provider.objects.filter(booking_system=bs1).count() == 1

    def test_sync_providers_calls_client_once(self, handler):
        """The client is called exactly once per sync — no extra API calls."""
        handler.client.get_providers.return_value = []
        handler.sync_providers()
        handler.client.get_providers.assert_called_once()

    def test_sync_appointments_calls_client_once(self, handler, synced_dependencies):
        """The client is called exactly once per sync — no extra API calls."""
        handler.client.get_appointments.return_value = []
        handler.sync_appointments()
        handler.client.get_appointments.assert_called_once()
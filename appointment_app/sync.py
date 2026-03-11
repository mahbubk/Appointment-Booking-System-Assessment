"""
DataSyncHandler — pulls data from the external booking system and upserts
it into the local database.
"""
import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction


from .client import BookingSystemClient
from .models import BookingSystem, Provider, Customer, Service, Appointment

logger = logging.getLogger(__name__)


def _str(value, default="") -> str:
    return value if value is not None else default


def _decimal(value, default=Decimal("0.00")) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


class DataSyncHandler:

    def __init__(self, booking_system: BookingSystem):
        self.booking_system = booking_system
        creds = booking_system.credentials
        self.client = BookingSystemClient(
            base_url=booking_system.base_url,
            username=creds.get("username", ""),
            password=creds.get("password", ""),
        )


    def sync_all(self) -> dict:
        """
        Full sync in dependency order: providers → customers → services → appointments.
        Returns a summary dict with counts per resource.
        """
        logger.info("Starting full sync for BookingSystem #%s (%s)", self.booking_system.pk, self.booking_system.name)
        summary = {}
        summary["providers"] = self.sync_providers()
        summary["customers"] = self.sync_customers()
        summary["services"] = self.sync_services()
        summary["appointments"] = self.sync_appointments()
        logger.info("Sync complete for BookingSystem #%s: %s", self.booking_system.pk, summary)
        return summary

    @transaction.atomic
    def sync_providers(self) -> int:
        """Sync all providers. Returns number of upserted records."""
        records = self.client.get_providers()
        count = 0
        for raw in records:
            count += self._upsert_provider(raw)
        logger.info("Synced %s providers for BookingSystem #%s", count, self.booking_system.pk)
        return count

    @transaction.atomic
    def sync_customers(self) -> int:
        """Sync all customers. Returns number of upserted records."""
        records = self.client.get_customers()
        count = 0
        for raw in records:
            count += self._upsert_customer(raw)
        logger.info("Synced %s customers for BookingSystem #%s", count, self.booking_system.pk)
        return count

    @transaction.atomic
    def sync_services(self) -> int:
        """Sync all services. Returns number of upserted records."""
        records = self.client.get_services()
        count = 0
        for raw in records:
            count += self._upsert_service(raw)
        logger.info("Synced %s services for BookingSystem #%s", count, self.booking_system.pk)
        return count

    @transaction.atomic
    def sync_appointments(self) -> int:
        """Sync all appointments. Returns number of upserted records."""
        records = self.client.get_appointments()
        count = 0
        for raw in records:
            count += self._upsert_appointment(raw)
        logger.info("Synced %s appointments for BookingSystem #%s", count, self.booking_system.pk)
        return count


    def _upsert_provider(self, raw: dict) -> int:
        try:
            with transaction.atomic():
                Provider.objects.update_or_create(
                    booking_system=self.booking_system,
                    external_id=str(raw["id"]),
                    defaults={
                        "first_name": _str(raw.get("firstName")),
                        "last_name": _str(raw.get("lastName")),
                        "email": _str(raw.get("email")),
                        "phone": _str(raw.get("phone")),
                        "extra_data": raw,
                    },
                )
            return 1
        except Exception as exc:
            logger.error("Failed to upsert provider id=%s: %s", raw.get("id"), exc)
            return 0

    def _upsert_customer(self, raw: dict) -> int:
        try:
            with transaction.atomic():
                Customer.objects.update_or_create(
                    booking_system=self.booking_system,
                    external_id=str(raw["id"]),
                    defaults={
                        "first_name": _str(raw.get("firstName")),
                        "last_name": _str(raw.get("lastName")),
                        "email": _str(raw.get("email")),
                        "phone": _str(raw.get("phone")),
                        "extra_data": raw,
                    },
                )
            return 1
        except Exception as exc:
            logger.error("Failed to upsert customer id=%s: %s", raw.get("id"), exc)
            return 0

    def _upsert_service(self, raw: dict) -> int:
        try:
            with transaction.atomic():
                Service.objects.update_or_create(
                    booking_system=self.booking_system,
                    external_id=str(raw["id"]),
                    defaults={
                        "name": _str(raw.get("name")),
                        "duration_minutes": raw.get("duration") or 0,
                        "price": _decimal(raw.get("price")),
                        "currency": _str(raw.get("currency"), "USD"),
                        "extra_data": raw,
                    },
                )
            return 1
        except Exception as exc:
            logger.error("Failed to upsert service id=%s: %s", raw.get("id"), exc)
            return 0

    def _upsert_appointment(self, raw: dict) -> int:
        """
        Upsert a single appointment.
        """
        provider_ext_id = str(raw.get("providerId", ""))
        customer_ext_id = str(raw.get("customerId", ""))
        service_ext_id = str(raw.get("serviceId", ""))

        try:
            provider = Provider.objects.get(
                booking_system=self.booking_system, external_id=provider_ext_id
            )
        except Provider.DoesNotExist:
            logger.warning(
                "Skipping appointment id=%s: provider external_id=%s not found locally.",
                raw.get("id"),
                provider_ext_id,
            )
            return 0

        try:
            customer = Customer.objects.get(
                booking_system=self.booking_system, external_id=customer_ext_id
            )
        except Customer.DoesNotExist:
            logger.warning(
                "Skipping appointment id=%s: customer external_id=%s not found locally.",
                raw.get("id"),
                customer_ext_id,
            )
            return 0

        try:
            service = Service.objects.get(
                booking_system=self.booking_system, external_id=service_ext_id
            )
        except Service.DoesNotExist:
            logger.warning(
                "Skipping appointment id=%s: service external_id=%s not found locally.",
                raw.get("id"),
                service_ext_id,
            )
            return 0

        try:
            with transaction.atomic():
                Appointment.objects.update_or_create(
                    booking_system=self.booking_system,
                    external_id=str(raw["id"]),
                    defaults={
                        "provider": provider,
                        "customer": customer,
                        "service": service,
                        "start_time": raw.get("start"),
                        "end_time": raw.get("end"),
                        "status": _str(raw.get("status"), Appointment.Status.BOOKED),
                        "location": _str(raw.get("location")),
                        "extra_data": raw,
                    },
                )
            return 1
        except Exception as exc:
            logger.error("Failed to upsert appointment id=%s: %s", raw.get("id"), exc)
            return 0
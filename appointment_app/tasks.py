"""
Celery tasks for the bookings app.

Task ordering in sync_booking_system_task:
    providers → customers → services → appointments

This order is required because appointments reference the other three.
If any step fails, sync_status is set to "error" and the chain stops.
"""
import logging

from celery import shared_task
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from .models import BookingSystem
import json

from .sync import DataSyncHandler

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="bookings.sync_booking_system",
)
def sync_booking_system_task(self, booking_system_id: int) -> dict:
    """
    Full sync: providers → customers → services → appointments.
    Updates last_synced_at only if ALL steps succeed.
    On failure, sets sync_status = "error" and stops.
    """
    

    try:
        bs = BookingSystem.objects.get(pk=booking_system_id)
    except BookingSystem.DoesNotExist:
        logger.error("BookingSystem #%s not found — aborting sync.", booking_system_id)
        return {}

    bs.sync_status = BookingSystem.SyncStatus.RUNNING
    bs.last_sync_error = ""
    bs.save(update_fields=["sync_status", "last_sync_error"])

    handler = DataSyncHandler(bs)
    summary = {}

    steps = [
        ("providers", handler.sync_providers),
        ("customers", handler.sync_customers),
        ("services", handler.sync_services),
        ("appointments", handler.sync_appointments),
    ]

    for step_name, step_fn in steps:
        try:
            summary[step_name] = step_fn()
        except Exception as exc:
            error_msg = f"Sync step '{step_name}' failed: {exc}"
            logger.exception(error_msg)
            bs.sync_status = BookingSystem.SyncStatus.ERROR
            bs.last_sync_error = error_msg
            bs.save(update_fields=["sync_status", "last_sync_error"])
            return summary

    # All steps succeeded
    bs.sync_status = BookingSystem.SyncStatus.SUCCESS
    bs.last_synced_at = timezone.now()
    bs.last_sync_error = ""
    bs.save(update_fields=["sync_status", "last_synced_at", "last_sync_error"])
    logger.info("Full sync completed for BookingSystem #%s: %s", booking_system_id, summary)
    return summary


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="bookings.sync_providers",
)
def sync_providers_task(self, booking_system_id: int) -> int:
    """Sync only providers for the given booking system."""
    from .models import BookingSystem
    from .sync import DataSyncHandler

    try:
        bs = BookingSystem.objects.get(pk=booking_system_id)
        return DataSyncHandler(bs).sync_providers()
    except Exception as exc:
        logger.exception("sync_providers_task failed for BookingSystem #%s: %s", booking_system_id, exc)
        try:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for sync_providers_task #%s", booking_system_id)
            return 0


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="bookings.sync_appointments",
)
def sync_appointments_task(self, booking_system_id: int) -> int:
    """Sync only appointments for the given booking system."""
    from .models import BookingSystem
    from .sync import DataSyncHandler

    try:
        bs = BookingSystem.objects.get(pk=booking_system_id)
        return DataSyncHandler(bs).sync_appointments()
    except Exception as exc:
        logger.exception("sync_appointments_task failed for BookingSystem #%s: %s", booking_system_id, exc)
        try:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for sync_appointments_task #%s", booking_system_id)
            return 0



def register_beat_schedules():
    """
    Register periodic tasks in the database-backed Celery Beat scheduler.
    Called from BookingsConfig.ready() so it runs once at startup.

    Syncs all active booking systems every 6 hours.
    """
    try:
        

        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=6,
            period=IntervalSchedule.HOURS,
        )

        for bs in BookingSystem.objects.filter(is_active=True):
            task_name = f"sync_booking_system_{bs.pk}_every_6h"
            PeriodicTask.objects.update_or_create(
                name=task_name,
                defaults={
                    "interval": schedule,
                    "task": "bookings.sync_booking_system",
                    "kwargs": json.dumps({"booking_system_id": bs.pk}),
                    "enabled": True,
                },
            )
    except Exception as exc:
       
        logger.warning("Could not register Beat schedules: %s", exc)
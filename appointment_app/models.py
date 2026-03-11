from django.db import models

class TimestampedModel(models.Model):
    

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class BookingSystem(TimestampedModel):
  

    class SyncStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        ERROR = "error", "Error"

    name = models.CharField(max_length=255)
    base_url = models.URLField(max_length=500)
    credentials = models.JSONField()
    last_synced_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    sync_status = models.CharField(
        max_length=20,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING,
        db_index=True,
    )
    last_sync_error = models.TextField(blank=True, default="")


    def __str__(self):
        return self.name


class Provider(TimestampedModel):

    booking_system = models.ForeignKey(
        BookingSystem, on_delete=models.CASCADE, related_name="providers"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True, default="")
    external_id = models.CharField(max_length=100, db_index=True)
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("booking_system", "external_id")]
        indexes = [
            models.Index(fields=["booking_system", "last_name", "first_name"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Customer(TimestampedModel):


    booking_system = models.ForeignKey(
        BookingSystem, on_delete=models.CASCADE, related_name="customers"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True, default="")
    external_id = models.CharField(max_length=100, db_index=True)
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("booking_system", "external_id")]
        indexes = [
            models.Index(fields=["booking_system", "last_name", "first_name"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Service(TimestampedModel):


    booking_system = models.ForeignKey(
        BookingSystem, on_delete=models.CASCADE, related_name="services"
    )
    name = models.CharField(max_length=255)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="BDT")
    external_id = models.CharField(max_length=100, db_index=True)
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("booking_system", "external_id")]
        indexes = [
            models.Index(fields=["booking_system", "name"]),
        ]

    def __str__(self):
        return self.name


class Appointment(TimestampedModel):
   

    class Status(models.TextChoices):
        BOOKED = "Booked", "Booked"
        CANCELLED = "Cancelled", "Cancelled"
        COMPLETED = "Completed", "Completed"

    booking_system = models.ForeignKey(
        BookingSystem, on_delete=models.CASCADE, related_name="appointments"
    )
    provider = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="appointments"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="appointments"
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE
    )
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.BOOKED, db_index=True
    )
    location = models.CharField(max_length=255, blank=True, default="")
    external_id = models.CharField(max_length=100, db_index=True)
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("booking_system", "external_id")]
        indexes = [
            models.Index(fields=["booking_system", "start_time"]),
            models.Index(fields=["booking_system", "provider", "start_time"]),
            models.Index(fields=["booking_system", "service", "start_time"]),
        ]

    def __str__(self):
        return f"Appt #{self.external_id} — {self.start_time:%Y-%m-%d %H:%M}"

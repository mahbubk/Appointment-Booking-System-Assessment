from django.urls import path
from .views import BookingSystemViewSet

urlpatterns = [
    path(
        "booking-systems/connect/",
        BookingSystemViewSet.as_view({"post": "connect"}),
        name="booking-systems-connect",
    ),
    path(
        "booking-systems/<int:pk>/status/",
        BookingSystemViewSet.as_view({"get": "booking_status"}),
        name="booking-systems-status",
    ),
    path(
        "booking-systems/<int:pk>/providers/",
        BookingSystemViewSet.as_view({"get": "providers"}),
        name="booking-systems-providers",
    ),
    path(
        "booking-systems/<int:pk>/customers/",
        BookingSystemViewSet.as_view({"get": "customers"}),
        name="booking-systems-customers",
    ),
    path(
        "booking-systems/<int:pk>/services/",
        BookingSystemViewSet.as_view({"get": "services"}),
        name="booking-systems-services",
    ),
    path(
        "booking-systems/<int:pk>/appointments/",
        BookingSystemViewSet.as_view({"get": "appointments"}),
        name="booking-systems-appointments",
    ),
    path(
        "booking-systems/<int:pk>/sync/",
        BookingSystemViewSet.as_view({"post": "trigger_sync"}),
        name="booking-systems-sync",
    ),
    path(
        "booking-systems/<int:pk>/sync/status/",
        BookingSystemViewSet.as_view({"get": "sync_status"}),
        name="booking-systems-sync-status",
    ),
]
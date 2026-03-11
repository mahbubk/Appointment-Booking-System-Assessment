"""
Build REST API endpoints using Django REST Framework
"""
import logging

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.response import Response

from utils.responses import filter_queryset, paginate_queryset
from .tasks import sync_booking_system_task


from .models import  BookingSystem

from .serializers import (
    AppointmentSerializer,
    BookingSystemConnectSerializer,
    BookingSystemStatusSerializer,
    CustomerSerializer,
    ProviderSerializer,
    ServiceSerializer,
)

logger = logging.getLogger(__name__)


class BookingSystemViewSet(viewsets.ViewSet):

 

    def connect(self, request):
        serializer = BookingSystemConnectSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        from .client import BookingSystemClient
        client = BookingSystemClient(
            base_url=serializer.validated_data["base_url"],
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if not client.test_connection():
            return Response(
                {"non_field_errors": ["Cannot connect to the booking system. Check base_url and credentials."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance = serializer.save()
        logger.info("BookingSystem connected: id=%s name=%s", instance.pk, instance.name)
        return Response({"id": instance.pk, "name": instance.name}, status=status.HTTP_201_CREATED)


    def booking_status(self, request, pk=None):
        bs = get_object_or_404(BookingSystem, pk=pk)
        data = {
            "id": bs.pk,
            "name": bs.name,
            "sync_status": bs.sync_status,
            "last_synced_at": bs.last_synced_at,
            "last_sync_error": bs.last_sync_error,
            "providers_count": bs.providers.count(),
            "customers_count": bs.customers.count(),
            "services_count": bs.services.count(),
            "appointments_count": bs.appointments.count(),
        }
        serializer = BookingSystemStatusSerializer(data)
        return Response(serializer.data)


    def providers(self, request, pk=None):
        bs = get_object_or_404(BookingSystem, pk=pk)
        queryset = bs.providers.all().order_by("last_name", "first_name")
        queryset = filter_queryset(queryset, request, search_fields=["first_name", "last_name"])
        return Response(paginate_queryset(request, queryset, ProviderSerializer))



    def customers(self, request, pk=None):
        bs = get_object_or_404(BookingSystem, pk=pk)
        queryset = bs.customers.all().order_by("last_name", "first_name")
        queryset = filter_queryset(queryset, request, search_fields=["first_name", "last_name"])
        return Response(paginate_queryset(request, queryset, CustomerSerializer))



    def services(self, request, pk=None):
        bs = get_object_or_404(BookingSystem, pk=pk)
        queryset = bs.services.all().order_by("name")
        queryset = filter_queryset(queryset, request, search_fields=["name"])
        return Response(paginate_queryset(request, queryset, ServiceSerializer))



    def appointments(self, request, pk=None):
        bs = get_object_or_404(BookingSystem, pk=pk)
        queryset = (
            bs.appointments
            .select_related("provider", "customer", "service")
            .order_by("-start_time")
        )
        queryset = filter_queryset(queryset, request, search_fields=None)
        return Response(paginate_queryset(request, queryset, AppointmentSerializer))



    def trigger_sync(self, request, pk=None):
        bs = get_object_or_404(BookingSystem, pk=pk)
  
        task = sync_booking_system_task.delay(bs.pk)
        logger.info("Sync triggered for BookingSystem id=%s task_id=%s", bs.pk, task.id)
        return Response({"task_id": task.id, "booking_system_id": bs.pk}, status=status.HTTP_202_ACCEPTED)



    def sync_status(self, request, pk=None):
        bs = get_object_or_404(BookingSystem, pk=pk)
        return Response({
            "sync_status": bs.sync_status,
            "last_synced_at": bs.last_synced_at,
            "last_sync_error": bs.last_sync_error,
        })
"""
Serializers for the appointment_booking_app.
"""
from rest_framework import serializers

from .models import BookingSystem, Provider, Customer, Service, Appointment




class BookingSystemConnectSerializer(serializers.Serializer):

    name = serializers.CharField(max_length=255)
    base_url = serializers.URLField(max_length=500)
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(max_length=255, write_only=True)

    def validate_base_url(self, value):
        return value.rstrip("/")

    def create(self, validated_data):
        return BookingSystem.objects.create(
            name=validated_data["name"],
            base_url=validated_data["base_url"],
            credentials={
                "username": validated_data["username"],
                "password": validated_data["password"],
            },
        )


class BookingSystemStatusSerializer(serializers.Serializer):

    id = serializers.IntegerField()
    name = serializers.CharField()
    sync_status = serializers.CharField()
    last_synced_at = serializers.DateTimeField(allow_null=True)
    last_sync_error = serializers.CharField()
    providers_count = serializers.IntegerField()
    customers_count = serializers.IntegerField()
    services_count = serializers.IntegerField()
    appointments_count = serializers.IntegerField()



class ProviderSerializer(serializers.ModelSerializer):


    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Provider
        fields = '__all__'

    def get_full_name(self, obj) -> str:
        return f"{obj.first_name} {obj.last_name}"


class CustomerSerializer(serializers.ModelSerializer):


    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = '_all__'

    def get_full_name(self, obj) -> str:
        return f"{obj.first_name} {obj.last_name}"


class ServiceSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Service
        fields = '_all__'

class AppointmentSerializer(serializers.ModelSerializer):

    provider_name = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    service_name = serializers.CharField(source="service.name", read_only=True)
    service_price = serializers.DecimalField(
        source="service.price", max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Appointment
        fields = fields = '_all__'

    def get_provider_name(self, obj) -> str:
        return f"{obj.provider.first_name} {obj.provider.last_name}"

    def get_customer_name(self, obj) -> str:
        return f"{obj.customer.first_name} {obj.customer.last_name}"
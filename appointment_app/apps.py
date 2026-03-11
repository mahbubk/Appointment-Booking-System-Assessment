from django.apps import AppConfig

class AppointmentAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'appointment_app'

    def ready(self):
        from .tasks import register_beat_schedules
        register_beat_schedules()
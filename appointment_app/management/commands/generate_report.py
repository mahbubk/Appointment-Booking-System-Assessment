import json
from django.core.management.base import BaseCommand
from appointment_app.analytics import generate_booking_report

class Command(BaseCommand):
    help = 'Generate booking report for a date range'

    def add_arguments(self, parser):
        parser.add_argument('--booking_system_id', type=int, required=True)
        parser.add_argument('--start_date', type=str, required=True)
        parser.add_argument('--end_date', type=str, required=True)

    def handle(self, *args, **options):
        report = generate_booking_report(
            booking_system_id=options['booking_system_id'],
            start_date=options['start_date'],
            end_date=options['end_date'],
        )
        self.stdout.write(json.dumps(report, indent=2))
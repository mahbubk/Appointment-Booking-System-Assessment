"""
Analytics queries for the generate_report management command.

All queries use ORM aggregation (Sum, Count, Avg, annotate, values)
to minimise round-trips and avoid N+1 patterns.

Total DB queries for generate_report: 4
  1. Summary aggregation
  2. Monthly breakdown
  3. Top providers
  4. Top services
"""
from decimal import Decimal
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from .models import Appointment, BookingSystem


def generate_booking_report(booking_system_id: int, start_date: str, end_date: str) -> dict:



    bs = BookingSystem.objects.get(pk=booking_system_id)

    base_qs = (
        Appointment.objects.filter(
            booking_system_id=booking_system_id,
            start_time__date__gte=start_date,
            start_time__date__lte=end_date,
        )
        .select_related("service", "provider", "customer")
    )


    summary_agg = base_qs.aggregate(
        total_appointments=Count("id"),
        unique_customers=Count("customer_id", distinct=True),
        total_revenue=Sum("service__price"),
    )

    total_appts = summary_agg["total_appointments"] or 0
    total_revenue = summary_agg["total_revenue"] or Decimal("0.00")
    avg_value = (total_revenue / total_appts).quantize(Decimal("0.01")) if total_appts else Decimal("0.00")

    summary = {
        "total_appointments": total_appts,
        "unique_customers": summary_agg["unique_customers"] or 0,
        "total_revenue": float(total_revenue),
        "avg_appointment_value": float(avg_value),
    }

 
    monthly_qs = (
        base_qs.annotate(month=TruncMonth("start_time"))
        .values("month")
        .annotate(
            appointments=Count("id"),
            unique_customers=Count("customer_id", distinct=True),
            revenue=Sum("service__price"),
        )
        .order_by("month")
    )

    monthly_breakdown = [
        {
            "month": row["month"].strftime("%Y-%m"),
            "appointments": row["appointments"],
            "unique_customers": row["unique_customers"],
            "revenue": float(row["revenue"] or 0),
        }
        for row in monthly_qs
    ]

   
    top_providers_qs = (
        base_qs.values("provider__first_name", "provider__last_name")
        .annotate(
            total_appointments=Count("id"),
            total_revenue=Sum("service__price"),
        )
        .order_by("-total_revenue")[:5]
    )

    top_providers = [
        {
            "name": f"{row['provider__first_name']} {row['provider__last_name']}",
            "total_appointments": row["total_appointments"],
            "total_revenue": float(row["total_revenue"] or 0),
        }
        for row in top_providers_qs
    ]

    top_services_qs = (
        base_qs.values("service__name")
        .annotate(
            times_booked=Count("id"),
            total_revenue=Sum("service__price"),
        )
        .order_by("-total_revenue")[:5]
    )

    top_services = [
        {
            "name": row["service__name"],
            "times_booked": row["times_booked"],
            "total_revenue": float(row["total_revenue"] or 0),
        }
        for row in top_services_qs
    ]

    return {
        "booking_system": bs.name,
        "period": f"{start_date} to {end_date}",
        "summary": summary,
        "monthly_breakdown": monthly_breakdown,
        "top_providers": top_providers,
        "top_services": top_services,
    }
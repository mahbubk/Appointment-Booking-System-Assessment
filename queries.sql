--  Raw SQL Analytics Query (PostgreSQL)
--
-- Purpose:
--   Returns per-provider performance stats for a given booking system
--   over a specified date range.
--
-- Columns returned:
--   provider_name         → Full name of the provider (first + last)
--   total_appointments    → Number of appointments handled in the period
--   total_revenue         → Sum of service prices for all appointments
--   unique_customers      → Count of distinct customers served
--   avg_appointment_value → Average revenue per appointment (rounded to 2dp)
--
-- Ordered by: total_revenue DESC (highest earning provider first)
--
-- Tables used:
--   appointment_app_appointment  → core appointments table
--   appointment_app_provider     → provider (staff) records
--   appointment_app_service      → service catalog with pricing
--
-- Variables (psql style):
--   :booking_system_id   → INTEGER  — PK of the BookingSystem to report on
--   :'start_date'        → DATE     — inclusive range start (YYYY-MM-DD)
--   :'end_date'          → DATE     — inclusive range end   (YYYY-MM-DD)
--
-- Usage:
--   Run in psql:
--     \set booking_system_id 1
--     \set start_date '2026-01-01'
--     \set end_date   '2026-03-07'
--     \i queries.sql
--
--   Or from the terminal:
--     psql -U postgres -d appointment_db -f queries.sql
--
-- Example values:
--   booking_system_id = 1
--   start_date        = '2026-01-01'
--   end_date          = '2026-03-07'
--
-- Performance notes:
--   Relies on the following indexes:
--     - appt_bs_start_idx           → filters by booking_system_id + start_time
--     - appt_provider_idx           → speeds up GROUP BY provider_id
--     - appt_service_idx            → speeds up JOIN on service_id
--     - appt_customer_idx           → speeds up COUNT(DISTINCT customer_id)
--     - appt_analytics_covering_idx → allows index-only scan on large datasets
--
-- Total DB round-trips: 1


\set booking_system_id 1
\set start_date '2026-01-01'
\set end_date   '2026-03-07'

SELECT
    -- Full name of the provider
    CONCAT(p.first_name, ' ', p.last_name)                      AS provider_name,

    -- Total number of appointments handled by this provider in the period
    COUNT(a.id)                                                  AS total_appointments,

    -- Total revenue: sum of all service prices for this provider's appointments
    -- COALESCE handles the case where a provider has no appointments (returns 0)
    COALESCE(SUM(svc.price), 0)                                  AS total_revenue,

    -- Number of distinct customers served by this provider
    COUNT(DISTINCT a.customer_id)                                AS unique_customers,

    -- Average revenue per appointment
    -- NULLIF prevents division-by-zero when total_appointments = 0
    -- ROUND to 2 decimal places for currency display
    -- COALESCE returns 0 if there are no appointments
    COALESCE(
        ROUND(SUM(svc.price) / NULLIF(COUNT(a.id), 0), 2),
        0
    )                                                            AS avg_appointment_value

FROM appointment_app_appointment a

-- Join provider to get first_name and last_name
INNER JOIN appointment_app_provider p
    ON p.id = a.provider_id

-- Join service to get price for revenue calculations
INNER JOIN appointment_app_service svc
    ON svc.id = a.service_id

WHERE
    -- Filter to the requested booking system only
    a.booking_system_id = :booking_system_id

    -- Inclusive date range filter on appointment start time
    -- DATE() strips the time component for accurate date comparison
    AND DATE(a.start_time) >= :'start_date'
    AND DATE(a.start_time) <= :'end_date'

-- Group by provider so aggregations are per-provider
-- Include p.id to ensure uniqueness if two providers share the same name
GROUP BY
    p.id,
    p.first_name,
    p.last_name

-- Highest earning provider appears first
ORDER BY
    total_revenue DESC;
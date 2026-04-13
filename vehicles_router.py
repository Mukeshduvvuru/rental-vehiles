"""
routers/dashboard_router.py — Aggregated statistics for dashboards

ENDPOINTS:
  GET /api/dashboard/admin  → admin summary stats
  GET /api/dashboard/fleet  → fleet manager summary

WHY A SEPARATE DASHBOARD ROUTER?
  Dashboard data is read-only, computed by aggregating multiple tables.
  Isolating it here keeps the other routers clean (vehicles_router handles
  CRUD on vehicles, this router handles analytics on top of them).

ADMIN DASHBOARD STATS:
  - Total vehicles | Available | Under maintenance
  - Active rentals (picked_up status)
  - Total revenue (sum of completed bookings)
  - Monthly revenue (current calendar month)
  - Total registered customers
  - Vehicles with maintenance due this week

FLEET MANAGER STATS:
  - Vehicle availability breakdown
  - Maintenance events this month
  - Vehicles with overdue maintenance
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db
from auth import require_role
import models
import schemas

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/admin", response_model=schemas.AdminDashboardStats)
def admin_dashboard(
    db:    Session    = Depends(get_db),
    admin: models.User = Depends(require_role("admin"))
):
    """
    Return aggregated stats for the admin overview panel.

    WHY aggregate at request time?
      For a hackathon dataset size, real-time aggregation is fast enough.
      In production you'd cache this (Redis) or pre-compute with a cron job.
    """

    # --- Vehicle counts ---
    total_vehicles = db.query(models.Vehicle).filter(
        models.Vehicle.status != models.VehicleStatus.INACTIVE
    ).count()

    available_vehicles = db.query(models.Vehicle).filter(
        models.Vehicle.status == models.VehicleStatus.AVAILABLE
    ).count()

    # --- Active rentals (vehicles currently with customers) ---
    active_rentals = db.query(models.Booking).filter(
        models.Booking.rental_status == models.RentalStatus.PICKED_UP
    ).count()

    # --- Revenue: sum of total_cost for RETURNED bookings (payment completed) ---
    total_revenue_result = db.query(func.sum(models.Booking.total_cost)).filter(
        models.Booking.rental_status  == models.RentalStatus.RETURNED,
        models.Booking.payment_status == models.PaymentStatus.COMPLETED
    ).scalar()
    total_revenue = float(total_revenue_result or 0)

    # --- Monthly revenue (current month only) ---
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_result = db.query(func.sum(models.Booking.total_cost)).filter(
        models.Booking.rental_status  == models.RentalStatus.RETURNED,
        models.Booking.payment_status == models.PaymentStatus.COMPLETED,
        models.Booking.created_at     >= month_start
    ).scalar()
    monthly_revenue = float(monthly_result or 0)

    # --- Customer count ---
    total_customers = db.query(models.User).filter(
        models.User.role == models.UserRole.CUSTOMER
    ).count()

    # --- Maintenance due in next 7 days ---
    next_week = datetime.utcnow() + timedelta(days=7)
    pending_maintenance = db.query(models.MaintenanceLog).filter(
        models.MaintenanceLog.next_due_date <= next_week,
        models.MaintenanceLog.next_due_date >= datetime.utcnow()
    ).count()

    return schemas.AdminDashboardStats(
        total_vehicles      = total_vehicles,
        available_vehicles  = available_vehicles,
        active_rentals      = active_rentals,
        total_revenue       = round(total_revenue, 2),
        monthly_revenue     = round(monthly_revenue, 2),
        total_customers     = total_customers,
        pending_maintenance = pending_maintenance,
    )


@router.get("/fleet")
def fleet_dashboard(
    db:   Session    = Depends(get_db),
    user: models.User = Depends(require_role("fleet_manager", "admin"))
):
    """
    Fleet manager's operational summary.

    Shows:
      - Status breakdown of all vehicles
      - Maintenance events logged this month
      - Vehicles overdue for maintenance (next_due_date passed)
      - Currently rented vehicles list
    """

    # Status breakdown
    statuses = db.query(
        models.Vehicle.status,
        func.count(models.Vehicle.id).label("count")
    ).group_by(models.Vehicle.status).all()

    status_breakdown = {str(s.status.value): s.count for s in statuses}

    # Maintenance events this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    maintenance_this_month = db.query(models.MaintenanceLog).filter(
        models.MaintenanceLog.date_performed >= month_start
    ).count()

    # Overdue maintenance (next_due_date in the past)
    overdue = db.query(models.MaintenanceLog).filter(
        models.MaintenanceLog.next_due_date < datetime.utcnow()
    ).count()

    # Currently rented vehicles
    rented = db.query(models.Vehicle).filter(
        models.Vehicle.status == models.VehicleStatus.RENTED
    ).count()

    return {
        "status_breakdown":       status_breakdown,
        "maintenance_this_month": maintenance_this_month,
        "overdue_maintenance":    overdue,
        "currently_rented":       rented,
    }

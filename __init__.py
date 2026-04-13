"""
routers/maintenance_router.py — Vehicle maintenance tracking

ENDPOINTS:
  POST /api/maintenance               → log maintenance event (fleet manager)
  GET  /api/maintenance               → list all logs (fleet manager / admin)
  GET  /api/maintenance/vehicle/{id}  → logs for a specific vehicle
  GET  /api/maintenance/due           → vehicles with upcoming maintenance due

FLEET MANAGER USER STORY:
  Ravi is a fleet manager.  Every Monday he checks the dashboard:
  - 3 vehicles have a next_due_date within the next 7 days
  - He books them for servicing, marks them as under_maintenance
  - After service he logs each event with type, cost, next due date
  - The vehicles go back to AVAILABLE status
"""

from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user, require_role
import models
import schemas

router = APIRouter(prefix="/api/maintenance", tags=["Maintenance"])


@router.post("", response_model=schemas.MaintenanceResponse, status_code=201)
def log_maintenance(
    payload: schemas.MaintenanceCreate,
    db:      Session    = Depends(get_db),
    user:    models.User = Depends(require_role("fleet_manager", "admin"))
):
    """
    Log a maintenance event for a vehicle.

    After logging, the system does NOT automatically change vehicle status —
    the fleet manager must separately call PATCH /vehicles/{id}/status
    because maintenance can be done while vehicle is idle (preventive)
    or after being pulled from rotation.

    Typical maintenance types:
      oil_change | tire_rotation | brake_service | battery_check
      ac_service | engine_checkup | full_service
    """
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == payload.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    log = models.MaintenanceLog(
        vehicle_id       = payload.vehicle_id,
        performed_by     = user.id,
        maintenance_type = payload.maintenance_type,
        description      = payload.description,
        cost             = payload.cost,
        date_performed   = payload.date_performed,
        next_due_date    = payload.next_due_date,
    )

    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("", response_model=List[schemas.MaintenanceResponse])
def list_all_maintenance(
    db:   Session    = Depends(get_db),
    user: models.User = Depends(require_role("fleet_manager", "admin"))
):
    """List all maintenance logs, newest first."""
    return (
        db.query(models.MaintenanceLog)
        .order_by(models.MaintenanceLog.date_performed.desc())
        .all()
    )


@router.get("/due", response_model=List[schemas.MaintenanceResponse])
def get_due_maintenance(
    days_ahead: int = 7,
    db:   Session    = Depends(get_db),
    user: models.User = Depends(require_role("fleet_manager", "admin"))
):
    """
    Return maintenance logs where next_due_date falls within the next N days.

    Default: 7 days — fleet manager checks weekly.
    This drives the "Maintenance Alerts" widget on the Fleet Dashboard.

    If a vehicle has multiple maintenance types due, each one appears.
    """
    cutoff = datetime.utcnow() + timedelta(days=days_ahead)

    due_logs = (
        db.query(models.MaintenanceLog)
        .filter(
            models.MaintenanceLog.next_due_date <= cutoff,
            models.MaintenanceLog.next_due_date >= datetime.utcnow()
        )
        .order_by(models.MaintenanceLog.next_due_date)
        .all()
    )
    return due_logs


@router.get("/vehicle/{vehicle_id}", response_model=List[schemas.MaintenanceResponse])
def get_vehicle_maintenance(
    vehicle_id: int,
    db:   Session    = Depends(get_db),
    user: models.User = Depends(require_role("fleet_manager", "admin"))
):
    """
    Return full maintenance history for a specific vehicle.
    Useful when inspecting a vehicle or preparing it for resale.
    """
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    return (
        db.query(models.MaintenanceLog)
        .filter(models.MaintenanceLog.vehicle_id == vehicle_id)
        .order_by(models.MaintenanceLog.date_performed.desc())
        .all()
    )

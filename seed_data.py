"""
routers/vehicles_router.py — Vehicle inventory management

ENDPOINTS:
  GET    /api/vehicles            → list all vehicles (with filters) — PUBLIC
  GET    /api/vehicles/{id}       → single vehicle details — PUBLIC
  POST   /api/vehicles            → add new vehicle — ADMIN only
  PUT    /api/vehicles/{id}       → full update — ADMIN only
  PATCH  /api/vehicles/{id}/status → update status — ADMIN + FLEET MANAGER
  POST   /api/vehicles/{id}/photo → upload photo — ADMIN + FLEET MANAGER
  DELETE /api/vehicles/{id}       → soft-delete (set inactive) — ADMIN only

FILTERING LOGIC:
  Customers on the browse page can filter by:
    - vehicle_type (car/bike/van/suv/truck)
    - fuel_type    (petrol/diesel/electric/hybrid/cng)
    - seats        (minimum seating capacity)
    - max_price    (maximum daily price)
    - location
  All filter params are optional query strings — missing = no filter applied.
"""

import os
import shutil
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user, require_role
import models
import schemas

router = APIRouter(prefix="/api/vehicles", tags=["Vehicles"])


@router.get("", response_model=List[schemas.VehicleResponse])
def list_vehicles(
    vehicle_type: Optional[str] = Query(None, description="Filter by type: car/bike/van/suv/truck"),
    fuel_type:    Optional[str] = Query(None, description="Filter by fuel: petrol/diesel/electric"),
    min_seats:    Optional[int] = Query(None, ge=1,  description="Minimum seating capacity"),
    max_price:    Optional[float] = Query(None, gt=0, description="Max price per day"),
    location:     Optional[str] = Query(None, description="Filter by hub location"),
    available_only: bool        = Query(True, description="Show only available vehicles"),
    db: Session = Depends(get_db)
):
    """
    Browse vehicles with optional filters.

    No authentication required — anyone can browse the catalogue.
    This is the SEARCH screen customers see first.

    WHY Query() parameters instead of request body?
      For GET requests, filters are passed as URL query strings:
        GET /api/vehicles?vehicle_type=car&min_seats=4&max_price=2000
      This is RESTful (GET requests should be idempotent and bookmarkable).
    """
    query = db.query(models.Vehicle)

    # Apply filters only when the query param was provided
    if available_only:
        query = query.filter(models.Vehicle.status == models.VehicleStatus.AVAILABLE)
    if vehicle_type:
        query = query.filter(models.Vehicle.vehicle_type == vehicle_type)
    if fuel_type:
        query = query.filter(models.Vehicle.fuel_type == fuel_type)
    if min_seats:
        query = query.filter(models.Vehicle.seating_capacity >= min_seats)
    if max_price:
        query = query.filter(models.Vehicle.price_per_day <= max_price)
    if location:
        query = query.filter(models.Vehicle.location.ilike(f"%{location}%"))

    return query.order_by(models.Vehicle.price_per_day).all()


@router.get("/{vehicle_id}", response_model=schemas.VehicleResponse)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    """
    Get full details of a single vehicle by ID.
    Used on the vehicle detail / booking confirmation page.
    """
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@router.post("", response_model=schemas.VehicleResponse, status_code=201)
def add_vehicle(
    payload: schemas.VehicleCreate,
    db:      Session      = Depends(get_db),
    admin:   models.User  = Depends(require_role("admin"))   # role guard
):
    """
    Add a new vehicle to the fleet.
    ADMIN ONLY — fleet managers may not add vehicles, only update status.

    USER STORY — ADMIN ONBOARDS A NEW CAR:
      Admin fills the "Add Vehicle" form:
        brand=Toyota, model=Fortuner, type=suv, seats=7,
        price_per_hour=150, price_per_day=1000, reg=MH12AB1234

      System:
        1. Validates all fields (Pydantic)
        2. Checks registration_number uniqueness
        3. Creates vehicle row with status=AVAILABLE
        4. Returns created vehicle
    """
    # Prevent duplicate registration numbers
    dup = db.query(models.Vehicle).filter(
        models.Vehicle.registration_number == payload.registration_number
    ).first()
    if dup:
        raise HTTPException(
            status_code=400,
            detail=f"Vehicle with registration '{payload.registration_number}' already exists"
        )

    vehicle = models.Vehicle(**payload.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.put("/{vehicle_id}", response_model=schemas.VehicleResponse)
def update_vehicle(
    vehicle_id: int,
    payload:    schemas.VehicleUpdate,
    db:         Session     = Depends(get_db),
    admin:      models.User = Depends(require_role("admin"))
):
    """
    Full or partial update of a vehicle record (admin only).
    Excludes None fields — only updates what was provided.
    """
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    # exclude_unset=True means only fields explicitly sent in request body are applied
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vehicle, field, value)

    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.patch("/{vehicle_id}/status", response_model=schemas.VehicleResponse)
def update_vehicle_status(
    vehicle_id: int,
    new_status: models.VehicleStatus,
    db:         Session     = Depends(get_db),
    user:       models.User = Depends(require_role("admin", "fleet_manager"))
):
    """
    Update only the operational status of a vehicle.

    FLEET MANAGER USE CASE:
      Fleet manager marks a car as "under_maintenance" before sending it
      for servicing.  Status change to AVAILABLE after service is done.
      This prevents customers from booking a vehicle that's unavailable.

    Allowed statuses: available | rented | under_maintenance | inactive
    """
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    vehicle.status = new_status
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.post("/{vehicle_id}/photo", response_model=schemas.VehicleResponse)
async def upload_vehicle_photo(
    vehicle_id: int,
    file:        UploadFile = File(...),
    db:          Session    = Depends(get_db),
    user:        models.User = Depends(require_role("admin", "fleet_manager"))
):
    """
    Upload / replace the photo for a vehicle.

    File is saved as a static asset: /static/vehicles/{vehicle_id}.jpg
    The photo_path column is updated to point to this URL.

    WHY file storage not DB BLOBs?
      Storing binary files in PostgreSQL (as BLOBs) bloats the DB and
      slows queries. Static files served by the web server are much faster.
    """
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    # Validate file type
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WebP images allowed")

    # Save file to static directory
    os.makedirs("static/vehicles", exist_ok=True)
    ext      = file.filename.rsplit(".", 1)[-1]
    filename = f"vehicle_{vehicle_id}.{ext}"
    filepath = f"static/vehicles/{filename}"

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Update the DB record
    vehicle.photo_path = f"/static/vehicles/{filename}"
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}", status_code=204)
def deactivate_vehicle(
    vehicle_id: int,
    db:   Session    = Depends(get_db),
    admin: models.User = Depends(require_role("admin"))
):
    """
    Soft-delete: set status to INACTIVE instead of deleting the row.

    WHY SOFT DELETE?
      Hard-deleting a vehicle would orphan historical booking records
      (foreign key violation or broken history).
      Setting status=INACTIVE hides it from customers while keeping
      the audit trail intact.
    """
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    vehicle.status = models.VehicleStatus.INACTIVE
    db.commit()
    # 204 No Content — success with no response body

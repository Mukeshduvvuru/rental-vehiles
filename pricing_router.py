"""
routers/bookings_router.py — Rental booking lifecycle

ENDPOINTS:
  POST /api/bookings                     → create booking (customer)
  GET  /api/bookings                     → list my bookings (customer) / all (admin)
  GET  /api/bookings/{id}                → single booking detail
  GET  /api/bookings/{id}/price-estimate → price preview before payment
  POST /api/bookings/{id}/pay            → simulate payment
  PATCH /api/bookings/{id}/status        → advance rental state (admin/fleet)
  POST  /api/bookings/{id}/return        → process vehicle return + late fee

BOOKING STATE MACHINE:
  [booked] → [picked_up] → [returned]
      ↘
   [cancelled]

BUSINESS RULES ENFORCED HERE:
  1. Vehicle must be AVAILABLE to accept a booking
  2. No overlapping bookings for the same vehicle
  3. Price is calculated at booking creation using the pricing engine
  4. Payment status must be COMPLETED before rental can move to PICKED_UP
  5. Late fee calculated on RETURNED based on actual vs planned return time
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user, require_role
from utils.pricing import calculate_full_price, calculate_late_fee
import models
import schemas

router = APIRouter(prefix="/api/bookings", tags=["Bookings"])


def _check_vehicle_availability(
    vehicle_id: int,
    start: datetime,
    end:   datetime,
    db:    Session,
    exclude_booking_id: int = None
) -> bool:
    """
    Helper: check if a vehicle has no overlapping approved bookings in [start, end].

    Overlap condition (two intervals A and B overlap when):
        A.start < B.end  AND  A.end > B.start

    We exclude cancelled/returned bookings and optionally the booking being updated.
    """
    query = db.query(models.Booking).filter(
        models.Booking.vehicle_id   == vehicle_id,
        models.Booking.rental_status.in_([
            models.RentalStatus.BOOKED,
            models.RentalStatus.PICKED_UP
        ]),
        models.Booking.start_datetime < end,
        models.Booking.end_datetime   > start,
    )
    if exclude_booking_id:
        query = query.filter(models.Booking.id != exclude_booking_id)

    return query.first() is None   # True = no conflict = available


@router.get("/price-estimate", response_model=schemas.PricingEstimate)
def get_price_estimate(
    vehicle_id:     int,
    start_datetime: datetime,
    end_datetime:   datetime,
    coupon_code:    str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Calculate and return a price breakdown WITHOUT creating a booking.

    USER STORY — SARAH PREVIEWS COST:
      On the booking form, Sarah selects dates.
      JS calls this endpoint; the page instantly shows:
        "Base: ₹4400  |  Weekend: +₹660  |  Coupon: -₹506  |  Total: ₹4554"
      She can try different coupon codes without committing to a booking.
    """
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if end_datetime <= start_datetime:
        raise HTTPException(status_code=400, detail="end_datetime must be after start_datetime")

    return calculate_full_price(vehicle, start_datetime, end_datetime, coupon_code, db)


@router.post("", response_model=schemas.BookingResponse, status_code=201)
def create_booking(
    payload:      schemas.BookingCreate,
    db:           Session     = Depends(get_db),
    current_user: models.User = Depends(require_role("customer"))
):
    """
    Create a new booking.  CUSTOMER ONLY.

    Steps:
      1. Validate vehicle exists and is AVAILABLE
      2. Check no time-overlap with existing bookings
      3. Calculate total price (with rules + coupon)
      4. Create booking record with status=BOOKED, payment=PENDING
      5. (Payment is a separate step → POST /api/bookings/{id}/pay)

    WHY split booking creation and payment?
      Gives the customer a chance to review the price breakdown before
      committing their payment details.  Real-world pattern (Airbnb, etc.)
    """
    # 1. Validate vehicle
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == payload.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if vehicle.status != models.VehicleStatus.AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail=f"Vehicle is currently {vehicle.status.value}, not available for booking"
        )

    # 2. Check time-overlap
    if not _check_vehicle_availability(vehicle.id, payload.start_datetime, payload.end_datetime, db):
        raise HTTPException(
            status_code=409,   # 409 Conflict
            detail="Vehicle is already booked for this time window. Choose different dates."
        )

    # 3. Price calculation
    pricing = calculate_full_price(
        vehicle, payload.start_datetime, payload.end_datetime, payload.coupon_code, db
    )

    # 4. Create booking
    booking = models.Booking(
        customer_id      = current_user.id,
        vehicle_id       = payload.vehicle_id,
        start_datetime   = payload.start_datetime,
        end_datetime     = payload.end_datetime,
        base_cost        = pricing["base_cost"],
        total_cost       = pricing["total_cost"],
        discount_applied = pricing["coupon_discount"],
        payment_mode     = payload.payment_mode,
        coupon_code      = payload.coupon_code,
        notes            = payload.notes,
        rental_status    = models.RentalStatus.BOOKED,
        payment_status   = models.PaymentStatus.PENDING,
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("", response_model=List[schemas.BookingResponse])
def list_bookings(
    db:           Session    = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Customers see only their own bookings.
    Admins see ALL bookings.

    This single endpoint handles both cases using role check.
    Pattern: "same URL, different data visibility per role"
    """
    if current_user.role == models.UserRole.ADMIN:
        return db.query(models.Booking).order_by(models.Booking.created_at.desc()).all()

    # Customer: only their own
    return (
        db.query(models.Booking)
        .filter(models.Booking.customer_id == current_user.id)
        .order_by(models.Booking.created_at.desc())
        .all()
    )


@router.get("/{booking_id}", response_model=schemas.BookingResponse)
def get_booking(
    booking_id:   int,
    db:           Session    = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get single booking details.
    Customers can only view their own; admins can view any.
    """
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Ownership check for customers
    if current_user.role == models.UserRole.CUSTOMER and booking.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return booking


@router.post("/{booking_id}/pay", response_model=schemas.BookingResponse)
def simulate_payment(
    booking_id:   int,
    db:           Session    = Depends(get_db),
    current_user: models.User = Depends(require_role("customer"))
):
    """
    Simulate payment for a booking.

    In a real system this would call Stripe / Razorpay.
    For the hackathon we simulate by simply setting payment_status=COMPLETED.

    WHY simulate?
      Building real payment integration takes hours and requires test API keys.
      For a demo we focus on the UX flow — the placeholder is honest and
      clearly labelled as "simulated".

    After payment, the vehicle is locked for this customer's window.
    """
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your booking")
    if booking.payment_status == models.PaymentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Payment already completed")

    booking.payment_status = models.PaymentStatus.COMPLETED
    db.commit()
    db.refresh(booking)
    return booking


@router.patch("/{booking_id}/status", response_model=schemas.BookingResponse)
def update_booking_status(
    booking_id: int,
    payload:    schemas.BookingStatusUpdate,
    db:         Session    = Depends(get_db),
    user:       models.User = Depends(require_role("admin", "fleet_manager"))
):
    """
    Advance the booking through its lifecycle (admin/fleet manager).

    Valid transitions only:
      BOOKED → PICKED_UP  (when customer collects vehicle)
      PICKED_UP → RETURNED  (use /return endpoint for this — it calculates late fee)
      BOOKED → CANCELLED

    When status moves to PICKED_UP: vehicle status → RENTED
    When CANCELLED: vehicle status → AVAILABLE again
    """
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # State transition guard
    new_status = payload.rental_status

    if new_status == models.RentalStatus.PICKED_UP:
        if booking.payment_status != models.PaymentStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Cannot pickup — payment not completed")
        if booking.rental_status != models.RentalStatus.BOOKED:
            raise HTTPException(status_code=400, detail="Booking is not in BOOKED state")
        booking.actual_pickup_time    = datetime.utcnow()
        booking.vehicle.status        = models.VehicleStatus.RENTED

    elif new_status == models.RentalStatus.CANCELLED:
        if booking.rental_status == models.RentalStatus.PICKED_UP:
            raise HTTPException(status_code=400, detail="Cannot cancel a booking already picked up")
        booking.vehicle.status = models.VehicleStatus.AVAILABLE

    booking.rental_status = new_status
    if payload.notes:
        booking.notes = payload.notes

    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/return", response_model=schemas.BookingResponse)
def process_return(
    booking_id: int,
    db:         Session    = Depends(get_db),
    user:       models.User = Depends(require_role("admin", "fleet_manager"))
):
    """
    Process vehicle return — calculates late fee if applicable.

    Steps:
      1. Record actual return time
      2. Calculate late fee vs planned end_datetime
      3. Update total_cost += late_fee
      4. Set rental_status = RETURNED
      5. Set vehicle.status = AVAILABLE (ready for next customer)

    USER STORY — SARAH RETURNS 2 HRS LATE:
      Planned end: Monday 10 AM
      Actual return: Monday 12 PM (2 hrs late)
      Late fee = ceil(2) × ₹150 × 2 = ₹600
      Total updated: ₹4554 + ₹600 = ₹5154
    """
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.rental_status != models.RentalStatus.PICKED_UP:
        raise HTTPException(status_code=400, detail="Vehicle not currently picked up")

    now        = datetime.utcnow()
    late_fee   = calculate_late_fee(booking.vehicle, booking.end_datetime, now)

    booking.actual_return_time = now
    booking.late_fee           = late_fee
    booking.total_cost         = (booking.total_cost or 0) + late_fee
    booking.rental_status      = models.RentalStatus.RETURNED
    booking.vehicle.status     = models.VehicleStatus.AVAILABLE   # back to pool

    db.commit()
    db.refresh(booking)
    return booking

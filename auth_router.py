"""
models.py — SQLAlchemy ORM table definitions

Each Python class below maps 1-to-1 with a PostgreSQL table.
SQLAlchemy reads these class definitions and creates the actual tables
when we call Base.metadata.create_all(engine) in main.py.

ENTITY RELATIONSHIPS (ER summary):
  User  1──* Booking  *──1  Vehicle
  Vehicle 1──* MaintenanceLog
  PricingRule  (standalone lookup table)

WHY ENUMS?
  Python enums restrict column values to a known set.
  e.g., VehicleStatus can only ever be "available", "rented",
  "under_maintenance", or "inactive". Any other value is rejected
  at the Python level before it even reaches the DB.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    Boolean, ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


# ──────────────────────────────────────────────────────────────
#  ENUMS  — predefined choices that protect data integrity
# ──────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    """Three distinct actor types in the platform."""
    CUSTOMER      = "customer"
    ADMIN         = "admin"
    FLEET_MANAGER = "fleet_manager"


class VehicleType(str, enum.Enum):
    """Physical category of the vehicle."""
    CAR   = "car"
    BIKE  = "bike"
    VAN   = "van"
    SUV   = "suv"
    TRUCK = "truck"


class VehicleStatus(str, enum.Enum):
    """
    Operational state of a vehicle.
    State machine:
      available ──▶ rented ──▶ available
      available ──▶ under_maintenance ──▶ available
      any       ──▶ inactive  (decommissioned)
    """
    AVAILABLE         = "available"
    RENTED            = "rented"
    UNDER_MAINTENANCE = "under_maintenance"
    INACTIVE          = "inactive"


class RentalStatus(str, enum.Enum):
    """
    Lifecycle of a single booking.
    State machine:
      booked ──▶ picked_up ──▶ returned
      booked ──▶ cancelled
    """
    BOOKED    = "booked"      # Payment done, awaiting physical pickup
    PICKED_UP = "picked_up"   # Customer has the keys
    RETURNED  = "returned"    # Vehicle back at hub; rental closed
    CANCELLED = "cancelled"   # Booking voided before pickup


class PaymentStatus(str, enum.Enum):
    PENDING   = "pending"
    COMPLETED = "completed"
    REFUNDED  = "refunded"


class FuelType(str, enum.Enum):
    PETROL   = "petrol"
    DIESEL   = "diesel"
    ELECTRIC = "electric"
    HYBRID   = "hybrid"
    CNG      = "cng"


# ──────────────────────────────────────────────────────────────
#  USER
# ──────────────────────────────────────────────────────────────

class User(Base):
    """
    Single table for all user roles (customer / admin / fleet_manager).

    WHY one table instead of three?
      - Simpler joins (booking.customer_id always points here)
      - Role-based behaviour is handled in API logic, not DB structure
      - Easy to add a new role later by extending the enum
    """
    __tablename__ = "users"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(100), nullable=False)
    # index=True speeds up login queries that filter by email
    email          = Column(String(150), unique=True, index=True, nullable=False)
    phone          = Column(String(20))
    # NEVER store plain text passwords — always store bcrypt hash
    password_hash  = Column(String(255), nullable=False)
    role           = Column(SAEnum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    driving_license = Column(String(50))   # Mandatory for customers
    is_active      = Column(Boolean, default=True)

    # server_default=func.now() — DB sets timestamp; survives clock-skew between app servers
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    # SQLAlchemy relationship — lets us do user.bookings in Python
    # back_populates creates the reverse: booking.customer
    bookings = relationship("Booking", back_populates="customer")


# ──────────────────────────────────────────────────────────────
#  VEHICLE
# ──────────────────────────────────────────────────────────────

class Vehicle(Base):
    """
    Represents every physical vehicle in the rental fleet.
    Stores identity, specs, compliance documents, pricing, and status.
    """
    __tablename__ = "vehicles"

    id                  = Column(Integer, primary_key=True, index=True)

    # Identity
    vehicle_type        = Column(SAEnum(VehicleType), nullable=False)
    brand               = Column(String(50), nullable=False)   # e.g., Toyota
    model               = Column(String(50), nullable=False)   # e.g., Fortuner
    year                = Column(Integer)
    color               = Column(String(30))

    # Technical specs
    fuel_type           = Column(SAEnum(FuelType), nullable=False)
    seating_capacity    = Column(Integer, nullable=False)

    # Compliance — fitness = roadworthy cert, insurance = third-party coverage
    registration_number = Column(String(20), unique=True, nullable=False)
    fitness_expiry      = Column(DateTime)
    insurance_expiry    = Column(DateTime)

    # Pricing
    price_per_hour      = Column(Float, nullable=False)
    price_per_day       = Column(Float, nullable=False)

    # Operational state
    status              = Column(SAEnum(VehicleStatus), default=VehicleStatus.AVAILABLE)

    # Photo stored as a relative path: "/static/vehicles/toyota_fortuner.jpg"
    photo_path          = Column(String(255), default="/static/default_vehicle.jpg")

    description         = Column(Text)
    location            = Column(String(100), default="Main Hub")

    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())

    bookings           = relationship("Booking", back_populates="vehicle")
    maintenance_logs   = relationship("MaintenanceLog", back_populates="vehicle")


# ──────────────────────────────────────────────────────────────
#  BOOKING
# ──────────────────────────────────────────────────────────────

class Booking(Base):
    """
    The core transaction record — every rental starts and ends here.

    Links:  Customer ──▶ Booking ◀── Vehicle

    Financial fields:
      base_cost         = raw duration × rate (before any rules)
      total_cost        = base + surcharges − discounts
      late_fee          = charged on return if vehicle is returned late
      discount_applied  = coupon or other discount amount
    """
    __tablename__ = "bookings"

    id              = Column(Integer, primary_key=True, index=True)

    # Foreign keys — referential integrity enforced at DB level
    customer_id     = Column(Integer, ForeignKey("users.id"),    nullable=False)
    vehicle_id      = Column(Integer, ForeignKey("vehicles.id"), nullable=False)

    # Planned window
    start_datetime  = Column(DateTime, nullable=False)
    end_datetime    = Column(DateTime, nullable=False)

    # Actual times (may differ from plan)
    actual_pickup_time = Column(DateTime)
    actual_return_time = Column(DateTime)

    # Financial breakdown
    base_cost         = Column(Float, default=0.0)
    total_cost        = Column(Float, default=0.0)
    late_fee          = Column(Float, default=0.0)
    discount_applied  = Column(Float, default=0.0)

    # Payment
    payment_mode      = Column(String(50), default="card")   # card / cash / upi
    payment_status    = Column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING)

    # Rental lifecycle
    rental_status     = Column(SAEnum(RentalStatus), default=RentalStatus.BOOKED)

    # Optional coupon
    coupon_code       = Column(String(50))

    notes             = Column(Text)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), onupdate=func.now())

    # ORM relationships
    customer = relationship("User",    back_populates="bookings")
    vehicle  = relationship("Vehicle", back_populates="bookings")


# ──────────────────────────────────────────────────────────────
#  MAINTENANCE LOG
# ──────────────────────────────────────────────────────────────

class MaintenanceLog(Base):
    """
    Every maintenance event for every vehicle.
    Fleet managers create these to track vehicle health.
    next_due_date is used to proactively schedule future service.
    """
    __tablename__ = "maintenance_logs"

    id               = Column(Integer, primary_key=True, index=True)
    vehicle_id       = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    performed_by     = Column(Integer, ForeignKey("users.id"))  # fleet manager's user id

    maintenance_type = Column(String(100), nullable=False)  # oil_change, tire, etc.
    description      = Column(Text)
    cost             = Column(Float, default=0.0)
    date_performed   = Column(DateTime, nullable=False)
    next_due_date    = Column(DateTime)   # reminder trigger

    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    vehicle          = relationship("Vehicle", back_populates="maintenance_logs")


# ──────────────────────────────────────────────────────────────
#  PRICING RULE
# ──────────────────────────────────────────────────────────────

class PricingRule(Base):
    """
    Admin-configurable rules that dynamically adjust rental cost.

    rule_type values and their effect:
      'weekend'  → multiplier applied to weekend portion of booking
      'seasonal' → multiplier for date-range (e.g., summer peak +15%)
      'coupon'   → discount_percent subtracted from total; requires coupon_code
      'late_fee' → multiplier on hourly rate for each hour of late return

    Examples stored in DB:
      {rule_name:"Weekend Surcharge", rule_type:"weekend", multiplier:1.20}
      {rule_name:"SAVE10",            rule_type:"coupon",  coupon_code:"SAVE10", discount_percent:10}
    """
    __tablename__ = "pricing_rules"

    id              = Column(Integer, primary_key=True, index=True)
    rule_name       = Column(String(100), nullable=False)
    rule_type       = Column(String(50),  nullable=False)

    # 1.20 = 20% surcharge;  0.90 = 10% discount via multiplier
    multiplier      = Column(Float, default=1.0)
    discount_percent = Column(Float, default=0.0)

    coupon_code     = Column(String(50), unique=True)
    max_uses        = Column(Integer)             # null = unlimited
    current_uses    = Column(Integer, default=0)

    start_date      = Column(DateTime)
    end_date        = Column(DateTime)

    description     = Column(Text)
    is_active       = Column(Boolean, default=True)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())

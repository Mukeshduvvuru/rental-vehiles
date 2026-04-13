"""
schemas.py — Pydantic models for API request/response validation

WHY separate schemas from SQLAlchemy models?
  SQLAlchemy models describe the DATABASE (tables, columns, foreign keys).
  Pydantic schemas describe the API CONTRACT (what JSON comes in / goes out).

  This separation gives us:
    1. Security  — password_hash is in the DB model but NEVER appears in
                   UserResponse (it would be a security breach to expose it).
    2. Flexibility — CreateBooking needs only vehicle_id + dates; the response
                     includes nested vehicle details. Two different shapes.
    3. Validation — Pydantic auto-validates types, ranges, and regex on every
                    incoming request. Bad data is rejected before it hits the DB.
    4. Auto-docs  — FastAPI reads these schemas to generate Swagger/OpenAPI docs.

HOW PYDANTIC VALIDATION WORKS:
  When a client POSTs JSON, FastAPI passes it to the matching schema class.
  Pydantic raises HTTP 422 (Unprocessable Entity) with clear field-level
  error messages if any constraint is violated.
"""

from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional, List
from datetime import datetime
from models import UserRole, VehicleType, VehicleStatus, RentalStatus, PaymentStatus, FuelType


# ──────────────────────────────────────────────────────────────
#  AUTH SCHEMAS
# ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    """
    Payload for POST /api/auth/register.
    Customers MUST include driving_license; admins/fleet managers need not.
    """
    name:            str      = Field(..., min_length=2, max_length=100)
    email:           EmailStr                          # validates format + MX record
    phone:           Optional[str] = None
    password:        str      = Field(..., min_length=6, description="Min 6 characters")
    role:            UserRole = UserRole.CUSTOMER
    driving_license: Optional[str] = None

    @field_validator("driving_license")
    @classmethod
    def license_required_for_customer(cls, v, info):
        """
        Custom business-rule validator.
        Pydantic calls this automatically after type-checking.
        Raising ValueError causes a 422 with a human-readable message.
        """
        if info.data.get("role") == UserRole.CUSTOMER and not v:
            raise ValueError("Driving license is required for customers")
        return v


class UserLogin(BaseModel):
    """Payload for POST /api/auth/login."""
    email:    EmailStr
    password: str


class UserResponse(BaseModel):
    """
    User data returned from any endpoint.
    NOTE: password_hash is intentionally absent — never sent over the wire.
    """
    id:              int
    name:            str
    email:           str
    phone:           Optional[str]
    role:            UserRole
    driving_license: Optional[str]
    created_at:      datetime

    model_config = {"from_attributes": True}   # lets Pydantic read SQLAlchemy objects


class Token(BaseModel):
    """JWT response returned after successful login."""
    access_token: str
    token_type:   str = "bearer"
    user:         UserResponse


# ──────────────────────────────────────────────────────────────
#  VEHICLE SCHEMAS
# ──────────────────────────────────────────────────────────────

class VehicleCreate(BaseModel):
    """Admin sends this to add a new vehicle to the fleet."""
    vehicle_type:        VehicleType
    brand:               str   = Field(..., min_length=2)
    model:               str   = Field(..., min_length=1)
    year:                Optional[int]   = None
    color:               Optional[str]  = None
    fuel_type:           FuelType
    seating_capacity:    int   = Field(..., ge=1, le=50)
    registration_number: str
    fitness_expiry:      Optional[datetime] = None
    insurance_expiry:    Optional[datetime] = None
    price_per_hour:      float = Field(..., gt=0, description="Must be positive")
    price_per_day:       float = Field(..., gt=0)
    description:         Optional[str] = None
    location:            Optional[str] = "Main Hub"


class VehicleUpdate(BaseModel):
    """
    Partial update — every field is Optional so clients only send what changed.
    PATCH semantics: only provided fields are modified.
    """
    brand:           Optional[str]           = None
    model:           Optional[str]           = None
    status:          Optional[VehicleStatus] = None
    price_per_hour:  Optional[float]         = None
    price_per_day:   Optional[float]         = None
    description:     Optional[str]           = None
    location:        Optional[str]           = None
    fitness_expiry:  Optional[datetime]      = None
    insurance_expiry: Optional[datetime]     = None


class VehicleResponse(BaseModel):
    """Full vehicle record returned from the API."""
    id:                  int
    vehicle_type:        VehicleType
    brand:               str
    model:               str
    year:                Optional[int]
    color:               Optional[str]
    fuel_type:           FuelType
    seating_capacity:    int
    registration_number: str
    fitness_expiry:      Optional[datetime]
    insurance_expiry:    Optional[datetime]
    price_per_hour:      float
    price_per_day:       float
    status:              VehicleStatus
    photo_path:          Optional[str]
    description:         Optional[str]
    location:            Optional[str]
    created_at:          datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────
#  BOOKING SCHEMAS
# ──────────────────────────────────────────────────────────────

class BookingCreate(BaseModel):
    """Customer sends this to create a new booking."""
    vehicle_id:     int
    start_datetime: datetime
    end_datetime:   datetime
    payment_mode:   str           = "card"   # card | cash | upi
    coupon_code:    Optional[str] = None
    notes:          Optional[str] = None

    @field_validator("end_datetime")
    @classmethod
    def end_must_be_after_start(cls, v, info):
        """
        Business rule: you can't return a car before picking it up.
        This guard runs before the booking is ever written to the DB.
        """
        if "start_datetime" in info.data and v <= info.data["start_datetime"]:
            raise ValueError("end_datetime must be after start_datetime")
        return v


class BookingResponse(BaseModel):
    """Full booking details including nested vehicle + customer info."""
    id:                 int
    customer_id:        int
    vehicle_id:         int
    start_datetime:     datetime
    end_datetime:       datetime
    actual_pickup_time: Optional[datetime]
    actual_return_time: Optional[datetime]
    base_cost:          Optional[float]
    total_cost:         Optional[float]
    late_fee:           Optional[float]
    payment_mode:       str
    payment_status:     PaymentStatus
    rental_status:      RentalStatus
    coupon_code:        Optional[str]
    discount_applied:   Optional[float]
    notes:              Optional[str]
    created_at:         datetime
    vehicle:            Optional[VehicleResponse] = None
    customer:           Optional[UserResponse]    = None

    model_config = {"from_attributes": True}


class BookingStatusUpdate(BaseModel):
    """
    Used to advance the rental state machine:
      BOOKED → PICKED_UP → RETURNED  or  → CANCELLED
    """
    rental_status: RentalStatus
    notes:         Optional[str] = None


class PricingEstimate(BaseModel):
    """
    Pre-booking price breakdown.
    Shown to customer on the booking confirmation page before payment.
    """
    base_cost:            float
    weekend_surcharge:    float
    coupon_discount:      float
    total_cost:           float
    duration_hours:       float
    breakdown:            dict


# ──────────────────────────────────────────────────────────────
#  MAINTENANCE SCHEMAS
# ──────────────────────────────────────────────────────────────

class MaintenanceCreate(BaseModel):
    """Fleet manager sends this when logging a maintenance event."""
    vehicle_id:       int
    maintenance_type: str   = Field(..., min_length=2)
    description:      Optional[str]      = None
    cost:             float = Field(default=0.0, ge=0)
    date_performed:   datetime
    next_due_date:    Optional[datetime] = None


class MaintenanceResponse(BaseModel):
    id:               int
    vehicle_id:       int
    performed_by:     Optional[int]
    maintenance_type: str
    description:      Optional[str]
    cost:             float
    date_performed:   datetime
    next_due_date:    Optional[datetime]
    created_at:       datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────
#  PRICING RULE SCHEMAS
# ──────────────────────────────────────────────────────────────

class PricingRuleCreate(BaseModel):
    """Admin creates a new pricing rule (weekend surcharge, coupon, etc.)."""
    rule_name:        str
    rule_type:        str   # weekend | seasonal | coupon | late_fee
    multiplier:       float = Field(default=1.0,  ge=0.1, le=5.0)
    discount_percent: float = Field(default=0.0,  ge=0.0, le=100.0)
    coupon_code:      Optional[str] = None
    max_uses:         Optional[int] = None
    start_date:       Optional[datetime] = None
    end_date:         Optional[datetime] = None
    description:      Optional[str] = None


class PricingRuleResponse(BaseModel):
    id:               int
    rule_name:        str
    rule_type:        str
    multiplier:       float
    discount_percent: float
    coupon_code:      Optional[str]
    max_uses:         Optional[int]
    current_uses:     int
    start_date:       Optional[datetime]
    end_date:         Optional[datetime]
    description:      Optional[str]
    is_active:        bool

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────
#  DASHBOARD SCHEMAS
# ──────────────────────────────────────────────────────────────

class AdminDashboardStats(BaseModel):
    """
    Summary metrics shown on the Admin Dashboard.
    Computed via aggregation queries in dashboard_router.py.
    """
    total_vehicles:      int
    available_vehicles:  int
    active_rentals:      int
    total_revenue:       float
    monthly_revenue:     float
    total_customers:     int
    pending_maintenance: int

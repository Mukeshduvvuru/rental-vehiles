"""
utils/pricing.py — Rental Pricing Calculation Engine

REAL-WORLD PROBLEM THIS SOLVES:
  A customer books a car from Friday 6 PM to Monday 10 AM.
  How much should they pay? It's not simply hours × hourly_rate because:
    - A "day rate" is usually cheaper per hour than the hourly rate
    - Saturday and Sunday have a 20% weekend surcharge
    - They might have a coupon code (e.g., SAVE10 = 10% off)
    - If they return 2 hours late, they owe a late-return penalty

USER STORY — SARAH'S BOOKING:
  Sarah books a Toyota Fortuner (₹150/hr, ₹1000/day) from
  Fri 6 PM → Mon 10 AM (64 hours = 2 full days + 16 hours remaining).

  Step 1 — Base cost:
    Hourly:  64 × ₹150  = ₹9,600
    Mixed:   2 × ₹1000  + 16 × ₹150  = ₹2,000 + ₹2,400 = ₹4,400  ← cheaper
    base_cost = ₹4,400

  Step 2 — Weekend surcharge (Sat + Sun = 48 of the 64 hours):
    weekend_fraction = 48/64 = 0.75
    surcharge = ₹4,400 × 0.75 × 0.20 = ₹660
    after_weekend = ₹5,060

  Step 3 — Coupon SAVE10 (10% off):
    discount = ₹5,060 × 0.10 = ₹506
    total = ₹4,554

  Step 4 — Late return (2 extra hours):
    late_fee = 2 × ₹150 × 2 = ₹600  (2× penalty rate)
    grand_total = ₹5,154
"""

import math
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session
import models


# ──────────────────────────────────────────────────────────────
#  Duration helpers
# ──────────────────────────────────────────────────────────────

def calculate_duration(start: datetime, end: datetime) -> Tuple[float, int, float]:
    """
    Split rental duration into full days and leftover hours.

    Returns:
        total_hours    (float) — entire rental length in hours
        full_days      (int)   — complete 24-hour blocks
        remaining_hours(float) — hours after removing full days

    Example:
        64-hour rental → total=64.0, full_days=2, remaining=16.0
    """
    total_seconds  = (end - start).total_seconds()
    total_hours    = total_seconds / 3600
    full_days      = int(total_hours // 24)
    remaining_hours = total_hours % 24
    return total_hours, full_days, remaining_hours


def get_base_cost(vehicle: models.Vehicle, start: datetime, end: datetime) -> float:
    """
    Calculate raw cost before any pricing rules.

    Strategy: compare pure-hourly vs mixed day+hour, use the cheaper one.
    This is CUSTOMER-FRIENDLY — same as most real rental companies.
    """
    total_hours, full_days, remaining_hours = calculate_duration(start, end)

    # Option A: pure hourly (good for short rentals)
    hourly_cost = total_hours * vehicle.price_per_hour

    # Option B: full days at day rate + leftover hours at hourly rate
    mixed_cost  = (full_days * vehicle.price_per_day) + (remaining_hours * vehicle.price_per_hour)

    return round(min(hourly_cost, mixed_cost), 2)


# ──────────────────────────────────────────────────────────────
#  Rule appliers
# ──────────────────────────────────────────────────────────────

def apply_weekend_surcharge(
    base_cost: float,
    start: datetime,
    end: datetime,
    db: Session
) -> Tuple[float, float]:
    """
    Apply the weekend surcharge rule from the DB.

    HOW IT WORKS:
      We count how many of the rented hours fall on Sat (weekday=5) or Sun (=6).
      The surcharge is proportional to that fraction.

      weekend_fraction = weekend_hours / total_hours
      surcharge = base_cost × weekend_fraction × (multiplier - 1)

    Returns (cost_after_surcharge, surcharge_amount)
    """
    # Fetch the active weekend rule (admin may have disabled it)
    rule = db.query(models.PricingRule).filter(
        models.PricingRule.rule_type == "weekend",
        models.PricingRule.is_active == True
    ).first()

    if not rule:
        return base_cost, 0.0   # No rule configured → no surcharge

    # Walk through each hour of the rental window
    total_hours   = (end - start).total_seconds() / 3600
    weekend_hours = 0.0
    cursor        = start

    while cursor < end:
        hour_end = cursor + timedelta(hours=1)
        if hour_end > end:
            # Partial last hour — credit proportionally
            fraction = (end - cursor).total_seconds() / 3600
        else:
            fraction = 1.0

        # weekday(): Mon=0 … Fri=4, Sat=5, Sun=6
        if cursor.weekday() >= 5:
            weekend_hours += fraction
        cursor += timedelta(hours=1)

    weekend_fraction = weekend_hours / total_hours if total_hours > 0 else 0
    surcharge        = base_cost * weekend_fraction * (rule.multiplier - 1)

    return round(base_cost + surcharge, 2), round(surcharge, 2)


def apply_coupon(cost: float, coupon_code: Optional[str], db: Session) -> Tuple[float, float]:
    """
    Validate and apply a coupon code.

    Validation checks (in order):
      1. Coupon exists and is_active
      2. Usage limit not exceeded (max_uses may be None = unlimited)
      3. Within start_date / end_date window (if set)

    Side effect: increments current_uses on valid coupon.

    Returns (discounted_cost, discount_amount)
    """
    if not coupon_code:
        return cost, 0.0

    rule = db.query(models.PricingRule).filter(
        models.PricingRule.coupon_code == coupon_code.upper(),
        models.PricingRule.is_active   == True
    ).first()

    if not rule:
        return cost, 0.0   # silently ignore invalid coupons

    # Usage limit check
    if rule.max_uses is not None and rule.current_uses >= rule.max_uses:
        return cost, 0.0

    # Date window check
    now = datetime.utcnow()
    if rule.start_date and now < rule.start_date:
        return cost, 0.0
    if rule.end_date and now > rule.end_date:
        return cost, 0.0

    discount = round(cost * (rule.discount_percent / 100), 2)

    # Consume one use of the coupon
    rule.current_uses += 1
    db.commit()

    return round(cost - discount, 2), discount


def calculate_late_fee(
    vehicle: models.Vehicle,
    planned_end:    datetime,
    actual_return:  datetime
) -> float:
    """
    Penalty for returning the vehicle after the agreed end time.

    Policy: 2× hourly rate per extra hour (ceiling — even 5 min late = 1 hr charge).
    WHY 2×? It discourages late returns that could block the next customer's booking.
    """
    if actual_return <= planned_end:
        return 0.0   # returned on time or early

    late_seconds = (actual_return - planned_end).total_seconds()
    late_hours   = late_seconds / 3600
    late_hours_ceil = math.ceil(late_hours)   # round UP to nearest full hour

    return round(late_hours_ceil * vehicle.price_per_hour * 2, 2)


# ──────────────────────────────────────────────────────────────
#  Master pricing function
# ──────────────────────────────────────────────────────────────

def calculate_full_price(
    vehicle:      models.Vehicle,
    start:        datetime,
    end:          datetime,
    coupon_code:  Optional[str],
    db:           Session
) -> Dict:
    """
    Orchestrates the complete pricing calculation and returns a detailed breakdown.

    This breakdown is shown to the customer on the booking confirmation screen
    so they understand exactly what they're paying for (transparency builds trust).

    Returns dict with keys:
      base_cost, weekend_surcharge, coupon_discount, total_cost,
      duration_hours, breakdown (detailed intermediate values)
    """
    # 1. Duration-based cost
    base = get_base_cost(vehicle, start, end)

    # 2. Weekend surcharge on top
    after_weekend, weekend_surcharge = apply_weekend_surcharge(base, start, end, db)

    # 3. Coupon discount
    final, coupon_discount = apply_coupon(after_weekend, coupon_code, db)

    return {
        "base_cost":         base,
        "weekend_surcharge": weekend_surcharge,
        "coupon_discount":   coupon_discount,
        "total_cost":        final,
        "duration_hours":    round((end - start).total_seconds() / 3600, 1),
        "breakdown": {
            "price_per_hour":  vehicle.price_per_hour,
            "price_per_day":   vehicle.price_per_day,
            "base_before_rules": base,
            "after_weekend":   after_weekend,
            "after_coupon":    final,
        }
    }

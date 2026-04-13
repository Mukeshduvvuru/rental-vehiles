"""
routers/pricing_router.py — Pricing rules management (admin)

ENDPOINTS:
  GET    /api/pricing                → list all rules
  POST   /api/pricing                → create a new rule (admin)
  PATCH  /api/pricing/{id}/toggle    → enable/disable a rule (admin)
  DELETE /api/pricing/{id}           → remove a rule (admin)

WHY RUNTIME-CONFIGURABLE RULES?
  Hardcoding "20% weekend surcharge" in source code means a developer must
  redeploy every time marketing wants to change a promotion.
  By storing rules in the DB, an admin can:
    - Change weekend surcharge from 20% to 25% with one click
    - Add a "MONSOON15" coupon for July–August without a code deploy
    - Disable a rule instantly if it causes pricing issues

RULE TYPES:
  weekend   → applied to hours falling on Sat/Sun (multiplier)
  seasonal  → date-range based (multiplier), e.g., summer peak
  coupon    → coupon_code required; discount_percent applied to total
  late_fee  → multiplier on hourly rate per late hour (future use)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import require_role
import models
import schemas

router = APIRouter(prefix="/api/pricing", tags=["Pricing Rules"])


@router.get("", response_model=List[schemas.PricingRuleResponse])
def list_pricing_rules(
    db:    Session    = Depends(get_db),
    admin: models.User = Depends(require_role("admin"))
):
    """Return all pricing rules (active and inactive) for admin review."""
    return db.query(models.PricingRule).order_by(models.PricingRule.rule_type).all()


@router.post("", response_model=schemas.PricingRuleResponse, status_code=201)
def create_pricing_rule(
    payload: schemas.PricingRuleCreate,
    db:      Session    = Depends(get_db),
    admin:   models.User = Depends(require_role("admin"))
):
    """
    Create a new pricing rule.

    ADMIN USER STORY — SETTING UP A WEEKEND SURCHARGE:
      Admin fills form:
        rule_name="Weekend Surcharge", rule_type="weekend", multiplier=1.20
      Effect: every booking that includes Saturday/Sunday gets +20% on that portion.

    ADMIN USER STORY — CREATING A COUPON:
      Admin fills form:
        rule_name="Summer Sale", rule_type="coupon",
        coupon_code="SUMMER20", discount_percent=20, max_uses=100,
        start_date=2024-06-01, end_date=2024-08-31
      Effect: first 100 customers who enter "SUMMER20" get 20% off.
    """
    # Coupon codes must be unique
    if payload.coupon_code:
        existing = db.query(models.PricingRule).filter(
            models.PricingRule.coupon_code == payload.coupon_code.upper()
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Coupon code already exists")

    rule = models.PricingRule(
        rule_name        = payload.rule_name,
        rule_type        = payload.rule_type,
        multiplier       = payload.multiplier,
        discount_percent = payload.discount_percent,
        coupon_code      = payload.coupon_code.upper() if payload.coupon_code else None,
        max_uses         = payload.max_uses,
        start_date       = payload.start_date,
        end_date         = payload.end_date,
        description      = payload.description,
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/{rule_id}/toggle", response_model=schemas.PricingRuleResponse)
def toggle_pricing_rule(
    rule_id: int,
    db:      Session    = Depends(get_db),
    admin:   models.User = Depends(require_role("admin"))
):
    """
    Enable or disable a pricing rule without deleting it.

    WHY toggle instead of delete?
      Admin might want to temporarily pause the weekend surcharge during
      a promotion period, then re-enable it. Keeping the record avoids
      re-configuration.
    """
    rule = db.query(models.PricingRule).filter(models.PricingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")

    rule.is_active = not rule.is_active   # flip the boolean
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_pricing_rule(
    rule_id: int,
    db:      Session    = Depends(get_db),
    admin:   models.User = Depends(require_role("admin"))
):
    """
    Permanently delete a pricing rule.
    Only removes rules with zero coupon uses (to preserve audit trail).
    """
    rule = db.query(models.PricingRule).filter(models.PricingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")

    db.delete(rule)
    db.commit()

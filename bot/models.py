from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Text, Float, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    referral_code = Column(String, unique=True, index=True)
    bonus_balance = Column(Integer, default=0)

    trial_used = Column(Boolean, default=False)

    referrer = relationship("User", remote_side=[id], backref="referrals")
    vpn_keys = relationship("VPNKey", back_populates="user", lazy="dynamic")

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price_stars = Column(Integer, nullable=True)
    price_rub = Column(Integer, nullable=True)
    duration_days = Column(Integer, nullable=False)
    traffic_limit_gb = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)

class PaymentMethod(str, enum.Enum):
    STARS = "stars"
    YOOKASSA = "yookassa"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="RUB")
    method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(String, default="pending")
    payment_id = Column(String, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

class VPNKey(Base):
    __tablename__ = "vpn_keys"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    key_uuid = Column(String, unique=True, nullable=False)
    key_data = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="vpn_keys")
    plan = relationship("Plan")

class ReferralBonus(Base):
    __tablename__ = "referral_bonuses"

    id = Column(Integer, primary_key=True)
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    referred_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TrialUsage(Base):
    __tablename__ = "trial_usage"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    used_at = Column(DateTime(timezone=True), server_default=func.now())
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

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
    
    # Referral system
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    referral_code = Column(String, unique=True, index=True)
    bonus_balance = Column(Integer, default=0)  # в звездах (или внутренней валюте)
    
    # Relations
    referrer = relationship("User", remote_side=[id], backref="referrals")
    vpn_keys = relationship("VPNKey", back_populates="user", lazy="dynamic")
    
class Plan(Base):
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price_stars = Column(Integer, nullable=False)  # цена в Telegram Stars
    duration_days = Column(Integer, nullable=False)
    traffic_limit_gb = Column(Integer, nullable=True)  # None = безлимит
    is_active = Column(Boolean, default=True)
    
class VPNKey(Base):
    __tablename__ = "vpn_keys"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    key_uuid = Column(String, unique=True, nullable=False)  # UUID ключа в панели
    key_data = Column(Text, nullable=True)  # ссылка/конфиг
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
    amount = Column(Integer, nullable=False)  # количество звезд
    created_at = Column(DateTime(timezone=True), server_default=func.now())
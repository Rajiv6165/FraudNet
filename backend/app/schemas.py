from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from uuid import UUID

# User Schemas
class UserBase(BaseModel):
    name: str
    home_country: str = Field(..., max_length=3, description="3-letter ISO country code")
    risk_tier: str = "low"

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Device Schemas
class DeviceBase(BaseModel):
    id: str
    fingerprint: str

class Device(DeviceBase):
    first_seen: datetime

    class Config:
        from_attributes = True

# Card Schemas
class CardBase(BaseModel):
    last_four: str = Field(..., max_length=4)
    issuer: str
    user_id: int

class CardCreate(CardBase):
    pass

class Card(CardBase):
    id: int

    class Config:
        from_attributes = True

# Transaction Schemas
class TransactionBase(BaseModel):
    user_id: int
    card_id: int
    device_id: str
    ip_address: str
    amount: Decimal
    merchant: str
    merchant_category: str
    country: str = Field(..., max_length=3)
    status: str = "approved"

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Fraud Score Schemas
class FraudScore(BaseModel):
    transaction_id: UUID
    velocity_score: Decimal
    deviation_score: Decimal
    ring_score: Decimal
    composite_score: Decimal
    flagged: bool
    computed_at: datetime

    class Config:
        from_attributes = True

# Combined Transaction & Score Schema for Live Stream
class TransactionWithScore(BaseModel):
    transaction_id: UUID
    user_id: int
    user_name: str
    amount: Decimal
    merchant: str
    merchant_category: str
    country: str
    created_at: datetime
    device_id: str
    ip_address: str
    velocity_score: Decimal
    deviation_score: Decimal
    ring_score: Decimal
    composite_score: Decimal
    flagged: bool

# Fraud Ring Schema
class FraudRing(BaseModel):
    ring_id: str
    user_id: int
    ring_size: int
    ring_volume: Decimal

# Materialized View / Dashboard Schema
class DashboardMetric(BaseModel):
    merchant_category: str
    country: str
    transaction_hour: datetime
    transaction_count: int
    flagged_count: int
    total_volume: Decimal
    avg_risk_score: Decimal

    class Config:
        from_attributes = True

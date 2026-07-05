import datetime
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, server_default=text("now()"))
    home_country = Column(String(3), nullable=False) # e.g. USA, IND
    risk_tier = Column(String(20), default="low") # low, medium, high

    cards = relationship("Card", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")

class Device(Base):
    __tablename__ = 'devices'

    id = Column(String(50), primary_key=True) # UUID or fingerprint
    fingerprint = Column(String(255), unique=True, index=True)
    first_seen = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, server_default=text("now()"))

    transactions = relationship("Transaction", back_populates="device")

class Card(Base):
    __tablename__ = 'cards'

    id = Column(Integer, primary_key=True, index=True)
    last_four = Column(String(4), nullable=False, index=True)
    issuer = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    user = relationship("User", back_populates="cards")
    transactions = relationship("Transaction", back_populates="card")

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    card_id = Column(Integer, ForeignKey('cards.id', ondelete='CASCADE'), nullable=False)
    device_id = Column(String(50), ForeignKey('devices.id'), nullable=False, index=True)
    ip_address = Column(String(45), nullable=False, index=True) # supports IPv4 and IPv6
    amount = Column(Numeric(12, 2), nullable=False)
    merchant = Column(String(100), nullable=False)
    merchant_category = Column(String(50), nullable=False)
    country = Column(String(3), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, server_default=text("now()"), index=True)
    status = Column(String(20), default="approved") # approved, declined

    user = relationship("User", back_populates="transactions")
    card = relationship("Card", back_populates="transactions")
    device = relationship("Device", back_populates="transactions")
    fraud_score = relationship("FraudScore", uselist=False, back_populates="transaction", cascade="all, delete-orphan")

class FraudScore(Base):
    __tablename__ = 'fraud_scores'

    transaction_id = Column(UUID(as_uuid=True), ForeignKey('transactions.id', ondelete='CASCADE'), primary_key=True)
    velocity_score = Column(Numeric(5, 2), default=0.0)
    deviation_score = Column(Numeric(5, 2), default=0.0)
    ring_score = Column(Numeric(5, 2), default=0.0)
    composite_score = Column(Numeric(5, 2), default=0.0)
    flagged = Column(Boolean, default=False, index=True)
    computed_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, server_default=text("now()"))

    transaction = relationship("Transaction", back_populates="fraud_score")

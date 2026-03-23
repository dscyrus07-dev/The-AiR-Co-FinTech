from sqlalchemy import Column, Integer, String, Float, Boolean, Date, Numeric, DateTime, func
from .session import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    normalized_name = Column(String(255), unique=True, nullable=False)
    category = Column(String(100), nullable=False)
    confidence = Column(Float, default=0.95)
    created_at = Column(DateTime, server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(255))
    bank_name = Column(String(100))
    account_type = Column(String(50))
    date = Column(Date)
    description = Column(String)
    debit = Column(Numeric(15, 2))
    credit = Column(Numeric(15, 2))
    balance = Column(Numeric(15, 2))
    category = Column(String(100))
    confidence = Column(Float)
    is_recurring = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

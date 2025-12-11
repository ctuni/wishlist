from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func

from .database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    source = Column(String, index=True)
    title = Column(String)
    image_url = Column(String)
    price = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    entry_type = Column(String, default="product")
    category = Column(String, index=True, nullable=True)
    purchased = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

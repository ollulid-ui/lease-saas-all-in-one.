import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    leases = relationship("Lease", back_populates="user")

class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key = Column(String, unique=True, index=True, nullable=False)
    plan = Column(String, default="starter")
    active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    monthly_limit = Column(Integer, default=None)
    last_reset = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class RateLimit(Base):
    __tablename__ = "rate_limits"
    id = Column(Integer, primary_key=True)
    key = Column(String, index=True, nullable=False)
    window_start = Column(DateTime, index=True, nullable=False)
    count = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("key","window_start", name="uix_key_window"),)

class Lease(Base):
    __tablename__ = "leases"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    text_excerpt = Column(Text)
    json_result = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="leases")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

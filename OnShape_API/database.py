"""
Database Models and Configuration
Defines all data structures and database setup
"""

from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import uuid

from config import settings



# Database setup
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ============= MODELS =============

class User(Base):
    """User model for OnShape OAuth"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    onshape_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String, nullable=True)
    
    # Tokens
    access_token = Column(Text)  # Encrypted
    refresh_token = Column(Text, nullable=True)  # Encrypted
    token_expires_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def is_token_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.utcnow() > self.token_expires_at


class SavedDocument(Base):
    """Saved OnShape documents"""
    __tablename__ = "saved_documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    
    # OnShape IDs
    document_id = Column(String, index=True)
    workspace_id = Column(String)
    element_id = Column(String)
    element_type = Column(String, nullable=True)  # "Assembly" or "PartStudio"
    
    # Metadata
    document_name = Column(String)
    element_name = Column(String, nullable=True)
    
    # Cached data
    bom_data = Column(JSON, nullable=True)
    bbox_data = Column(JSON, nullable=True)
    properties_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "document_id": self.document_id,
            "workspace_id": self.workspace_id,
            "element_id": self.element_id,
            "element_type": self.element_type,
            "document_name": self.document_name,
            "element_name": self.element_name,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat(),
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None
        }


class BOMCache(Base):
    """Cache for BOM data"""
    __tablename__ = "bom_cache"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    document_id = Column(String, index=True)
    element_id = Column(String, index=True)
    
    # BOM data
    bom_flat = Column(JSON)  # Flattened BOM
    bom_structured = Column(JSON)  # Structured BOM
    
    # Metadata
    part_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    cached_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)  # Cache expiration


class PropertySync(Base):
    """Track property syncs"""
    __tablename__ = "property_syncs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    document_id = Column(String, index=True)
    element_id = Column(String, index=True)
    
    # Sync metadata
    property_name = Column(String)  # "Length", "Width", "Height"
    parts_updated = Column(Integer, default=0)
    errors = Column(JSON, nullable=True)  # List of errors
    
    # Status
    status = Column(String, default="pending")  # pending, success, failed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

# ============= DATABASE INITIALIZATION =============

def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
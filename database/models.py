# database/models.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean
from datetime import datetime

# This is the base class for your declarative models
Base = declarative_base()

# Example Model (you'll have your actual models here, e.g., Document, User, etc.)
class Document(Base):
    __tablename__ = 'documents'  # Essential for SQLAlchemy to know the table name
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False, unique=True)
    upload_date = Column(DateTime, default=datetime.utcnow)
    extracted_text = Column(Text)
    # Add other fields as per your application's needs
    
    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}')>"

class ProcessingStats(Base):
    __tablename__ = 'processing_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), nullable=True)
    operation_type = Column(String(100), nullable=False)  # e.g., 'sync', 'process', 'upload'
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    status = Column(String(50), default='pending')  # 'pending', 'completed', 'failed'
    error_message = Column(String(1000), nullable=True)
    records_processed = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    success_rate = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ProcessingStats(id={self.id}, operation='{self.operation_type}', status='{self.status}')>"
    
    def calculate_success_rate(self):
        """Calculate and update the success rate"""
        if self.records_processed > 0:
            self.success_rate = ((self.records_processed - self.records_failed) / self.records_processed) * 100
        else:
            self.success_rate = 0.0
        return self.success_rate
    
    def mark_completed(self):
        """Mark the processing as completed and calculate duration"""
        self.end_time = datetime.utcnow()
        self.status = 'completed'
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.calculate_success_rate()
    
    def mark_failed(self, error_message=None):
        """Mark the processing as failed"""
        self.end_time = datetime.utcnow()
        self.status = 'failed'
        if error_message:
            self.error_message = error_message
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()

# You would define other models (e.g., User, etc.) here
# class User(Base):
#     __tablename__ = 'users'
#     id = Column(Integer, primary_key=True)
#     username = Column(String(50), unique=True, nullable=False)
#     password_hash = Column(String(128), nullable=False)

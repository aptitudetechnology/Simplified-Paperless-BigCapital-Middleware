# database/models.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean
from datetime import datetime

# This is the base class for your declarative models
Base = declarative_base()

# Example Model (you'll have your actual models here, e.g., Document, User, etc.)
class Document(Base):
    __tablename__ = 'documents' # Essential for SQLAlchemy to know the table name

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False, unique=True)
    upload_date = Column(DateTime, default=datetime.utcnow)
    extracted_text = Column(Text)
    # Add other fields as per your application's needs

    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}')>"

# You would define other models (e.g., User, etc.) here
# class User(Base):
#     __tablename__ = 'users'
#     id = Column(Integer, primary_key=True)
#     username = Column(String(50), unique=True, nullable=False)
#     password_hash = Column(String(128), nullable=False)

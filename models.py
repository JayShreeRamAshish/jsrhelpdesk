from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Ensure the images directory exists
if not os.path.exists("images"):
    os.makedirs("images")

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    company_id = Column(Integer)
    #is_superuser = Column(Boolean, default=False)

class Visitor(Base):
    __tablename__ = 'visitors'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    company_id = Column(Integer)
    pre_registered = Column(Boolean, default=False)
    notified = Column(Boolean, default=False)
    check_in = Column(DateTime, default=None)
    check_out = Column(DateTime, default=None)
    temperature = Column(Float, default=None)
    health_status = Column(String, default=None)
    face_image_path = Column(String, default=None)
    visit_purpose = Column(String, default=None)
    person_to_meet = Column(String, default=None)
    department = Column(String, default=None)
    company_name = Column(String, default=None)
    visitor_location = Column(String, default=None)

Base.metadata.create_all(bind=engine)

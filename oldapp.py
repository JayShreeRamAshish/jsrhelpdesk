import streamlit as st
from sqlalchemy.orm import Session
from models import Visitor, User, SessionLocal, engine
from auth import create_user, authenticate_user, create_jwt_token, decode_jwt_token
from notifications import send_email, send_sms
from facial_recognition import detect_face, capture_face
import pandas as pd
import datetime
import cv2
import os
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

# Database session management
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to add a visitor
def add_visitor(db: Session, name: str, email: str, phone: str, company_id: int, visit_purpose: str, person_to_meet: str, department: str, company_name: str, visitor_location: str):
    visitor = Visitor(name=name, email=email, phone=phone, company_id=company_id, pre_registered=True, notified=True, visit_purpose=visit_purpose, person_to_meet=person_to_meet, department=department, company_name=company_name, visitor_location=visitor_location)
    db.add(visitor)
    db.commit()
    db.refresh(visitor)
    return visitor

# Function to check in a visitor
def check_in_visitor(db: Session, visitor_id: int, temperature: float, health_status: str, face_image_path: str):
    if not detect_face(face_image_path):
        return None, "Face not detected"
    
    visitor = db.query(Visitor).filter(Visitor.id == visitor_id).first()
    if visitor:
        visitor.check_in = datetime.datetime.utcnow()
        visitor.temperature = temperature
        visitor.health_status = health_status
        visitor.face_image_path = face_image_path
        db.commit()
    return visitor, "Visitor checked in successfully" if visitor else "Visitor not found"

# Function to check out a visitor
def check_out_visitor(db: Session, visitor_id: int):
    visitor = db.query(Visitor).filter(Visitor.id == visitor_id).first()
    if visitor:
        visitor.check_out = datetime.datetime.utcnow()
        db.commit()
    return visitor

# Function to authenticate a user
def authenticate(username: str, password: str):
    db = next(get_db())
    user = authenticate_user(db, username, password)
    if user:
        token = create_jwt_token(user.id)
        return token
    return None

# Streamlit app layout
st.set_page_config(page_title="Visitor Management System", layout="wide")

# Database initialization
if not os.path.exists("test.db"):
    engine.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, hashed_password TEXT, company_id INTEGER, is_superuser BOOLEAN DEFAULT FALSE)")
    engine.execute("CREATE TABLE visitors (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT, company_id INTEGER, pre_registered BOOLEAN DEFAULT FALSE, notified BOOLEAN DEFAULT FALSE, check_in DATETIME, check_out DATETIME, temperature FLOAT, health_status TEXT, face_image_path TEXT, visit_purpose TEXT, person_to_meet TEXT, department TEXT, company_name TEXT, visitor_location TEXT)")

menu = ["Home", "Pre-Register", "Check In", "Check Out", "Reports", "Admin"]
choice = st.sidebar.selectbox("Menu", menu)

token = st.session_state.get("auth_token")

if token:
    user_id = decode_jwt_token(token)
else:
    user_id = None

if user_id:
    db = next(get_db())
    user = db.query(User).filter(User.id == user_id).first()
    company_id = user.company_id if user else None

    if choice == "Home":
        st.title("Welcome to the Visitor Management System")

    elif choice == "Pre-Register":
        st.header("Pre-Register Visitor")
        name = st.text_input("Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        visit_purpose = st.selectbox("Visit Purpose", ["Meeting", "Interview", "Repair & Maintenance", "Other - Please explain"])
        if visit_purpose == "Other - Please explain":
            visit_purpose = st.text_input("Please explain")
        person_to_meet = st.text_input("Person to Meet")
        department = st.text_input("Department")
        company_name = st.text_input("Company Name")
        visitor_location = st.text_input("Visitor Location")
        if st.button("Pre-Register"):
            visitor = add_visitor(db, name, email, phone, company_id, visit_purpose, person_to_meet, department, company_name, visitor_location)
            send_sms(visitor.phone, f"Hello {visitor.name}, you have been pre-registered.")
            send_email(visitor.email, "Visitor Registration", f"Please register yourself using this link: http://localhost:8000/register/{visitor.id}")
            st.success(f"Visitor {visitor.name} pre-registered successfully")

    elif choice == "Check In":
        st.header("Visitor Check In")
        visitor_id = st.number_input("Visitor ID", min_value=1)
        temperature = st.number_input("Temperature", min_value=90, max_value=110)
        health_status = st.text_input("Health Status")
        if st.button("Capture Face"):
            face_image_path, frame = capture_face(visitor_id)
            if frame is not None:
                st.image(frame, caption='Captured Image', use_column_width=True)
                if st.button("Proceed with Check-In"):
                    visitor, message = check_in_visitor(db, visitor_id, temperature, health_status, face_image_path)
                    if visitor:
                        st.success(message)
                        st.write(f"Visitor {visitor.name} checked in successfully at {visitor.check_in}")
                    else:
                        st.error(message)
            else:
                st.error("Failed to capture image. Please try again.")
    
    elif choice == "Check Out":
        st.header("Visitor Check Out")
        visitor_id = st.number_input("Visitor ID", min_value=1)
        if st.button("Check Out"):
            visitor = check_out_visitor(db, visitor_id)
            if visitor:
                st.success(f"Visitor {visitor.name} checked out successfully at {visitor.check_out}")
            else:
                st.error("Visitor not found or already checked out")
    
    elif choice == "Reports":
        st.header("Visitor Reports")
        visitors = db.query(Visitor).filter(Visitor.company_id == company_id).all()
        if visitors:
            visitor_data = {
                "Name": [visitor.name for visitor in visitors],
                "Email": [visitor.email for visitor in visitors],
                "Phone": [visitor.phone for visitor in visitors],
                "Check-In Time": [visitor.check_in.strftime("%Y-%m-%d %H:%M:%S") if visitor.check_in else "-" for visitor in visitors],
                "Check-Out Time": [visitor.check_out.strftime("%Y-%m-%d %H:%M:%S") if visitor.check_out else "-" for visitor in visitors],
                "Visit Purpose": [visitor.visit_purpose for visitor in visitors],
                "Person to Meet": [visitor.person_to_meet for visitor in visitors],
                "Department": [visitor.department for visitor in visitors],
                "Company Name": [visitor.company_name for visitor in visitors],
                "Visitor Location": [visitor.visitor_location for visitor in visitors]
            }
            df = pd.DataFrame(visitor_data)
            st.dataframe(df)
        else:
            st.warning("No visitors found")

    elif choice == "Admin":
        st.header("Admin Panel")
        st.subheader("Create New User")
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        if st.button("Create User"):
            create_user(db, new_username, new_password, company_id)
            st.success(f"User '{new_username}' created successfully")

else:
    st.title("Visitor Management System")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        token = authenticate(username, password)
        if token:
            st.session_state.auth_token = token
            st.success("Logged in successfully!")
        else:
            st.error("Invalid username or password")

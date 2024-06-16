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
from streamlit_option_menu import option_menu

st.set_page_config(page_title="Visitor Management System", layout="wide")

def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Load custom CSS
load_css("styles.css")
    
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

# Function to generate a QR code
def generate_qr_code(data: str):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    return img

# Function to create a PDF badge
def create_pdf_badge(visitor):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    text = f"Visitor ID: {visitor.id}\nName: {visitor.name}\nVisit Purpose: {visitor.visit_purpose}\nPerson to Meet: {visitor.person_to_meet}"
    c.drawString(100, 700, text)
    
    qr_code_image = generate_qr_code(f"Visitor ID: {visitor.id}")
    qr_code_image.save("temp_qr_code.png")
    
    c.drawImage("temp_qr_code.png", 100, 600, width=100, height=100)
    if visitor.face_image_path:
        c.drawImage(visitor.face_image_path, 200, 600, width=100, height=100)
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# Function to show dashboard with widgets
def show_dashboard():
    st.header("Jay Shree Ram India Limited",divider=True)
    
    db = next(get_db())
    col1,col2,col3=st.columns(3)
    with col1:
        total_visitors = db.query(Visitor).count()
        st.metric("Total Visitors", total_visitors)
        checked_in_visitors = db.query(Visitor).filter(Visitor.check_in != None).count()
        st.metric("Checked-In Visitors", checked_in_visitors)
    with col2:
        checked_out_visitors = db.query(Visitor).filter(Visitor.check_out != None).count()
        st.metric("Checked-Out Visitors", checked_out_visitors)
        visitors_today = db.query(Visitor).filter(Visitor.check_in >= datetime.datetime.utcnow().date()).count()
        st.metric("Visitors Today", visitors_today)
    with col3:
        pre_registered_visitors = db.query(Visitor).filter(Visitor.pre_registered == True).count()
        notified_visitors = db.query(Visitor).filter(Visitor.notified == True).count()
        st.metric("Pre-Registered Visitors", pre_registered_visitors)
        st.metric("Notified Visitors", notified_visitors)
    
# Database initialization
if not os.path.exists("test.db"):
    engine.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, hashed_password TEXT, company_id INTEGER, is_superuser BOOLEAN DEFAULT FALSE)")
    engine.execute("CREATE TABLE visitors (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT, company_id INTEGER, pre_registered BOOLEAN DEFAULT FALSE, notified BOOLEAN DEFAULT FALSE, check_in DATETIME, check_out DATETIME, temperature FLOAT, health_status TEXT, face_image_path TEXT, visit_purpose TEXT, person_to_meet TEXT, department TEXT, company_name TEXT, visitor_location TEXT)")

# Login logic
if "auth_token" in st.session_state:
    token = st.session_state["auth_token"]
    user_id = decode_jwt_token(token)
else:
    token = None
    user_id = None

# Show menu only if logged in
if user_id:
    db = next(get_db())
    user = db.query(User).filter(User.id == user_id).first()
    company_id = user.company_id if user else None

    with st.sidebar:
        
        selected = option_menu(
        menu_title="Security : HelpDesk",  # required
        options=["Dashboard","Visitor HelpDesk","Admin","Logout"],  # required
        icons=["speedometer", "person-plus", "person-check", "person-x", "bar-chart", "gear"],  # required
        menu_icon="cast",  # optional
        default_index=0,  # optional
        styles={
            "container": {"padding": "0!important", "background-color": "#f7f9fc"},
            "icon": {"color": "#2e7bcf", "font-size": "25px"},
            "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#2e7bcf", "color": "white"},
        }
    )


    if selected == "Visitor HelpDesk":
        st.header("Visitor HelpDesk")
        
        sub_menu=st.sidebar.selectbox("Select Menu",["Pre-Register","Check In","Check Out","Reports"])
        
        if sub_menu=="Pre-Register":
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

        elif sub_menu == "Check In":
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
                        
                        # Generate and download badge
                        badge_pdf = create_pdf_badge(visitor)
                        st.download_button("Download Badge", badge_pdf, file_name=f"visitor_{visitor.id}_badge.pdf")
                    else:
                        st.error(message)
                else:
                    st.error("Failed to capture image. Please try again.")
    
        elif sub_menu == "Check Out":
                st.header("Visitor Check Out")
                visitor_id = st.number_input("Visitor ID", min_value=1)
                if st.button("Check Out"):
                    visitor = check_out_visitor(db, visitor_id)
                    if visitor:
                        st.success(f"Visitor {visitor.name} checked out successfully at {visitor.check_out}")
                    else:
                        st.error("Visitor not found")

        elif sub_menu == "Reports":
                st.header("Visitor Reports")
                visitors = db.query(Visitor).filter(Visitor.company_id == company_id).all()
                visitor_data = [(v.id, v.name, v.email, v.phone, v.check_in, v.check_out, v.visit_purpose, v.person_to_meet, v.department, v.company_name, v.visitor_location) for v in visitors]
                df = pd.DataFrame(visitor_data, columns=["ID", "Name", "Email", "Phone", "Check In", "Check Out", "Visit Purpose", "Person to Meet", "Department", "Company Name", "Visitor Location"])
                st.dataframe(df)

    elif selected == "Admin":
        st.header("Admin Panel")
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        if st.button("Create User"):
            create_user(db, new_username, new_password, company_id)
            st.success(f"User {new_username} created successfully")

    elif selected == "Dashboard":
        show_dashboard()
        
    elif selected == "Logout":
        st.session_state.pop("auth_token", None)
        st.experimental_rerun()

else:
    # Centered login form
    #st.markdown("<div class='centered-form'>", unsafe_allow_html=True)
    #st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.image('JSRVMS.png',use_column_width=True)
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        token = authenticate(username, password)
        if token:
            st.session_state["auth_token"] = token
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    import os
    if not os.path.exists("images"):
        os.makedirs("images")

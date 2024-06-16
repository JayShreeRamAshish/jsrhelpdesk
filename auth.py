from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models import User, SessionLocal
from datetime import datetime, timedelta
import jwt

# Initialize password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Secret key and token configuration
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Function to create a new user
def create_user(db: Session, username: str, password: str, company_id: int):
    hashed_password = pwd_context.hash(password)
    user = User(username=username, hashed_password=hashed_password, company_id=company_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# Function to authenticate a user
def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if user and pwd_context.verify(password, user.hashed_password):
        return user
    return None

# Function to create JWT token
def create_jwt_token(user_id: int):
    expiration = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data = {"sub": str(user_id), "exp": expiration}
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

# Function to decode JWT token
def decode_jwt_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        return user_id
    except jwt.ExpiredSignatureError:
        return None
    except jwt.DecodeError:
        return None
# Create superuser if not exists
def create_superuser():
    db = SessionLocal()
    superuser = db.query(User).filter(User.username == "super").first()
    if not superuser:
        create_user(db, "super", "JayShreeRam",1)
    db.close()

create_superuser()
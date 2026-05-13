from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt
from sqlalchemy import text
from config import db, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, pwd_context
from dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str = ""
    reset_pin: str = ""

class UserReset(BaseModel):
    email: str
    reset_pin: str
    new_password: str

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/register")
def register(user: UserRegister):
    hashed = get_password_hash(user.password)
    try:
        query = text("""
            INSERT INTO users (email, hashed_password, full_name, reset_pin)
            VALUES (:email, :password, :name, :pin)
        """)
        with db.engine.connect() as conn:
            conn.execute(query, {"email": user.email, "password": hashed, "name": user.full_name, "pin": user.reset_pin})
            conn.commit()
        return {"message": "User created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="User already exists or database error")

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    query = text("SELECT email, hashed_password FROM users WHERE email = :email")
    with db.engine.connect() as conn:
        res = conn.execute(query, {"email": form_data.username}).fetchone()
    
    if not res or not verify_password(form_data.password, res[1]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": res[0]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
def get_me(current_user: str = Depends(get_current_user)):
    query = text("SELECT email, full_name, created_at FROM users WHERE email = :email")
    with db.engine.connect() as conn:
        res = conn.execute(query, {"email": current_user}).fetchone()
    if not res:
        raise HTTPException(status_code=404, detail="User not found")
    return {"email": res[0], "full_name": res[1], "created_at": res[2]}

@router.post("/reset-password")
def reset_password(req: UserReset):
    query = text("SELECT email FROM users WHERE email = :email AND reset_pin = :pin")
    with db.engine.connect() as conn:
        res = conn.execute(query, {"email": req.email, "pin": req.reset_pin}).fetchone()
    if not res:
        raise HTTPException(status_code=400, detail="Invalid Email or PIN")
    
    new_hashed = get_password_hash(req.new_password)
    update_query = text("UPDATE users SET hashed_password = :hp WHERE email = :email")
    with db.engine.connect() as conn:
        conn.execute(update_query, {"hp": new_hashed, "email": req.email})
        conn.commit()
    return {"message": "Password reset successful"}

@router.put("/change-password")
def change_password(req: PasswordChange, current_user: str = Depends(get_current_user)):
    query = text("SELECT hashed_password FROM users WHERE email = :email")
    with db.engine.connect() as conn:
        res = conn.execute(query, {"email": current_user}).fetchone()

    if not res or not verify_password(req.old_password, res[0]):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    new_hashed = get_password_hash(req.new_password)
    update_query = text("UPDATE users SET hashed_password = :hp WHERE email = :email")
    with db.engine.connect() as conn:
        conn.execute(update_query, {"hp": new_hashed, "email": current_user})
        conn.commit()
    return {"message": "Password updated successfully"}

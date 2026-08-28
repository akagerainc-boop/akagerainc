"""Authentication: email/password + Google (Firebase) + profile management."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth_utils import hash_password, verify_password, create_token, get_current_user
from ratelimit import limiter

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _public_user(u: User) -> dict:
    return {
        "id": u.id, "name": u.name, "email": u.email, "role": u.role,
        "profile_picture": u.profile_picture, "phone": u.phone, "company": u.company,
        "country": u.country, "provider": u.provider, "email_verified": bool(u.email_verified),
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


def _auth_response(u: User) -> dict:
    return {"access_token": create_token({"sub": str(u.id), "role": u.role, "email": u.email}),
            "token_type": "bearer", "user": _public_user(u)}


class RegisterBody(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None
    company: str | None = None
    country: str | None = None


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class GoogleBody(BaseModel):
    email: EmailStr
    name: str | None = "User"
    profile_picture: str | None = None
    token: str | None = None


class ProfileBody(BaseModel):
    name: str | None = None
    phone: str | None = None
    company: str | None = None
    country: str | None = None
    profile_picture: str | None = None


class PasswordBody(BaseModel):
    current_password: str | None = None
    new_password: str


@router.post("/register", dependencies=[Depends(limiter("auth-register", 8, 300))])
def register(body: RegisterBody, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    user = User(name=body.name.strip(), email=body.email.lower(), password_hash=hash_password(body.password),
                phone=body.phone, company=body.company, country=body.country,
                role="customer", provider="password", is_active=True, last_login_at=datetime.utcnow())
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_response(user)


@router.post("/login", dependencies=[Depends(limiter("auth-login", 12, 300))])
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is disabled.")
    user.last_login_at = datetime.utcnow()
    db.commit()
    return _auth_response(user)


@router.post("/google", dependencies=[Depends(limiter("auth-google", 20, 300))])
def google_auth(body: GoogleBody, db: Session = Depends(get_db)):
    email = body.email.lower()
    user = db.query(User).filter(User.email == email).first()
    if user:
        if body.profile_picture:
            user.profile_picture = body.profile_picture
        if not user.google_id:
            user.google_id = email
        user.provider = user.provider or "google"
        user.last_login_at = datetime.utcnow()
    else:
        user = User(name=body.name or "User", email=email, google_id=email,
                    profile_picture=body.profile_picture, role="customer", provider="google",
                    email_verified=True, is_active=True, last_login_at=datetime.utcnow())
        db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_response(user)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _public_user(user)


@router.patch("/profile")
def update_profile(body: ProfileBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field in ("name", "phone", "company", "country", "profile_picture"):
        val = getattr(body, field)
        if val is not None:
            setattr(user, field, val)
    db.commit()
    db.refresh(user)
    return _public_user(user)


@router.post("/change-password")
def change_password(body: PasswordBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.password_hash and not verify_password(body.current_password or "", user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters.")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password updated."}


@router.delete("/account")
def delete_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(user)
    db.commit()
    return {"message": "Account deleted."}

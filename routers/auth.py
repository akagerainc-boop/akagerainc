"""Authentication: email/password + Google (Firebase) + email OTP + profile."""
import os
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from models import User, OtpCode
from auth_utils import hash_password, verify_password, create_token, decode_token, get_current_user
from ratelimit import limiter
from email_service import send_otp

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

OTP_TTL_MINUTES = int(os.getenv("OTP_TTL_MINUTES", "10"))
OTP_MAX_ATTEMPTS = 5
DEBUG = os.getenv("DEBUG", "False").lower() == "true"


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


# ==========================================================================
#  Email OTP  (Resend)
# ==========================================================================
_VALID_PURPOSES = {"login", "verify", "reset"}


class OtpRequestBody(BaseModel):
    email: EmailStr
    purpose: str = "login"


class OtpVerifyBody(BaseModel):
    email: EmailStr
    code: str
    purpose: str = "login"
    name: str | None = None


class OtpPasswordResetBody(BaseModel):
    reset_token: str
    new_password: str


def _gen_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


@router.post("/otp/request", dependencies=[Depends(limiter("otp-request", 6, 300))])
def otp_request(body: OtpRequestBody, db: Session = Depends(get_db)):
    email = body.email.lower()
    purpose = body.purpose if body.purpose in _VALID_PURPOSES else "login"

    user = db.query(User).filter(User.email == email).first()
    # For password reset we must not reveal whether the account exists.
    if purpose == "reset" and not user:
        return {"message": "If that email has an account, a code is on its way.", "sent": False}

    # invalidate previous unconsumed codes for this email+purpose
    db.query(OtpCode).filter(
        OtpCode.email == email, OtpCode.purpose == purpose, OtpCode.consumed == False  # noqa: E712
    ).update({"consumed": True})

    code = _gen_code()
    db.add(OtpCode(
        email=email, code_hash=hash_password(code), purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES),
    ))
    db.commit()

    ok, info = send_otp(email, code, purpose, OTP_TTL_MINUTES)
    resp = {"message": "We sent a 6-digit code to your email.", "sent": ok, "expires_in_minutes": OTP_TTL_MINUTES}
    if not ok:
        if DEBUG:
            # dev convenience — the real deployment must have DEBUG=False and a
            # verified Resend domain so codes are only ever delivered by email.
            resp["dev_code"] = code
            resp["email_error"] = info
            resp["message"] = "Email send failed — returning the code because DEBUG=True."
        else:
            raise HTTPException(status_code=502, detail=f"Could not send the verification email: {info}")
    return resp


def _consume_otp(db: Session, email: str, code: str, purpose: str) -> bool:
    row = (db.query(OtpCode)
           .filter(OtpCode.email == email, OtpCode.purpose == purpose, OtpCode.consumed == False)  # noqa: E712
           .order_by(OtpCode.id.desc()).first())
    if not row:
        return False
    if row.expires_at and row.expires_at < datetime.utcnow():
        row.consumed = True
        db.commit()
        return False
    row.attempts = (row.attempts or 0) + 1
    if row.attempts > OTP_MAX_ATTEMPTS:
        row.consumed = True
        db.commit()
        return False
    if not verify_password(code.strip(), row.code_hash):
        db.commit()
        return False
    row.consumed = True
    db.commit()
    return True


@router.post("/otp/verify", dependencies=[Depends(limiter("otp-verify", 15, 300))])
def otp_verify(body: OtpVerifyBody, db: Session = Depends(get_db)):
    email = body.email.lower()
    purpose = body.purpose if body.purpose in _VALID_PURPOSES else "login"

    if not _consume_otp(db, email, body.code, purpose):
        raise HTTPException(status_code=400, detail="Invalid or expired code. Request a new one.")

    user = db.query(User).filter(User.email == email).first()

    if purpose == "login":
        if not user:
            user = User(name=(body.name or email.split("@")[0]).strip() or "User", email=email,
                        role="customer", provider="otp", email_verified=True, is_active=True,
                        last_login_at=datetime.utcnow())
            db.add(user)
        else:
            user.email_verified = True
            user.last_login_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        if not user.is_active:
            raise HTTPException(status_code=403, detail="This account is disabled.")
        return _auth_response(user)

    if purpose == "verify":
        if user:
            user.email_verified = True
            db.commit()
        return {"message": "Email verified.", "verified": True}

    # purpose == "reset"
    if not user:
        raise HTTPException(status_code=404, detail="Account not found.")
    reset_token = create_token({"sub": str(user.id), "scope": "pwreset", "email": user.email}, expires_hours=1)
    return {"reset_token": reset_token, "message": "Code accepted. You can set a new password now."}


@router.post("/password/reset", dependencies=[Depends(limiter("pw-reset", 10, 300))])
def password_reset(body: OtpPasswordResetBody, db: Session = Depends(get_db)):
    data = decode_token(body.reset_token)
    if not data or data.get("scope") != "pwreset":
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    user = db.query(User).filter(User.id == int(data["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found.")
    user.password_hash = hash_password(body.new_password)
    user.email_verified = True
    db.commit()
    return _auth_response(user)

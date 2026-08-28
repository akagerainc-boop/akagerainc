import requests
import uuid
import os
import secrets
import string
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Query, Form, Request, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import get_db
import json
from typing import List, Optional
import stripe
from pydantic import BaseModel
import traceback
from pathlib import Path
from io import BytesIO
from reportlab.pdfgen import canvas

# Load environment variables from the backend folder regardless of the current working directory
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

# ==================== DATABASE SETUP (WORKING VERSION) ====================
from database import engine, get_db, Base, SessionLocal
from models import User, App, Service, Payment, License, ContactMessage, BusinessToken
from models import SiteContent, Order
import schemas
from utils import generate_license_key, generate_hex_license_key, slugify
from admin import admin_router
from routers import auth as auth_router
from routers import public as public_router
from routers import orders as orders_router
from routers import subscriptions as subscriptions_router
from routers import support as support_router
from routers import applications as applications_router
from payments.service import finalize_payment


def _safe_print(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


def initialize_database() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        _safe_print("[db] tables initialized")
    except Exception as exc:
        _safe_print(f"[db] initialization skipped: {exc}")


initialize_database()


def _bootstrap_admin_and_content() -> None:
    """Idempotently ensure the super-admin + default CMS content exist."""
    try:
        import seed as _seed
        db = SessionLocal()
        try:
            _seed.seed_site_content(db)
            _seed.seed_admin(db)
            _seed.seed_navigation(db)
        finally:
            db.close()
    except Exception as exc:
        print(f"⚠️ Admin/content bootstrap skipped: {exc}")


_bootstrap_admin_and_content()


def _resolve_order_ref(db: Session, order_ref, payment: Payment) -> None:
    if not order_ref:
        return
    order = db.query(Order).filter(Order.order_ref == order_ref).first()
    if order and order.user_id == payment.user_id:
        payment.order_id = order.id
        db.commit()

# Initialize FastAPI app
app = FastAPI(
    title="Akagera Inc API",
    description="Smart Mobile Solutions API",
    version="1.0.0"
)

# CORS middleware configuration
_default_origins = "https://akagerainc.store,https://akagerainc.onrender.com,https://akagera-frontend.onrender.com,http://localhost:3000,http://localhost:8000"
_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)


class CachedStaticFiles(StaticFiles):
    """StaticFiles that adds long-lived immutable caching for uploaded media."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        try:
            response.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
        except Exception:
            pass
        return response


app.mount("/uploads", CachedStaticFiles(directory="uploads"), name="uploads")

# Routers
app.include_router(admin_router)
app.include_router(auth_router.router)
app.include_router(public_router.router)
app.include_router(orders_router.router)
app.include_router(subscriptions_router.router)
app.include_router(support_router.router)
app.include_router(applications_router.router)


SITE_CONTENT = {
    "brand": {
        "name": "Akagera Inc",
        "tagline": "Building innovative software solutions for businesses and communities.",
        "primary_color": "#0B3C5D",
        "secondary_color": "#1a1a1a",
        "accent_color": "#F77F00",
    },
    "hero": {
        "title": "Building Innovative Software Solutions For Businesses And Communities.",
        "subtitle": "Akagera Inc develops mobile applications, websites, enterprise systems and digital solutions that help organizations grow.",
        "primary_cta": "Explore Products",
        "secondary_cta": "Request Software",
    },
    "business_categories": ["Restaurant", "School", "Hospital", "Hotel", "Shop", "Pharmacy"],
    "pricing": [
        {
            "name": "Starter",
            "price": "$250",
            "description": "For small businesses that need a clear online presence and a reliable launch plan.",
            "features": ["Corporate website", "Basic support", "Contact form", "Mobile friendly"],
        },
        {
            "name": "Professional",
            "price": "$850",
            "description": "For growing companies that need a stronger digital platform and custom workflows.",
            "features": ["Custom web app", "Marketplace setup", "Admin tools", "Priority support"],
        },
        {
            "name": "Enterprise",
            "price": "Custom",
            "description": "For large organizations that need private portals, advanced automation and dedicated support.",
            "features": ["Business portal", "Advanced security", "Dedicated delivery", "API integration"],
        },
    ],
    "services": [
        {
            "title": "Mobile Application Development",
            "description": "Android and iOS products built for reliable business growth.",
        },
        {
            "title": "Web Application Development",
            "description": "Secure portals, dashboards and SaaS platforms built for scale.",
        },
        {
            "title": "Custom Software Development",
            "description": "ERP, CRM, inventory and management systems tailored to your operations.",
        },
        {
            "title": "Cloud and Support Services",
            "description": "Hosting, deployment, maintenance and API integration for production systems.",
        },
    ],
    "portfolio": [
        {
            "name": "Akagera POS System",
            "client": "Retail client",
            "technology": "React, FastAPI, MySQL",
            "description": "Sales, inventory and reporting platform for day-to-day retail operations.",
        },
        {
            "name": "School Management Portal",
            "client": "Education client",
            "technology": "React, Node.js, PostgreSQL",
            "description": "Student, class and performance management portal for schools.",
        },
        {
            "name": "Business Service Dashboard",
            "client": "Operations client",
            "technology": "React, FastAPI, JWT",
            "description": "Private business dashboard for subscriptions, licenses and access tokens.",
        },
    ],
}


def get_default_pricing_content():
    return SITE_CONTENT["pricing"]


def get_pricing_content(db: Session):
    record = db.query(SiteContent).filter(SiteContent.content_key == "pricing").first()
    if record and isinstance(record.content_value, list):
        return record.content_value
    return get_default_pricing_content()


def ensure_default_site_content(db: Session):
    if not db.query(SiteContent).filter(SiteContent.content_key == "pricing").first():
        db.add(SiteContent(content_key="pricing", content_value=get_default_pricing_content()))
        db.commit()


startup_db = SessionLocal()
try:
    ensure_default_site_content(startup_db)
except Exception as exc:
    print(f"⚠️ Default site content initialization skipped: {exc}")
finally:
    startup_db.close()

def generate_business_access_token() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(10))


def serialize_business_token(token: BusinessToken) -> dict:
    return {
        "id": token.id,
        "business_name": token.business_name,
        "category": token.category,
        "token": token.token,
        "status": token.status,
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        "created_at": token.created_at.isoformat() if token.created_at else None,
    }


def create_purchase_receipt_file(db: Session, user_id: int, payment_id: int, service_id: int, license_key: str, portal_token: str | None = None) -> str | None:
    user = db.query(User).filter(User.id == user_id).first()
    service = db.query(Service).filter(Service.id == service_id).first()
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not user or not service or not payment:
        return None

    receipt_dir = Path("uploads/receipts")
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_filename = f"receipt_{payment_id}_{slugify(service.name)}.pdf"
    receipt_path = receipt_dir / receipt_filename

    content_lines = [
        "AKAGERA INC - PROOF OF PURCHASE",
        "=" * 40,
        f"Receipt ID: {payment.id}",
        f"Service: {service.name}",
        f"Service Type: {getattr(service, 'service_type', 'app_license')}",
        f"Amount Paid: {payment.amount}",
        f"Customer: {user.name} ({user.email})",
        f"License Credential: {license_key}",
    ]
    if portal_token:
        content_lines.append(f"Portal Token: {portal_token}")
    content_lines.extend([
        f"Status: {payment.status}",
        f"Issued: {payment.created_at.isoformat() if payment.created_at else datetime.utcnow().isoformat()}",
        "This receipt confirms the successful purchase of the selected service from Akagera Inc.",
    ])

    try:
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer)
        pdf.setTitle("Akagera Inc Proof of Purchase")
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, 770, "AKAGERA INC - PROOF OF PURCHASE")
        pdf.setFont("Helvetica", 11)
        y = 740
        for line in content_lines:
            if y < 50:
                pdf.showPage()
                y = 770
                pdf.setFont("Helvetica", 11)
            pdf.drawString(50, y, line)
            y -= 14
        pdf.save()
        buffer.seek(0)
        receipt_path.write_bytes(buffer.getvalue())
        return str(receipt_path)
    except Exception as exc:
        print(f"⚠️ Failed to write receipt file: {exc}")
        return None


def create_business_token_for_purchase(db: Session, user_id: int, service_id: int, payment_id: int):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service or not getattr(service, "grants_business_portal_access", False):
        return None

    business_name = (service.portal_business_name or "Business Portal").strip()
    category = (service.portal_category or "General").strip()
    duration_days = service.portal_access_duration_days or 365
    token_value = generate_business_access_token()
    existing_token = db.query(BusinessToken).filter(BusinessToken.token == token_value).first()
    retry_count = 0
    while existing_token and retry_count < 5:
        token_value = generate_business_access_token()
        existing_token = db.query(BusinessToken).filter(BusinessToken.token == token_value).first()
        retry_count += 1

    business_token = BusinessToken(
        user_id=user_id,
        service_id=service_id,
        payment_id=payment_id,
        business_name=business_name,
        category=category,
        token=token_value,
        expires_at=datetime.utcnow() + timedelta(days=duration_days),
        status="active",
    )
    db.add(business_token)
    db.commit()
    db.refresh(business_token)
    return business_token

# ITEC/AKAGERA INC PAYMENT ENDPOINTS
ITEC_MOMO_API_URL = "https://pay.itecpay.rw/api2/pay"
ITEC_CARD_API_URL = "https://pay.itecpay.rw/api/pay/apis/pesapal/generatecode"
ITEC_VERIFY_API_URL = "https://pay.itecpay.rw/api2/verify"
ITEC_API_KEY = os.getenv("ITEC_API_KEY", "")  # Set your Akagera Inc ITEC API key in env

# USD to RWF conversion
USD_TO_RWF = 1466.52


def normalize_payment_status(status_value: Optional[str]) -> str:
    if not status_value:
        return "pending"
    status_text = str(status_value).strip().lower()
    if status_text in {"success", "successful", "succeeded", "completed", "complete", "paid", "done", "200"}:
        return "completed"
    if status_text in {"pending", "processing", "in_progress", "waiting", "initiated"}:
        return "pending"
    return status_text

# Initiate MoMo Payment (ITEC)
# Add these Pydantic models at the top of your file (after other models)

class MomoPaymentRequest(BaseModel):
    amount: float
    service_id: int
    currency: str = "USD"
    user_id: int
    phone_number: str
    order_ref: Optional[str] = None

# Replace your existing initiate-momo endpoint with this
@app.post("/api/payments/initiate-momo")
async def initiate_momo_payment(
    request: MomoPaymentRequest,
    db: Session = Depends(get_db)
):
    if not ITEC_API_KEY:
        raise HTTPException(status_code=500, detail="ITEC API key not configured.")

    user = db.query(User).filter(User.id == request.user_id).first()
    service = db.query(Service).filter(Service.id == request.service_id).first()
    
    if not user or not service:
        raise HTTPException(status_code=404, detail="User or service not found.")
    
    amount_rwf = int(round(request.amount * USD_TO_RWF))
    req_ref = str(uuid.uuid4())
    
    payload = {
        "amount": amount_rwf,
        "phone": request.phone_number,
        "key": ITEC_API_KEY,
        "req_ref": req_ref,
        "note": f"AkageraInc Service {request.service_id}",
        "message": f"Payment for {service.name} by {user.email}"
    }
    
    try:
        print(f"Sending MoMo payment request: {payload}")
        resp = requests.post(ITEC_MOMO_API_URL, json=payload, timeout=30)
        print(f"MoMo API Response Status: {resp.status_code}")
        print(f"MoMo API Response Body: {resp.text}")
        
        if resp.status_code == 200:
            data = resp.json()
            status_code = data.get("status")
            
            if status_code == 200:
                # Save payment as pending
                db_payment = Payment(
                    user_id=request.user_id,
                    amount=request.amount,
                    currency=request.currency,
                    service_id=request.service_id,
                    status="pending",
                    payment_method="momo",
                    stripe_transaction_id=req_ref
                )
                db.add(db_payment)
                db.commit()
                db.refresh(db_payment)
                _resolve_order_ref(db, request.order_ref, db_payment)

                return {
                    "success": True,
                    "req_ref": req_ref,
                    "amount_rwf": amount_rwf,
                    "momo_reference": data.get("data", {}).get("transaction_id") or req_ref,
                    "message": "MoMo payment initiated. Awaiting confirmation."
                }
            else:
                error_msg = data.get("data", {}).get("message", "MoMo payment failed.")
                return {"success": False, "error": error_msg}
        else:
            return {"success": False, "error": f"ITEC API returned status {resp.status_code}: {resp.text}"}
            
    except requests.exceptions.Timeout:
        print("MoMo payment request timed out")
        return {"success": False, "error": "Request timed out. Please try again."}
    except Exception as e:
        print(f"MoMo payment error: {str(e)}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# Replace your existing initiate-card endpoint with this

    
# Verify Payment Status (ITEC)
@app.post("/api/payments/status")
async def verify_payment_status(
    req_ref: str = Query(...),
    db: Session = Depends(get_db)
):
    if not ITEC_API_KEY:
        raise HTTPException(status_code=500, detail="ITEC API key not configured.")
    payload = {
        "action": "status_check",
        "req_ref": req_ref,
        "key": ITEC_API_KEY
    }
    try:
        resp = requests.post(ITEC_VERIFY_API_URL, json=payload, timeout=15)
        data = resp.json()
        status = data.get("data", {}).get("status") or data.get("status")
        normalized_status = normalize_payment_status(status)

        # Update payment status in DB
        db_payment = db.query(Payment).filter(Payment.stripe_transaction_id == req_ref).first()
        if db_payment:
            db_payment.status = normalized_status
            db_payment.transaction_id = req_ref
            db_payment.provider = db_payment.provider or "itec"
            db.commit()
            if normalized_status == "completed":
                finalize_payment(db, db_payment)
        return {"success": True, "status": normalized_status}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Add these new Pydantic models

class CardPaymentCallback(BaseModel):
    PCODE: str
    amount: str
    transID: str

# Add this endpoint for card payment
# Update your CardPaymentRequest model
class CardPaymentRequest(BaseModel):
    amount: float
    service_id: int
    currency: str = "USD"
    user_id: int
    email: str

@app.post("/api/payments/initiate-card")
async def initiate_card_payment(
    request: CardPaymentRequest,
    db: Session = Depends(get_db)
):
    """Initiate card payment with ITEC API"""
    if not ITEC_API_KEY:
        raise HTTPException(status_code=500, detail="ITEC API key not configured.")
    
    # Validate user
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate service
    service = db.query(Service).filter(Service.id == request.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Convert USD to RWF
    amount_rwf = int(round(request.amount * USD_TO_RWF))
    
    # Prepare payload for ITEC API - ONLY amount, email, and key
    payload = {
        "amount": amount_rwf,
        "email": request.email,
        "key": ITEC_API_KEY  # Make sure this is your CARD API key, not MOMO key
    }
    
    print(f"Card payment request - Amount RWF: {amount_rwf}, Email: {request.email}")
    print(f"Payload being sent: {payload}")
    
    try:
        # Call ITEC card payment API
        resp = requests.post(
            ITEC_CARD_API_URL,  # This should be https://pay.itecpay.rw/api/pay/apis/pesapal/generatecode
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"ITEC Response Status: {resp.status_code}")
        print(f"ITEC Response Body: {resp.text}")
        
        if resp.status_code == 200:
            data = resp.json()
            
            # Check if we got a valid PCODE and link
            if data.get("status") == 200 and data.get("link"):
                # Save payment to database
                db_payment = Payment(
                    user_id=request.user_id,
                    amount=request.amount,
                    currency=request.currency,
                    service_id=request.service_id,
                    status="pending",
                    payment_method="card",
                    stripe_transaction_id=data.get("PCODE")
                )
                db.add(db_payment)
                db.commit()
                db.refresh(db_payment)
                
                return {
                    "success": True,
                    "payment_url": data["link"],
                    "payment_id": data.get("PCODE"),
                    "amount_rwf": amount_rwf,
                    "valid_until": data.get("valid_until"),
                    "message": "Card payment initiated successfully"
                }
            else:
                error_msg = data.get("message", "Card payment initiation failed")
                return {"success": False, "error": error_msg}
        else:
            return {"success": False, "error": f"ITEC API error: {resp.status_code} - {resp.text}"}
            
    except requests.exceptions.Timeout:
        print("Card payment request timed out")
        return {"success": False, "error": "Request timed out. Please try again."}
    except Exception as e:
        print(f"Card payment error: {str(e)}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# Add callback endpoint for ITEC to notify payment status
@app.post("/api/payments/card-callback")
async def handle_card_callback(
    request: CardPaymentCallback,
    db: Session = Depends(get_db)
):
    """Handle ITEC card payment callback"""
    try:
        print(f"Received card callback: PCODE={request.PCODE}, transID={request.transID}, amount={request.amount}")
        
        # Find payment by transaction ID
        payment = db.query(Payment).filter(
            Payment.stripe_transaction_id == request.PCODE
        ).first()
        
        if not payment:
            print(f"Payment not found for PCODE: {request.PCODE}")
            return {"status": "error", "message": "Payment not found"}
        
        # Update payment status to completed
        payment.status = "completed"
        payment.transaction_id = request.transID
        payment.provider = payment.provider or "itec"
        db.commit()
        finalize_payment(db, payment)
        return {"status": "success", "message": "Payment callback processed"}
        
    except Exception as e:
        print(f"Callback error: {str(e)}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

# Add endpoint to check payment status
@app.get("/api/payments/card-status/{payment_id}")
async def check_card_payment_status(
    payment_id: str,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Check status of a card payment"""
    try:
        payment = db.query(Payment).filter(
            Payment.stripe_transaction_id == payment_id,
            Payment.user_id == user_id
        ).first()
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        return {
            "status": payment.status,
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "created_at": payment.created_at.isoformat() if payment.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Status check error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== HEALTH CHECK ====================
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Akagera Inc API"
    }

# ==================== APPS (WORKING DIRECT CONNECTION) ====================
@app.get("/api/apps", tags=["Apps"])
async def list_apps(db: Session = Depends(get_db)):
    """Get all available apps"""
    try:
        apps_data = db.query(App).order_by(App.id.asc()).all()

        result = []
        for app_data in apps_data:
            features = app_data.features
            if features and isinstance(features, str):
                try:
                    features = json.loads(features)
                except:
                    features = []
            elif not features:
                features = []
            
            installation_steps = app_data.installation_steps
            if installation_steps and isinstance(installation_steps, str):
                try:
                    installation_steps = json.loads(installation_steps)
                except:
                    installation_steps = []
            elif not installation_steps:
                installation_steps = []
            
            result.append({
                "id": app_data.id,
                "name": app_data.name,
                "description": app_data.description,
                "short_description": app_data.short_description,
                "requires_license": app_data.requires_license or False,
                "features": features,
                "how_it_works": app_data.how_it_works,
                "installation_steps": installation_steps,
                "download_url": app_data.download_url,
                "app_icon": app_data.app_icon,
                "app_logo": app_data.app_logo,
                "app_image": app_data.app_image,
                "created_at": app_data.created_at.isoformat() if app_data.created_at else None,
                "updated_at": app_data.updated_at.isoformat() if app_data.updated_at else None
            })
        
        print(f"✅ Returning {len(result)} apps")
        return result
        
    except Exception as e:
        print(f"❌ Error in /api/apps: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/apps/{app_id}", tags=["Apps"])
async def get_app(app_id: int, db: Session = Depends(get_db)):
    """Get app details by ID"""
    try:
        app_data = db.query(App).filter(App.id == app_id).first()

        if not app_data:
            raise HTTPException(status_code=404, detail="App not found")

        features = app_data.features
        if features and isinstance(features, str):
            try:
                features = json.loads(features)
            except:
                features = []
        elif not features:
            features = []

        installation_steps = app_data.installation_steps
        if installation_steps and isinstance(installation_steps, str):
            try:
                installation_steps = json.loads(installation_steps)
            except:
                installation_steps = []
        elif not installation_steps:
            installation_steps = []
        
        return {
            "id": app_data.id,
            "name": app_data.name,
            "description": app_data.description,
            "short_description": app_data.short_description,
            "requires_license": app_data.requires_license or False,
            "features": features,
            "how_it_works": app_data.how_it_works,
            "installation_steps": installation_steps,
            "download_url": app_data.download_url,
            "app_icon": app_data.app_icon,
            "app_logo": app_data.app_logo,
            "app_image": app_data.app_image,
            "created_at": app_data.created_at.isoformat() if app_data.created_at else None,
            "updated_at": app_data.updated_at.isoformat() if app_data.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in /api/apps/{app_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/apps/{app_id}/access", tags=["Apps"])
async def get_app_access(app_id: int, user_id: int = Query(None), db: Session = Depends(get_db)):
    """Check whether a user can access an app download or license-protected content."""
    app_data = db.query(App).filter(App.id == app_id).first()
    if not app_data:
        raise HTTPException(status_code=404, detail="App not found")

    has_access = True
    if app_data.requires_license:
        if user_id is None:
            has_access = False
        else:
            license = (
                db.query(License)
                .filter(
                    License.user_id == user_id,
                    License.app_id == app_id,
                    License.is_active == True,
                )
                .order_by(License.id.desc())
                .first()
            )
            if not license:
                has_access = False
            elif license.expires_at and license.expires_at < datetime.utcnow():
                has_access = False

    return {
        "app_id": app_id,
        "requires_license": bool(app_data.requires_license),
        "has_access": has_access,
        "download_url": app_data.download_url,
        "message": "Sign in with Google and complete payment to access this app." if app_data.requires_license and not has_access else "Access granted.",
    }

# ==================== USERS (ORIGINAL SQLALCHEMY VERSION) ====================
@app.post("/api/auth/register", response_model=schemas.UserResponse, tags=["Authentication"])
async def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    db_user = User(
        name=user_data.name,
        email=user_data.email,
        google_id=user_data.google_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/api/auth/google", tags=["Authentication"])
async def google_auth(request: dict, db: Session = Depends(get_db)):
    """Google OAuth authentication"""
    try:
        name = request.get("name", "User")
        email = request.get("email")
        profile_picture = request.get("profile_picture")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )
        
        existing_user = db.query(User).filter(User.email == email).first()
        
        if existing_user:
            db_user = existing_user
            if profile_picture:
                db_user.profile_picture = profile_picture
            db.commit()
        else:
            db_user = User(
                name=name,
                email=email,
                profile_picture=profile_picture,
                google_id=email
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
        
        access_token = f"token_{db_user.id}_{datetime.utcnow().timestamp()}"
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": db_user.id,
                "name": db_user.name,
                "email": db_user.email,
                "profile_picture": db_user.profile_picture,
                "created_at": db_user.created_at.isoformat() if db_user.created_at else None
            }
        }
    except Exception as e:
        print(f"Google auth error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )

@app.get("/api/users/{user_id}", response_model=schemas.UserResponse, tags=["Users"])
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/api/users/email/{email}", response_model=schemas.UserResponse, tags=["Users"])
async def get_user_by_email(email: str, db: Session = Depends(get_db)):
    """Get user by email"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ==================== SERVICES (SQLALCHEMY VERSION) ====================
@app.get("/api/services", response_model=list[schemas.ServiceResponse], tags=["Services"])
async def list_services(db: Session = Depends(get_db)):
    """Get all available services"""
    services = db.query(Service).all()
    return services

@app.get("/api/services/{service_id}", response_model=schemas.ServiceResponse, tags=["Services"])
async def get_service(service_id: int, db: Session = Depends(get_db)):
    """Get service details by ID"""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

# ==================== PAYMENTS ====================
class PaymentIntentRequest(BaseModel):
    amount: float
    service_id: int
    currency: str = "usd"


@app.post("/api/services/{service_id}/activate-free", tags=["Services"])
async def activate_free_service(service_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    service = db.query(Service).filter(Service.id == service_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    if float(service.price or 0) > 0:
        raise HTTPException(status_code=400, detail="This service is not free")

    db_payment = Payment(
        user_id=user_id,
        amount=0,
        currency="USD",
        service_id=service_id,
        status="completed",
        payment_method="free",
        provider="free",
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)

    result = finalize_payment(db, db_payment)
    return {
        "success": True,
        "status": "completed",
        "message": "Free service access granted successfully",
        "token": result.get("business_token"),
        "license_key": result.get("license_key"),
        "order_ref": result.get("order_ref"),
        "service_id": service_id,
    }


class MomoPaymentRequest(BaseModel):
    amount: float
    service_id: int
    currency: str = "usd"
    phone_number: str


def get_usd_to_rwf_rate() -> float:
    # Fixed conversion rate: 1 USD = 1,462 RWF
    return 1462.0


@app.post("/api/payments/create-intent")
async def create_payment_intent(
    request: PaymentIntentRequest,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    
    stripe_secret = os.getenv("STRIPE_SECRET_KEY")

    # ================= VALIDATE STRIPE CONFIG =================
    if not stripe_secret or stripe_secret.startswith("sk_test_your"):
        raise HTTPException(
            status_code=500,
            detail="Stripe secret key not configured properly in .env"
        )

    stripe.api_key = stripe_secret

    try:
        # ================= VALIDATE USER =================
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # ================= VALIDATE AMOUNT =================
        if request.amount is None or request.amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid amount")

        # SAFE conversion to cents
        amount_in_cents = int(float(request.amount) * 100)

        # ================= CREATE STRIPE INTENT =================
        intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency=request.currency.lower(),
            payment_method_types=["card"],
            metadata={
                "user_id": str(user_id),
                "service_id": str(request.service_id),
            }
        )

        # ================= SAVE PAYMENT =================
        db_payment = Payment(
            user_id=user_id,
            amount=request.amount,
            currency=request.currency,
            service_id=request.service_id,
            status="pending",
            stripe_transaction_id=intent.id
        )

        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)

        # ================= RESPONSE =================
        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id,
            "amount": request.amount,
            "currency": request.currency
        }

    except stripe.error.CardError as e:
        print("💳 Stripe Card Error:", str(e))
        raise HTTPException(status_code=400, detail=str(e))

    except stripe.error.StripeError as e:
        print("🔥 Stripe Error:", str(e))
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        print("💥 Payment Intent Error:")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Internal payment error: {str(e)}"
        )

@app.post("/api/payments/create-momo-charge")
async def create_momo_charge(
    request: MomoPaymentRequest,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    momo_api_url = os.getenv("MOMO_API_URL")
    momo_api_key = os.getenv("MOMO_API_KEY")
    momo_receiver = os.getenv("MOMO_RECEIVER_NUMBER", "0795226123")

    if not momo_api_url or not momo_api_key:
        raise HTTPException(
            status_code=500,
            detail="MoMo payment processing is not configured. Set MOMO_API_URL and MOMO_API_KEY in environment."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    service = db.query(Service).filter(Service.id == request.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    if request.amount is None or request.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    if not request.phone_number or not request.phone_number.strip():
        raise HTTPException(status_code=400, detail="Phone number is required for MoMo payment")

    exchange_rate = get_usd_to_rwf_rate()
    amount_rwf = int(round(float(request.amount) * exchange_rate))

    payment_payload = {
        "recipient_number": momo_receiver,
        "payer_number": request.phone_number.strip(),
        "amount": amount_rwf,
        "currency": "RWF",
        "description": f"Payment for {service.name} by {user.email}",
        "metadata": {
            "user_id": str(user_id),
            "service_id": str(request.service_id),
            "source": "MoMo"
        }
    }

    headers = {
        "Authorization": f"Bearer {momo_api_key}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(momo_api_url, json=payment_payload, headers=headers, timeout=15)
        response.raise_for_status()
        provider_data = response.json() if response.headers.get("Content-Type", "").startswith("application/json") else {}
        provider_reference = provider_data.get("transaction_id") or provider_data.get("reference") or provider_data.get("id") or ""

        db_payment = Payment(
            user_id=user_id,
            amount=request.amount,
            currency=request.currency,
            service_id=request.service_id,
            status="pending",
            stripe_transaction_id=f"momo:{provider_reference}" if provider_reference else "momo"
        )
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)

        return {
            "status": "pending",
            "amount_usd": request.amount,
            "amount_rwf": amount_rwf,
            "currency": request.currency,
            "momo_number": momo_receiver,
            "reference": provider_reference,
            "message": f"MoMo payment requested for RWF {amount_rwf}. Please complete payment to {momo_receiver}."
        }

    except requests.RequestException as e:
        print(f"MoMo payment request failed: {str(e)}")
        raise HTTPException(status_code=502, detail="Failed to create MoMo payment request. Please try again later.")

@app.post("/api/payments/webhook", tags=["Payments"])
async def handle_stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events"""
    stripe_secret = os.getenv("STRIPE_SECRET_KEY")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    if not stripe_secret or not webhook_secret:
        raise HTTPException(status_code=400, detail="Stripe webhook not configured")
    
    stripe.api_key = stripe_secret
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        print(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        print(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        
        payment = db.query(Payment).filter(
            Payment.stripe_transaction_id == payment_intent["id"]
        ).first()
        
        if payment:
            payment.status = "completed"
            payment.provider = payment.provider or "stripe"
            db.commit()
            finalize_payment(db, payment)

    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        
        payment = db.query(Payment).filter(
            Payment.stripe_transaction_id == payment_intent["id"]
        ).first()
        
        if payment:
            payment.status = "failed"
            db.commit()
            print(f"Payment {payment.id} marked as failed")
    
    return {"status": "success", "type": event["type"]}

# ==================== PAYPAL PAYMENT ENDPOINTS ====================
from paypal_service import paypal_service

@app.post("/api/payments/paypal/create-order", tags=["Payments"])
async def create_paypal_order(
    request: PaymentIntentRequest,
    user_id: int = Query(...),
    order_ref: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Create a PayPal order
    Returns PayPal order ID and approval link for client
    """
    try:
        # Validate user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate amount
        if request.amount is None or request.amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid amount")
        
        # Validate service
        service = db.query(Service).filter(Service.id == request.service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # Get frontend URL from environment
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        
        # Create PayPal order
        success, paypal_response = paypal_service.create_order(
            amount=str(round(request.amount, 2)),
            currency=request.currency.upper(),
            reference_id=f"order-{user_id}-{datetime.utcnow().timestamp()}",
            description=f"Payment for {service.name}",
            return_url=f"{frontend_url}/payment-success",
            cancel_url=f"{frontend_url}/payment-cancel"
        )
        
        if not success:
            raise HTTPException(status_code=502, detail=paypal_response.get("error", "Failed to create PayPal order"))
        
        paypal_order_id = paypal_response.get("id")
        approval_link = None
        
        # Find PayPal approval link
        for link in paypal_response.get("links", []):
            if link.get("rel") == "approve":
                approval_link = link.get("href")
                break
        
        if not approval_link:
            raise HTTPException(status_code=502, detail="No approval link in PayPal response")
        
        # Save payment to database
        db_payment = Payment(
            user_id=user_id,
            amount=request.amount,
            currency=request.currency,
            service_id=request.service_id,
            status="pending",
            payment_method="paypal",
            paypal_order_id=paypal_order_id
        )
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)
        _resolve_order_ref(db, order_ref, db_payment)

        return {
            "success": True,
            "paypal_order_id": paypal_order_id,
            "approval_url": approval_link,
            "status": "pending",
            "amount": request.amount,
            "currency": request.currency
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"PayPal order creation error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/api/payments/paypal/capture-order", tags=["Payments"])
async def capture_paypal_order(
    paypal_order_id: str = Query(...),
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """
    Capture (complete) a PayPal order after user approval
    Generates license if service requires it
    """
    try:
        # Validate user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Find payment by PayPal order ID
        payment = db.query(Payment).filter(
            Payment.paypal_order_id == paypal_order_id,
            Payment.user_id == user_id
        ).first()
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Capture PayPal order
        success, paypal_response = paypal_service.capture_order(paypal_order_id)
        
        if not success:
            payment.status = "failed"
            db.commit()
            raise HTTPException(status_code=502, detail=paypal_response.get("error", "Failed to capture PayPal order"))
        
        # Check if capture was successful
        status = paypal_response.get("status", "").upper()
        if status != "COMPLETED":
            payment.status = "failed"
            db.commit()
            raise HTTPException(status_code=402, detail=f"PayPal order not completed. Status: {status}")
        
        # Update payment status
        payment.status = "completed"
        payment.provider = payment.provider or "paypal"
        db.commit()
        db.refresh(payment)

        result = finalize_payment(db, payment)

        return {
            "success": True,
            "status": "completed",
            "payment_id": payment.id,
            "order_ref": result.get("order_ref"),
            "license_key": result.get("license_key"),
            "business_token": result.get("business_token"),
            "message": "Payment completed successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"PayPal order capture error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/api/payments/paypal/details/{paypal_order_id}", tags=["Payments"])
async def get_paypal_order_details(
    paypal_order_id: str,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Get details of a PayPal order"""
    try:
        # Verify payment exists for user
        payment = db.query(Payment).filter(
            Payment.paypal_order_id == paypal_order_id,
            Payment.user_id == user_id
        ).first()
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Get order details from PayPal
        success, paypal_response = paypal_service.get_order_details(paypal_order_id)
        
        if not success:
            raise HTTPException(status_code=502, detail=paypal_response.get("error", "Failed to get PayPal order details"))
        
        return {
            "success": True,
            "paypal_order": paypal_response,
            "payment_status": payment.status
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"PayPal order details error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/api/payments/user/{user_id}", response_model=list[schemas.PaymentResponse], tags=["Payments"])
async def get_user_payments(user_id: int, db: Session = Depends(get_db)):
    """Get all payments for a user"""
    payments = db.query(Payment).filter(Payment.user_id == user_id).all()
    return payments

@app.get("/api/payments/{payment_id}/receipt", tags=["Payments"])
async def download_payment_receipt(payment_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.user_id != user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this receipt")

    receipt_dir = Path("uploads/receipts")
    matches = sorted(receipt_dir.glob(f"receipt_{payment_id}*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Receipt not found")

    receipt_path = matches[0]
    return FileResponse(receipt_path, media_type="application/pdf", filename=receipt_path.name)

# ==================== LICENSES ====================
@app.get("/api/licenses/user/{user_id}", response_model=list[schemas.LicenseResponse], tags=["Licenses"])
async def get_user_licenses(user_id: int, db: Session = Depends(get_db)):
    """Get all licenses for a user"""
    licenses = db.query(License).filter(License.user_id == user_id).all()
    return licenses

@app.get("/api/licenses/verify/{license_key}", response_model=schemas.LicenseResponse, tags=["Licenses"])
async def verify_license(license_key: str, db: Session = Depends(get_db)):
    """Verify a license key"""
    license = db.query(License).filter(License.license_key == license_key).first()
    if not license:
        raise HTTPException(status_code=404, detail="License not found")
    
    if not license.is_active:
        raise HTTPException(status_code=400, detail="License is not active")
    
    if license.expires_at and license.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="License has expired")
    
    return license

@app.post("/api/licenses/generate", response_model=schemas.LicenseKeyResponse, tags=["Licenses"])
async def generate_license(
    user_id: int,
    service_id: int,
    db: Session = Depends(get_db)
):
    """Generate a new license key"""
    license_key = generate_license_key()
    expires_at = datetime.utcnow() + timedelta(days=365)
    
    db_license = License(
        user_id=user_id,
        license_key=license_key,
        service_id=service_id,
        is_active=True,
        expires_at=expires_at
    )
    db.add(db_license)
    db.commit()
    db.refresh(db_license)
    
    return schemas.LicenseKeyResponse(
        license_key=license_key,
        created_at=db_license.created_at,
        expires_at=expires_at,
        message="⚠️ Save this license key securely. You will need it later."
    )

# ==================== STATS ====================
@app.get("/api/stats", response_model=schemas.StatsResponse, tags=["Stats"])
async def get_stats(db: Session = Depends(get_db)):
    """Get application statistics"""
    total_users = db.query(User).count()
    total_payments = db.query(Payment).filter(Payment.status == "completed").count()
    total_apps = db.query(App).count()
    total_revenue = db.query(Payment.amount).filter(Payment.status == "completed").scalar() or 0
    
    return schemas.StatsResponse(
        total_users=total_users,
        total_payments=total_payments,
        total_apps=total_apps,
        total_revenue=total_revenue
    )


@app.get("/api/site/content", tags=["Public Site"])
async def get_site_content(db: Session = Depends(get_db)):
    apps = db.query(App).order_by(App.id.desc()).limit(6).all()
    services = db.query(Service).order_by(Service.id.asc()).all()
    portfolio = SITE_CONTENT["portfolio"]

    return {
        **SITE_CONTENT,
        "pricing": get_pricing_content(db),
        "apps": [
            {
                "id": app.id,
                "name": app.name,
                "short_description": app.short_description,
                "description": app.description,
                "requires_license": app.requires_license,
                "download_url": app.download_url,
                "app_logo": app.app_logo,
                "app_image": app.app_image,
                "features": app.features or [],
            }
            for app in apps
        ],
        "services": [
            {
                "id": service.id,
                "name": service.name,
                "description": service.description,
                "price": str(service.price),
                "icon": service.icon,
                "image_url": service.image_url,
            }
            for service in services
        ],
        "portfolio": portfolio,
    }


@app.post("/api/contact", response_model=schemas.ContactMessageResponse, tags=["Public Site"])
async def submit_contact_message(payload: schemas.ContactMessageCreate, db: Session = Depends(get_db)):
    message = ContactMessage(
        name=payload.name.strip(),
        email=payload.email,
        phone=payload.phone.strip() if payload.phone else None,
        service_required=payload.service_required.strip() if payload.service_required else None,
        message=payload.message.strip(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@app.get("/api/business/categories", tags=["Business Portal"])
async def get_business_categories():
    return {"categories": SITE_CONTENT["business_categories"]}


@app.get("/api/business/tokens/user/{user_id}", tags=["Business Portal"])
async def get_user_business_tokens(user_id: int, db: Session = Depends(get_db)):
    tokens = (
        db.query(BusinessToken)
        .filter(BusinessToken.user_id == user_id)
        .order_by(BusinessToken.created_at.desc())
        .all()
    )
    return {
        "success": True,
        "tokens": [serialize_business_token(token) for token in tokens],
    }


@app.post("/api/business/tokens", response_model=schemas.BusinessTokenResponse, tags=["Business Portal"])
async def create_business_token(
    payload: schemas.BusinessTokenCreate,
    admin_password: str = Query(...),
    db: Session = Depends(get_db),
):
    if admin_password != os.getenv("ADMIN_PASSWORD", "Admin@Akagera2024!"):
        raise HTTPException(status_code=401, detail="Invalid admin password")

    token_value = generate_business_access_token()
    existing_token = db.query(BusinessToken).filter(BusinessToken.token == token_value).first()
    retry_count = 0
    while existing_token and retry_count < 5:
        token_value = generate_business_access_token()
        existing_token = db.query(BusinessToken).filter(BusinessToken.token == token_value).first()
        retry_count += 1

    business_token = BusinessToken(
        business_name=payload.business_name.strip(),
        category=payload.category.strip(),
        token=token_value,
        expires_at=payload.expires_at or (datetime.utcnow() + timedelta(days=365)),
    )
    db.add(business_token)
    db.commit()
    db.refresh(business_token)
    return business_token


@app.post("/api/business/login", tags=["Business Portal"])
async def business_login(payload: schemas.BusinessLoginRequest, db: Session = Depends(get_db)):
    business_token = (
        db.query(BusinessToken)
        .filter(
            BusinessToken.business_name == payload.business_name.strip(),
            BusinessToken.category == payload.category.strip(),
            BusinessToken.token == payload.token.strip().upper(),
        )
        .first()
    )

    if not business_token:
        raise HTTPException(status_code=401, detail="Invalid business credentials")

    if business_token.status != "active":
        raise HTTPException(status_code=403, detail="Business access is inactive")

    if business_token.expires_at and business_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Business access token has expired")

    return {
        "success": True,
        "access_token": f"business_{business_token.id}_{int(datetime.utcnow().timestamp())}",
        "token_type": "bearer",
        "business": serialize_business_token(business_token),
    }

# ==================== ROOT ====================
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Akagera Inc API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🚀 FastAPI Server Starting...")
    print("📍 API URL: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("📱 Apps Endpoint: http://localhost:8000/api/apps")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
"""
Admin Management Endpoints
Complex URL: /api/admin-xyz789-control
Password Protected Admin Dashboard
"""
import os
import base64
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query, Form, Path as FastAPIPath
from sqlalchemy.orm import Session
from database import get_db
from models import User, App, Service, Payment, License, Image, SiteContent
import hashlib
import uuid
from pydantic import BaseModel
from typing import List

# Admin router
admin_router = APIRouter(prefix="/api/admin-xyz789-control", tags=["Admin"])

# Admin password (use environment variable in production)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@Akagera2024!")

def verify_admin_password(password: str) -> bool:
    """Verify admin password"""
    return password == ADMIN_PASSWORD


def remove_stored_file(path_value: str | None) -> None:
    """Delete a stored file from disk if it exists."""
    if not path_value:
        return
    try:
        normalized_path = path_value if path_value.startswith("uploads/") else f"uploads/{path_value}"
        if os.path.exists(normalized_path):
            os.remove(normalized_path)
    except Exception as exc:
        print(f"Warning: could not remove stored file {path_value}: {exc}")


class PricingPlanItem(BaseModel):
    name: str
    price: str
    description: str
    features: List[str]

# ==================== DASHBOARD STATS ====================
@admin_router.get("/stats", tags=["Admin Dashboard"])
async def get_dashboard_stats(password: str, db: Session = Depends(get_db)):
    """Get admin dashboard statistics"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    total_users = db.query(User).count()
    total_apps = db.query(App).count()
    total_services = db.query(Service).count()
    total_payments = db.query(Payment).count()
    
    revenue = db.query(Payment).filter(Payment.status == "completed").all()
    total_revenue = sum(float(p.amount) for p in revenue)
    
    return {
        "total_users": total_users,
        "total_apps": total_apps,
        "total_services": total_services,
        "total_payments": total_payments,
        "total_revenue": total_revenue,
        "timestamp": datetime.utcnow().isoformat()
    }


@admin_router.get("/pricing", tags=["Site Content"])
async def get_pricing(password: str, db: Session = Depends(get_db)):
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")

    record = db.query(SiteContent).filter(SiteContent.content_key == "pricing").first()
    return {"pricing": record.content_value if record and isinstance(record.content_value, list) else []}


@admin_router.put("/pricing", tags=["Site Content"])
async def update_pricing(password: str, pricing: List[PricingPlanItem], db: Session = Depends(get_db)):
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")

    payload = [item.dict() for item in pricing]
    record = db.query(SiteContent).filter(SiteContent.content_key == "pricing").first()

    if record:
        record.content_value = payload
        record.updated_at = datetime.utcnow()
    else:
        record = SiteContent(content_key="pricing", content_value=payload)
        db.add(record)

    db.commit()
    return {"message": "Pricing updated successfully", "pricing": payload}

# ==================== USER MANAGEMENT ====================
@admin_router.get("/users", tags=["User Management"])
async def get_all_users(password: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all users"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    users = db.query(User).offset(skip).limit(limit).all()
    return {
        "total": db.query(User).count(),
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "google_id": u.google_id,
                "profile_picture": u.profile_picture,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None
            } for u in users
        ]
    }

@admin_router.delete("/users/{user_id}", tags=["User Management"])
async def delete_user(password: str, user_id: int, db: Session = Depends(get_db)):
    """Delete a user"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

# ==================== APP MANAGEMENT ====================
@admin_router.get("/apps", tags=["App Management"])
async def get_all_apps(password: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all apps"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    apps = db.query(App).offset(skip).limit(limit).all()
    return {
        "total": db.query(App).count(),
        "apps": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "short_description": a.short_description,
                "requires_license": a.requires_license,
                "download_url": a.download_url,
                "app_icon": a.app_icon,
                "app_logo": a.app_logo,
                "app_image": a.app_image,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None
            } for a in apps
        ]
    }

@admin_router.post("/apps", tags=["App Management"])
async def create_app(
    password: str = Query(...),
    name: str = Form(...),
    description: str = Form(...),
    short_description: str = Form(...),
    features: str = Form(None),
    how_it_works: str = Form(None),
    installation_steps: str = Form(None),
    requires_license: bool = Form(False),
    download_url: str = Form(None),
    app_icon: UploadFile = File(None),
    app_logo: UploadFile = File(None),
    app_image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Create a new app with full details and file uploads"""
    try:
        if not verify_admin_password(password):
            raise HTTPException(status_code=401, detail="Invalid admin password")
        
        import json
        from pathlib import Path
        
        print(f"📝 Creating app: {name}")
        print(f"📁 Features: {features}, Installation Steps: {installation_steps}")
        
        # Parse JSON fields
        features_list = None
        if features:
            try:
                features_list = json.loads(features) if isinstance(features, str) and features.startswith('[') else [f.strip() for f in features.split(',') if f.strip()]
            except (json.JSONDecodeError, Exception) as e:
                print(f"⚠️ Features parse warning: {e}")
                features_list = [f.strip() for f in features.split(',') if f.strip()] if isinstance(features, str) else features
        
        installation_steps_list = None
        if installation_steps:
            try:
                installation_steps_list = json.loads(installation_steps) if isinstance(installation_steps, str) and installation_steps.startswith('[') else [s.strip() for s in installation_steps.split(',') if s.strip()]
            except (json.JSONDecodeError, Exception) as e:
                print(f"⚠️ Installation steps parse warning: {e}")
                installation_steps_list = [s.strip() for s in installation_steps.split(',') if s.strip()] if isinstance(installation_steps, str) else installation_steps
        
        # Handle file uploads
        app_icon_path = None
        app_logo_path = None
        app_image_path = None
        
        upload_dir = Path("uploads/apps")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        async def save_file(file: UploadFile, prefix: str) -> str:
            if not file:
                return None
            try:
                import time
                timestamp = str(int(time.time() * 1000))
                file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
                filename = f"{prefix}_{timestamp}.{file_extension}"
                file_path = upload_dir / filename
                contents = await file.read()
                with open(file_path, "wb") as f:
                    f.write(contents)
                print(f"✅ Saved {prefix} to: {filename}")
                return f"uploads/apps/{filename}"
            except Exception as e:
                print(f"❌ Error saving file {prefix}: {e}")
                return None
        
        app_icon_path = await save_file(app_icon, "icon")
        app_logo_path = await save_file(app_logo, "logo")
        app_image_path = await save_file(app_image, "image")
        
        # Parse requires_license
        if isinstance(requires_license, str):
            requires_license = requires_license.lower() in ['true', 'yes', '1']
        
        new_app = App(
            name=name,
            description=description,
            short_description=short_description,
            features=features_list,
            how_it_works=how_it_works,
            installation_steps=installation_steps_list,
            requires_license=requires_license,
            download_url=download_url,
            app_icon=app_icon_path,
            app_logo=app_logo_path,
            app_image=app_image_path
        )
        db.add(new_app)
        db.commit()
        db.refresh(new_app)
        
        print(f"✅ App created successfully with ID: {new_app.id}")
        
        return {
            "message": "App created successfully", 
            "app_id": new_app.id, 
            "app": {
                "id": new_app.id,
                "name": new_app.name,
                "description": new_app.description,
                "app_icon": app_icon_path,
                "app_logo": app_logo_path,
                "app_image": app_image_path
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating app: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating app: {str(e)}"
        )

@admin_router.put("/apps/{app_id}", tags=["App Management"])
async def update_app(
    password: str,
    app_id: int,
    name: str = None,
    description: str = None,
    short_description: str = None,
    features: str = None,
    how_it_works: str = None,
    installation_steps: str = None,
    requires_license: bool = None,
    download_url: str = None,
    app_icon: UploadFile = File(None),
    app_logo: UploadFile = File(None),
    app_image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Update an app with all details"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    import json
    from pathlib import Path
    
    # Helper function to save file
    async def save_file(file: UploadFile, prefix: str) -> str:
        if not file:
            return None
        try:
            timestamp = datetime.utcnow().timestamp()
            file_extension = file.filename.split('.')[-1]
            filename = f"{prefix}_{timestamp}.{file_extension}"
            upload_dir = Path("uploads/apps")
            upload_dir.mkdir(parents=True, exist_ok=True)
            file_path = upload_dir / filename
            contents = await file.read()
            with open(file_path, "wb") as f:
                f.write(contents)
            return f"uploads/apps/{filename}"
        except Exception as e:
            print(f"Error saving file: {e}")
            return None
    
    if name is not None:
        app.name = name
    if description is not None:
        app.description = description
    if short_description is not None:
        app.short_description = short_description
    if features is not None:
        try:
            app.features = json.loads(features) if isinstance(features, str) else features
        except json.JSONDecodeError:
            app.features = [f.strip() for f in features.split(',') if f.strip()]
    if how_it_works is not None:
        app.how_it_works = how_it_works
    if installation_steps is not None:
        try:
            app.installation_steps = json.loads(installation_steps) if isinstance(installation_steps, str) else installation_steps
        except json.JSONDecodeError:
            app.installation_steps = [s.strip() for s in installation_steps.split(',') if s.strip()]
    if requires_license is not None:
        if isinstance(requires_license, str):
            requires_license = requires_license.lower() in ['true', 'yes', '1']
        app.requires_license = requires_license
    if download_url is not None:
        app.download_url = download_url
    
    # Handle file uploads
    if app_icon:
        app.app_icon = await save_file(app_icon, "icon")
    if app_logo:
        app.app_logo = await save_file(app_logo, "logo")
    if app_icon:
        remove_stored_file(app.app_icon)
        app.app_icon = await save_file(app_icon, "icon")
    if app_logo:
        remove_stored_file(app.app_logo)
        app.app_logo = await save_file(app_logo, "logo")
    if app_image:
        remove_stored_file(app.app_image)
        app.app_image = await save_file(app_image, "image")
    
    app.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "App updated successfully"}

@admin_router.delete("/apps/{app_id}", tags=["App Management"])
async def delete_app(password: str, app_id: int, db: Session = Depends(get_db)):
    """Delete an app"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    for path_value in [app.app_icon, app.app_logo, app.app_image]:
        remove_stored_file(path_value)
    
    db.delete(app)
    db.commit()
    return {"message": "App deleted successfully"}

# ==================== SERVICE MANAGEMENT ====================
@admin_router.get("/services", tags=["Service Management"])
async def get_all_services(password: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all services"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    services = db.query(Service).offset(skip).limit(limit).all()
    return {
        "total": db.query(Service).count(),
        "services": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "price": str(s.price),
                "icon": s.icon,
                "image_url": s.image_url,
                "service_type": s.service_type,
                "grants_business_portal_access": s.grants_business_portal_access,
                "portal_business_name": s.portal_business_name,
                "portal_category": s.portal_category,
                "portal_access_duration_days": s.portal_access_duration_days,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None
            } for s in services
        ]
    }

@admin_router.post("/services", tags=["Service Management"])
async def create_service(
    password: str = Query(...),
    name: str = Form(...),
    description: str = Form(...),
    price: str = Form(...),
    icon: str = Form(None),
    service_type: str = Form("app_license"),
    grants_business_portal_access: bool = Form(False),
    portal_business_name: str = Form(None),
    portal_category: str = Form(None),
    portal_access_duration_days: int = Form(365),
    service_image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Create a new service with file upload support"""
    try:
        if not verify_admin_password(password):
            raise HTTPException(status_code=401, detail="Invalid admin password")
        
        # Validate required fields
        if not name or not description:
            raise HTTPException(status_code=400, detail="Name and description are required")
        
        # Parse price
        try:
            price_float = float(price) if price else 0.0
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Price must be a valid number")
        
        from pathlib import Path
        import time
        
        print(f"📝 Creating service: {name}")
        
        # Handle file upload
        image_path = None
        if service_image:
            try:
                upload_dir = Path("uploads/services")
                upload_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = str(int(time.time() * 1000))
                file_extension = service_image.filename.split('.')[-1] if '.' in service_image.filename else 'bin'
                filename = f"service_{timestamp}.{file_extension}"
                file_path = upload_dir / filename
                
                contents = await service_image.read()
                with open(file_path, "wb") as f:
                    f.write(contents)
                
                image_path = f"uploads/services/{filename}"
                print(f"✅ Service image saved: {filename}")
            except Exception as e:
                print(f"⚠️ Warning - Could not save service image: {e}")
        
        if isinstance(grants_business_portal_access, str):
            grants_business_portal_access = grants_business_portal_access.lower() in ['true', 'yes', '1']
        if isinstance(portal_access_duration_days, str):
            try:
                portal_access_duration_days = int(portal_access_duration_days)
            except ValueError:
                portal_access_duration_days = 365

        new_service = Service(
            name=name,
            description=description,
            price=price_float,
            icon=icon,
            image_url=image_path,
            service_type=(service_type or "app_license").strip() or "app_license",
            grants_business_portal_access=bool(grants_business_portal_access),
            portal_business_name=portal_business_name.strip() if portal_business_name else None,
            portal_category=portal_category.strip() if portal_category else None,
            portal_access_duration_days=portal_access_duration_days,
        )
        db.add(new_service)
        db.commit()
        db.refresh(new_service)
        
        print(f"✅ Service created successfully with ID: {new_service.id}")
        
        return {
            "message": "Service created successfully", 
            "service_id": new_service.id, 
            "service": {
                "id": new_service.id,
                "name": new_service.name,
                "image_url": image_path
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating service: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating service: {str(e)}"
        )

@admin_router.put("/services/{service_id}", tags=["Service Management"])
async def update_service(
    password: str = Query(...),
    service_id: int = FastAPIPath(...),
    name: str = Form(None),
    description: str = Form(None),
    price: str = Form(None),
    icon: str = Form(None),
    service_type: str = Form(None),
    grants_business_portal_access: bool = Form(None),
    portal_business_name: str = Form(None),
    portal_category: str = Form(None),
    portal_access_duration_days: int = Form(None),
    service_image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Update a service with file upload support"""
    try:
        if not verify_admin_password(password):
            raise HTTPException(status_code=401, detail="Invalid admin password")
        
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        
        if name:
            service.name = name
        if description:
            service.description = description
        if price:
            try:
                service.price = float(price)
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail="Price must be a valid number")
        if icon:
            service.icon = icon
        if service_type is not None:
            service.service_type = (service_type or "app_license").strip() or "app_license"
        if grants_business_portal_access is not None:
            if isinstance(grants_business_portal_access, str):
                grants_business_portal_access = grants_business_portal_access.lower() in ['true', 'yes', '1']
            service.grants_business_portal_access = bool(grants_business_portal_access)
        if portal_business_name is not None:
            service.portal_business_name = portal_business_name.strip() if portal_business_name else None
        if portal_category is not None:
            service.portal_category = portal_category.strip() if portal_category else None
        if portal_access_duration_days is not None:
            try:
                service.portal_access_duration_days = int(portal_access_duration_days)
            except ValueError:
                service.portal_access_duration_days = 365
        
        # Handle file upload
        if service_image:
            try:
                from pathlib import Path
                import time
                
                remove_stored_file(service.image_url)
                upload_dir = Path("uploads/services")
                upload_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = str(int(time.time() * 1000))
                file_extension = service_image.filename.split('.')[-1] if '.' in service_image.filename else 'bin'
                filename = f"service_{timestamp}.{file_extension}"
                file_path = upload_dir / filename
                
                contents = await service_image.read()
                with open(file_path, "wb") as f:
                    f.write(contents)
                
                service.image_url = f"uploads/services/{filename}"
                print(f"✅ Service image updated: {filename}")
            except Exception as e:
                print(f"⚠️ Warning - Could not save service image: {e}")
        
        service.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(service)
        
        return {"message": "Service updated successfully", "service_id": service.id}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating service: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating service: {str(e)}")

@admin_router.delete("/services/{service_id}", tags=["Service Management"])
async def delete_service(password: str, service_id: int, db: Session = Depends(get_db)):
    """Delete a service"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    remove_stored_file(service.image_url)
    
    db.delete(service)
    db.commit()
    return {"message": "Service deleted successfully"}

# ==================== PAYMENT MANAGEMENT ====================
@admin_router.get("/payments", tags=["Payment Management"])
async def get_all_payments(password: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all payments"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    payments = db.query(Payment).offset(skip).limit(limit).all()
    return {
        "total": db.query(Payment).count(),
        "payments": [
            {
                "id": p.id,
                "user_id": p.user_id,
                "amount": str(p.amount),
                "status": p.status,
                "stripe_transaction_id": p.stripe_transaction_id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None
            } for p in payments
        ]
    }

@admin_router.get("/payments/{payment_id}", tags=["Payment Management"])
async def get_payment_details(password: str, payment_id: int, db: Session = Depends(get_db)):
    """Get payment details"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {
        "id": payment.id,
        "user_id": payment.user_id,
        "amount": str(payment.amount),
        "status": payment.status,
        "stripe_transaction_id": payment.stripe_transaction_id,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "updated_at": payment.updated_at.isoformat() if payment.updated_at else None
    }

# ==================== LICENSE MANAGEMENT ====================
@admin_router.get("/licenses", tags=["License Management"])
async def get_all_licenses(password: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all licenses"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    licenses = db.query(License).offset(skip).limit(limit).all()
    return {
        "total": db.query(License).count(),
        "licenses": [
            {
                "id": l.id,
                "user_id": l.user_id,
                "app_id": l.app_id,
                "service_id": l.service_id,
                "license_key": l.license_key,
                "expires_at": l.expires_at.isoformat() if l.expires_at else None,
                "is_active": l.is_active,
                "created_at": l.created_at.isoformat() if l.created_at else None
            } for l in licenses
        ]
    }

@admin_router.delete("/licenses/{license_id}", tags=["License Management"])
async def delete_license(password: str, license_id: int, db: Session = Depends(get_db)):
    """Delete a license"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    license = db.query(License).filter(License.id == license_id).first()
    if not license:
        raise HTTPException(status_code=404, detail="License not found")
    
    db.delete(license)
    db.commit()
    return {"message": "License deleted successfully"}

# ==================== IMAGE MANAGEMENT ====================
@admin_router.get("/images", tags=["Image Management"])
async def get_all_images(password: str, page_type: str = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all carousel/background images"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    query = db.query(Image)
    if page_type:
        query = query.filter(Image.page_type == page_type)
    
    images = query.order_by(Image.order).offset(skip).limit(limit).all()
    return {
        "total": query.count(),
        "images": [
            {
                "id": img.id,
                "filename": img.filename,
                "alt_text": img.alt_text,
                "page_type": img.page_type,
                "app_id": img.app_id,
                "service_id": img.service_id,
                "order": img.order,
                "is_active": img.is_active,
                "mime_type": img.mime_type,
                "size": os.path.getsize(img.url) if img.url and os.path.exists(img.url) else (len(img.data) if img.data else 0),
                "url": img.url,
                "created_at": img.created_at.isoformat() if img.created_at else None
            } for img in images
        ]
    }

@admin_router.get("/images/{image_id}/data", tags=["Image Management"])
async def get_image_data(password: str, image_id: int, db: Session = Depends(get_db)):
    """Return a data URL for display by reading the stored file from disk."""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")

    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    file_path = None
    if getattr(image, "url", None):
        file_path = image.url if image.url.startswith("uploads/") else f"uploads/{image.url}"
    elif getattr(image, "data", None):
        base64_data = base64.b64encode(image.data).decode('utf-8')
        return {
            "id": image.id,
            "filename": image.filename,
            "mime_type": image.mime_type,
            "data": f"data:{image.mime_type};base64,{base64_data}",
            "alt_text": image.alt_text
        }

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image file not found")

    with open(file_path, "rb") as fh:
        file_bytes = fh.read()
    base64_data = base64.b64encode(file_bytes).decode('utf-8')

    return {
        "id": image.id,
        "filename": image.filename,
        "mime_type": image.mime_type,
        "data": f"data:{image.mime_type};base64,{base64_data}",
        "alt_text": image.alt_text,
        "path": image.url,
    }

@admin_router.post("/images", tags=["Image Management"])
async def upload_carousel_image(
    password: str = Query(...),
    file: UploadFile = File(...),
    alt_text: str = "",
    page_type: str = "home",
    app_id: int = None,
    service_id: int = None,
    db: Session = Depends(get_db)
):
    """Upload a carousel or background image and store only the file path in the database."""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")

    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}")

        file_data = await file.read()
        if not file_data:
            raise HTTPException(status_code=400, detail="File is empty")

        mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }
        mime_type = mime_types.get(file_extension, 'image/jpeg')
        max_order = db.query(Image).filter(Image.page_type == page_type).count()

        from pathlib import Path
        upload_dir = Path("uploads/images")
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{page_type}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{file.filename}"
        file_path = upload_dir / filename
        with open(file_path, "wb") as fh:
            fh.write(file_data)

        relative_path = f"uploads/images/{filename}"
        new_image = Image(
            url=relative_path,
            data=None,
            filename=file.filename,
            mime_type=mime_type,
            alt_text=alt_text or file.filename.split('.')[0],
            page_type=page_type,
            app_id=app_id,
            service_id=service_id,
            order=max_order,
            is_active=True
        )
        db.add(new_image)
        db.commit()
        db.refresh(new_image)

        return {
            "message": "Image uploaded successfully",
            "image_id": new_image.id,
            "filename": file.filename,
            "size": len(file_data),
            "mime_type": mime_type,
            "path": relative_path,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")

@admin_router.put("/images/{image_id}", tags=["Image Management"])
async def update_image(
    password: str,
    image_id: int,
    alt_text: str = None,
    order: int = None,
    is_active: bool = None,
    db: Session = Depends(get_db)
):
    """Update image details"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    if alt_text is not None:
        image.alt_text = alt_text
    if order is not None:
        image.order = order
    if is_active is not None:
        image.is_active = is_active
    
    image.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Image updated successfully"}

@admin_router.delete("/images/{image_id}", tags=["Image Management"])
async def delete_image(password: str, image_id: int, db: Session = Depends(get_db)):
    """Delete a carousel image and its saved file from disk."""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")

    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        if image.url:
            file_path = image.url if image.url.startswith("uploads/") else f"uploads/{image.url}"
            if os.path.exists(file_path):
                os.remove(file_path)
    except Exception as e:
        print(f"Error deleting file: {e}")

    db.delete(image)
    db.commit()
    return {"message": "Image deleted successfully"}

@admin_router.post("/images/reorder", tags=["Image Management"])
async def reorder_images(password: str, image_ids: list, page_type: str, db: Session = Depends(get_db)):
    """Reorder carousel images"""
    if not verify_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    for index, image_id in enumerate(image_ids):
        image = db.query(Image).filter(Image.id == image_id, Image.page_type == page_type).first()
        if image:
            image.order = index
    
    db.commit()
    return {"message": "Images reordered successfully"}

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Subscription, User
from auth_utils import get_current_user
from serializers import serialize_subscription

router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])


@router.get("/me")
def my_subscriptions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Subscription).filter(Subscription.user_id == user.id).order_by(
        Subscription.created_at.desc()).all()
    return [serialize_subscription(s) for s in rows]


@router.post("/{sub_id}/cancel")
def cancel(sub_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Subscription).filter(Subscription.id == sub_id, Subscription.user_id == user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Subscription not found")
    s.status = "cancelled"
    s.cancelled_at = datetime.utcnow()
    db.commit()
    return {"message": "Subscription cancelled. Access continues until the end of the period."}

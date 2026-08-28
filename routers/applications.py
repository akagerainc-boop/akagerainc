"""Internship + job applications (multipart file upload)."""
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from models import Internship, InternshipApplication, JobPosition, JobApplication
from utils import validate_upload
from ratelimit import limiter

router = APIRouter(prefix="/api", tags=["Applications"])
UP = Path("uploads/applications")


def _save(file: UploadFile | None, prefix: str) -> str | None:
    if not file or not file.filename:
        return None
    data = file.file.read()
    validate_upload(file.filename, len(data), kind="doc")
    UP.mkdir(parents=True, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1].lower()
    name = f"{prefix}_{int(time.time() * 1000)}.{ext}"
    (UP / name).write_bytes(data)
    return f"uploads/applications/{name}"


@router.post("/internships/{slug}/apply", dependencies=[Depends(limiter("apply", 8, 600))])
async def apply_internship(
    slug: str,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    education: str = Form(None),
    interest_area: str = Form(None),
    preferred_duration: str = Form(None),
    start_date: str = Form(None),
    message: str = Form(None),
    cv: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    internship = db.query(Internship).filter(Internship.slug == slug).first()
    if not internship:
        raise HTTPException(status_code=404, detail="Internship not found")
    try:
        cv_path = _save(cv, "cv")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    app = InternshipApplication(
        internship_id=internship.id, full_name=full_name.strip(), email=email.lower(),
        phone=phone, education=education, interest_area=interest_area,
        preferred_duration=preferred_duration, message=message, cv_path=cv_path,
    )
    if start_date:
        try:
            from datetime import date
            app.start_date = date.fromisoformat(start_date)
        except ValueError:
            pass
    db.add(app)
    db.commit()
    return {"message": "Application submitted. We'll review it and get back to you."}


@router.post("/careers/{slug}/apply", dependencies=[Depends(limiter("apply", 8, 600))])
async def apply_job(
    slug: str,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    cover_letter: str = Form(None),
    resume: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    job = db.query(JobPosition).filter(JobPosition.slug == slug).first()
    if not job:
        raise HTTPException(status_code=404, detail="Position not found")
    try:
        resume_path = _save(resume, "resume")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    db.add(JobApplication(job_id=job.id, full_name=full_name.strip(), email=email.lower(),
                          phone=phone, cover_letter=cover_letter, resume_path=resume_path))
    db.commit()
    return {"message": "Application submitted. Thank you for your interest in Akagera Inc."}

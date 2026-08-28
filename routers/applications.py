"""Internship + job applications (multipart file upload)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from models import Internship, InternshipApplication, JobPosition, JobApplication
from utils import validate_upload
from ratelimit import limiter
from media_storage import persist_file

router = APIRouter(prefix="/api", tags=["Applications"])


def _store_cv(db: Session, file: UploadFile | None, tag: str) -> tuple[str | None, str | None]:
    """Returns (url, warning). Never raises — the application must still be accepted."""
    if not file or not file.filename:
        return None, None
    data = file.file.read()
    try:
        validate_upload(file.filename, len(data), kind="doc")
        return persist_file(db, data, file.filename, tag=tag), None
    except ValueError as e:
        return None, f"Your file could not be attached: {e} Your application was still submitted — we may email you for it."


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
    cv_path, warning = _store_cv(db, cv, "application-cv")

    app = InternshipApplication(
        internship_id=internship.id, full_name=full_name.strip(), email=email.lower(),
        phone=phone, education=education, interest_area=interest_area,
        preferred_duration=preferred_duration, message=message, cv_path=cv_path,
        status="submitted",
    )
    if start_date:
        try:
            app.start_date = date.fromisoformat(start_date)
        except ValueError:
            pass
    db.add(app)
    db.commit()
    return {"message": warning or "Application submitted. We'll review it and get back to you.",
            "cv_stored": cv_path is not None}


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
    resume_path, warning = _store_cv(db, resume, "application-resume")

    db.add(JobApplication(job_id=job.id, full_name=full_name.strip(), email=email.lower(),
                          phone=phone, cover_letter=cover_letter, resume_path=resume_path,
                          status="submitted"))
    db.commit()
    return {"message": warning or "Application submitted. Thank you for your interest in Akagera Inc.",
            "resume_stored": resume_path is not None}

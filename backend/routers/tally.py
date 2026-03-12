"""Tally XML file upload and upload history endpoints."""

import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal, get_db, get_readonly_db
from dependencies import get_restaurant_id
from models import Restaurant, TallyUpload

logger = logging.getLogger("ytip.tally")
router = APIRouter(prefix="/api/tally", tags=["Tally Integration"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB hard cap


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class TallyUploadResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    period_start: Optional[date]
    period_end: Optional[date]
    records_imported: int
    status: str
    error_message: Optional[str]
    uploaded_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Background task helpers
# ---------------------------------------------------------------------------
def _run_tally_import(upload_id: int, filepath: Path, restaurant_id: int) -> None:
    """Import a Tally XML file in a background thread.

    Imports are intentionally deferred — the router returns immediately with
    the upload_id so the client can poll GET /uploads/{upload_id} for status.
    """
    try:
        # Import here to avoid circular imports at module load time.
        # etl.etl_tally is created in a later phase; guard gracefully.
        from etl.etl_tally import import_tally_file  # type: ignore[import]
    except ImportError:
        logger.warning(
            "etl.etl_tally not yet implemented — marking upload %d as failed",
            upload_id,
        )
        with SessionLocal() as db:
            upload = db.get(TallyUpload, upload_id)
            if upload:
                upload.status = "failed"
                upload.error_message = "ETL module not yet implemented"
                upload.completed_at = datetime.utcnow()
                db.commit()
        return

    with SessionLocal() as db:
        restaurant = db.get(Restaurant, restaurant_id)
        if restaurant is None:
            logger.error(
                "Background tally import: restaurant_id=%d not found", restaurant_id
            )
            return
        try:
            import_tally_file(restaurant, db, filepath, upload_id)
        except Exception as exc:
            logger.error(
                "Background tally import failed for upload_id=%d: %s", upload_id, exc
            )
            upload = db.get(TallyUpload, upload_id)
            if upload:
                upload.status = "failed"
                upload.error_message = str(exc)[:500]
                upload.completed_at = datetime.utcnow()
                db.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/upload", response_model=TallyUploadResponse, status_code=201)
async def upload_tally_file(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_db),
) -> TallyUploadResponse:
    """Accept a Tally XML export file, persist it to disk, and queue import.

    Returns immediately with upload_id. Poll GET /uploads/{upload_id} for
    processing status.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    raw_bytes = await file.read()
    file_size = len(raw_bytes)

    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if file_size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )

    try:
        os.makedirs(settings.tally_upload_dir, exist_ok=True)

        safe_filename = Path(file.filename).name  # strip any path components
        dest_path = Path(settings.tally_upload_dir) / f"{rid}_{safe_filename}"

        dest_path.write_bytes(raw_bytes)

        upload = TallyUpload(
            restaurant_id=rid,
            filename=safe_filename,
            file_size=file_size,
            status="processing",
        )
        db.add(upload)
        db.flush()  # get upload.id before commit
        upload_id = upload.id
        db.commit()
        db.refresh(upload)

        background_tasks.add_task(
            _run_tally_import, upload_id, dest_path, rid
        )

        logger.info(
            "Tally upload accepted: upload_id=%d restaurant_id=%d filename=%s size=%d",
            upload_id, rid, safe_filename, file_size,
        )
        return TallyUploadResponse.model_validate(upload)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[API] POST /api/tally/upload failed: %s | restaurant_id=%d", exc, rid
        )
        raise HTTPException(status_code=500, detail="Failed to process upload")


@router.get("/uploads", response_model=List[TallyUploadResponse])
def list_tally_uploads(
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> List[TallyUploadResponse]:
    """Return the 50 most recent Tally uploads for this restaurant."""
    try:
        rows = (
            db.query(TallyUpload)
            .filter(TallyUpload.restaurant_id == rid)
            .order_by(TallyUpload.uploaded_at.desc())
            .limit(50)
            .all()
        )
        return [TallyUploadResponse.model_validate(r) for r in rows]
    except Exception as exc:
        logger.error(
            "[API] GET /api/tally/uploads failed: %s | restaurant_id=%d", exc, rid
        )
        raise HTTPException(status_code=500, detail="Failed to load upload history")


@router.get("/uploads/{upload_id}", response_model=TallyUploadResponse)
def get_tally_upload(
    upload_id: int,
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> TallyUploadResponse:
    """Return detailed status for a single Tally upload."""
    try:
        upload = (
            db.query(TallyUpload)
            .filter(
                TallyUpload.id == upload_id,
                TallyUpload.restaurant_id == rid,
            )
            .first()
        )
        if upload is None:
            raise HTTPException(status_code=404, detail="Upload not found")
        return TallyUploadResponse.model_validate(upload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[API] GET /api/tally/uploads/%d failed: %s | restaurant_id=%d",
            upload_id, exc, rid,
        )
        raise HTTPException(status_code=500, detail="Failed to load upload details")

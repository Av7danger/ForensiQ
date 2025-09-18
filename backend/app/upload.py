"""
Upload Router for ForensiQ API
Handles UFDR file uploads and processing
"""

import os
import hashlib
import zipfile
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from db import get_database
from models import Case, UFDRFile, ProcessingJob
from parsers.ufdr_parser import UFDRParser

router = APIRouter()

@router.post("/")
async def upload_ufdr_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    case_id: str = Form(...),
    investigator: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_database)
):
    """
    Upload and process a UFDR file.
    
    Args:
        file: UFDR file upload
        case_id: Case identifier
        investigator: Investigator name
        description: Optional case description
        
    Returns:
        Upload status and processing job ID
    """
    
    # Validate file type
    if not file.filename.lower().endswith(('.ufdr', '.zip')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only UFDR/ZIP files are supported."
        )
    
    # Check file size (limit to 2GB)
    if file.size > 2 * 1024 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 2GB."
        )
    
    try:
        # Create or get case
        case = db.query(Case).filter(Case.case_id == case_id).first()
        if not case:
            case = Case(
                case_id=case_id,
                investigator=investigator,
                description=description or f"Case {case_id}"
            )
            db.add(case)
            db.commit()
            db.refresh(case)
        
        # Generate file hash
        file_content = await file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Check for duplicate files
        existing_file = db.query(UFDRFile).filter(
            UFDRFile.file_hash == file_hash,
            UFDRFile.case_id == case.id
        ).first()
        
        if existing_file:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "duplicate",
                    "message": "File already exists in this case",
                    "file_id": str(existing_file.id),
                    "case_id": case_id
                }
            )
        
        # Save file
        upload_dir = Path("uploads") / case_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_id = str(uuid4())
        file_path = upload_dir / f"{file_id}_{file.filename}"
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Create database record
        ufdr_file = UFDRFile(
            case_id=case.id,
            filename=file.filename,
            file_hash=file_hash,
            file_size=len(file_content),
            upload_path=str(file_path),
            processing_status="pending"
        )
        db.add(ufdr_file)
        db.commit()
        db.refresh(ufdr_file)
        
        # Create processing job
        job = ProcessingJob(
            case_id=case.id,
            job_type="ufdr_parse",
            status="pending",
            metadata={"file_id": str(ufdr_file.id)}
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Start background processing
        background_tasks.add_task(
            process_ufdr_file,
            str(ufdr_file.id),
            str(job.id),
            str(file_path)
        )
        
        return {
            "status": "success",
            "message": "File uploaded successfully",
            "file_id": str(ufdr_file.id),
            "job_id": str(job.id),
            "case_id": case_id,
            "filename": file.filename,
            "file_size": len(file_content),
            "file_hash": file_hash
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/status/{job_id}")
async def get_processing_status(
    job_id: str,
    db: Session = Depends(get_database)
):
    """Get processing job status."""
    
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job_id,
        "status": job.status,
        "progress": job.progress,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error_message": job.error_message,
        "metadata": job.metadata
    }

async def process_ufdr_file(file_id: str, job_id: str, file_path: str):
    """Background task to process UFDR file."""
    
    db = next(get_database())
    
    try:
        # Update job status
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job:
            job.status = "running"
            job.progress = 0.1
            db.commit()
        
        # Initialize parser
        parser = UFDRParser()
        
        # Parse UFDR file
        results = await parser.parse_ufdr_file(file_path, file_id)
        
        # Update progress
        if job:
            job.progress = 0.5
            db.commit()
        
        # Store parsed data in database
        await parser.store_parsed_data(results, db)
        
        # Update progress
        if job:
            job.progress = 0.8
            db.commit()
        
        # Generate embeddings
        from nlp.embeddings import generate_embeddings
        await generate_embeddings(file_id, db)
        
        # Complete job
        if job:
            job.status = "completed"
            job.progress = 1.0
            job.completed_at = "now()"
            db.commit()
        
        # Update file status
        ufdr_file = db.query(UFDRFile).filter(UFDRFile.id == file_id).first()
        if ufdr_file:
            ufdr_file.processing_status = "completed"
            ufdr_file.processed_at = "now()"
            db.commit()
            
    except Exception as e:
        # Mark job as failed
        if job:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
        
        # Update file status
        ufdr_file = db.query(UFDRFile).filter(UFDRFile.id == file_id).first()
        if ufdr_file:
            ufdr_file.processing_status = "failed"
            db.commit()
    
    finally:
        db.close()
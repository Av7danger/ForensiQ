"""
API endpoints for case management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ....database import get_db
from ....models.case import Case, Evidence, CaseStatus
from ....schemas.case import (
    CaseCreate, CaseUpdate, Case, CaseWithEvidence,
    EvidenceCreate, EvidenceUpdate, Evidence
)

router = APIRouter()

# Case endpoints
@router.post("/cases/", response_model=Case, status_code=201)
def create_case(case: CaseCreate, db: Session = Depends(get_db)):
    """Create a new forensic case."""
    db_case = Case(**case.dict())
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

@router.get("/cases/", response_model=List[Case])
def list_cases(
    skip: int = 0, 
    limit: int = 100, 
    status: CaseStatus = None,
    db: Session = Depends(get_db)
):
    """List all forensic cases with optional status filter."""
    query = db.query(Case)
    if status:
        query = query.filter(Case.status == status)
    return query.offset(skip).limit(limit).all()

@router.get("/cases/{case_id}", response_model=CaseWithEvidence)
def get_case(case_id: int, db: Session = Depends(get_db)):
    """Get a specific case by ID with its evidence."""
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    return db_case

@router.put("/cases/{case_id}", response_model=Case)
def update_case(
    case_id: int, 
    case: CaseUpdate, 
    db: Session = Depends(get_db)
):
    """Update a case."""
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    update_data = case.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_case, field, value)
    
    db.commit()
    db.refresh(db_case)
    return db_case

@router.delete("/cases/{case_id}", status_code=204)
def delete_case(case_id: int, db: Session = Depends(get_db)):
    """Delete a case."""
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    db.delete(db_case)
    db.commit()
    return None

# Evidence endpoints
@router.post("/evidence/", response_model=Evidence, status_code=201)
def create_evidence(
    evidence: EvidenceCreate, 
    db: Session = Depends(get_db)
):
    """Add evidence to a case."""
    # Verify case exists
    case = db.query(Case).filter(Case.id == evidence.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    db_evidence = Evidence(**evidence.dict())
    db.add(db_evidence)
    db.commit()
    db.refresh(db_evidence)
    return db_evidence

@router.get("/evidence/{evidence_id}", response_model=Evidence)
def get_evidence(evidence_id: int, db: Session = Depends(get_db)):
    """Get evidence by ID."""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence

@router.put("/evidence/{evidence_id}", response_model=Evidence)
def update_evidence(
    evidence_id: int, 
    evidence: EvidenceUpdate, 
    db: Session = Depends(get_db)
):
    """Update evidence."""
    db_evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not db_evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    update_data = evidence.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_evidence, field, value)
    
    db.commit()
    db.refresh(db_evidence)
    return db_evidence

@router.delete("/evidence/{evidence_id}", status_code=204)
def delete_evidence(evidence_id: int, db: Session = Depends(get_db)):
    """Delete evidence."""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    db.delete(evidence)
    db.commit()
    return None

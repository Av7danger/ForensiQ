"""
Pydantic schemas for case management.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from ..models.case import CaseStatus, EvidenceType

# Shared properties
class EvidenceBase(BaseModel):
    name: str
    description: Optional[str] = None
    evidence_type: EvidenceType
    file_path: Optional[str] = None
    hash_md5: Optional[str] = None
    hash_sha1: Optional[str] = None
    hash_sha256: Optional[str] = None
    collected_at: Optional[datetime] = None

class CaseBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: CaseStatus = CaseStatus.OPEN

# Properties to receive on case creation
class CaseCreate(CaseBase):
    pass

# Properties to receive on case update
class CaseUpdate(CaseBase):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CaseStatus] = None

# Properties shared by models stored in DB
class CaseInDBBase(CaseBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Properties to return to client
class Case(CaseInDBBase):
    pass

# Properties stored in DB
class CaseInDB(CaseInDBBase):
    pass

# Evidence schemas
class EvidenceCreate(EvidenceBase):
    case_id: int

class EvidenceUpdate(EvidenceBase):
    name: Optional[str] = None
    description: Optional[str] = None
    evidence_type: Optional[EvidenceType] = None

class Evidence(EvidenceBase):
    id: int
    case_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Case with evidence
class CaseWithEvidence(Case):
    evidence: List[Evidence] = []

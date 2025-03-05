from pydantic import BaseModel, EmailStr, UUID4, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(UserBase):
    password: str

class UserResponse(BaseModel):
    id: UUID4
    email: EmailStr
    is_admin: bool
    subscription_tier: str
    created_at: datetime

    class Config:
        orm_mode = True

# Query Schemas
class QueryBase(BaseModel):
    query_text: str
    signals_to_track: Optional[List[str]] = []
    is_paused: bool = False
    check_frequency_hours: int = 24

class QueryCreate(QueryBase):
    pass

class QueryResponse(QueryBase):
    id: UUID4
    user_id: UUID4
    created_at: datetime
    last_run_at: Optional[datetime]

    class Config:
        orm_mode = True

class QueriesListResponse(BaseModel):
    queries: List[QueryResponse]
    max_queries: int
    remaining_queries: int
    is_paid: bool

    class Config:
        orm_mode = True

class QueryUpdate(BaseModel):
    is_paused: Optional[bool] = None
    check_frequency_hours: Optional[int] = None
    signals_to_track: Optional[List[str]] = None

    class Config:
        orm_mode = True

# Lead Schemas
class LeadBase(BaseModel):
    company_name: str
    website: Optional[str]
    employee_name: Optional[str]
    employee_linkedin: Optional[str]
    employee_email: Optional[str]
    signals: Optional[Dict]
    reasoning: Optional[str]

class LeadCreate(LeadBase):
    query_id: UUID4

class LeadUpdate(BaseModel):
    is_checked: Optional[bool] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class LeadResponse(BaseModel):
    id: UUID4
    query_id: UUID4
    company_name: Optional[str] = None
    website: Optional[str] = None
    employee_name: Optional[str] = None
    employee_linkedin: Optional[str] = None
    employee_email: Optional[str] = None
    signals: Optional[List[str]] = None
    reasoning: Optional[str] = None
    is_checked: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

# Token Schema
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Search Request Schema
class SearchRequest(BaseModel):
    query: str

    class Config:
        json_schema_extra = {
            "example": {
                "query": "example search query"
            }
        }

class EmailQuery(BaseModel):
    employee_name: str
    company_name: str

    class Config:
        json_schema_extra = {
            "example": {
                "employee_name": "John Smith",
                "company_name": "Acme Corp"
            }
        }

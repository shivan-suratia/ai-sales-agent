from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database.database import get_db
from ..database.models import User, Query
from ..schemas import QueryCreate, QueryResponse, QueryUpdate
from ..auth.dependencies import get_current_active_user

router = APIRouter(prefix="/queries", tags=["queries"])

@router.post("/", response_model=QueryResponse)
async def create_query(
    query: QueryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_query = Query(
        user_id=current_user.id,
        **query.dict()
    )
    db.add(db_query)
    db.commit()
    db.refresh(db_query)
    return db_query

@router.get("/", response_model=List[QueryResponse])
async def get_queries(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return db.query(Query).filter(Query.user_id == current_user.id).all()

@router.put("/{query_id}", response_model=QueryResponse)
async def update_query(
    query_id: str,
    query_update: QueryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_query = db.query(Query).filter(
        Query.id == query_id,
        Query.user_id == current_user.id
    ).first()
    
    if not db_query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    for key, value in query_update.dict(exclude_unset=True).items():
        setattr(db_query, key, value)
    
    db.commit()
    db.refresh(db_query)
    return db_query

@router.delete("/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query(
    query_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_query = db.query(Query).filter(
        Query.id == query_id,
        Query.user_id == current_user.id
    ).first()
    
    if not db_query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    db.delete(db_query)
    db.commit()
    return None

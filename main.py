from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.lead_finder import LeadFinder
from core.intent_signal_finder import IntentSignalFinder
import logging
import sys
from dotenv import load_dotenv
from app.routes import auth, queries
from app.database.database import engine, Base, get_db
from fastapi.responses import JSONResponse
from app.auth.dependencies import get_current_active_user
from app.database.models import User, Query, Lead
from app.schemas import SearchRequest, LeadResponse, QueryResponse, QueryCreate, QueryUpdate, LeadUpdate, QueriesListResponse, EmailQuery
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from uuid import UUID

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sales Intelligence API",
    description="API for finding leads and analyzing intent signals",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth routes
app.include_router(auth.router)
app.include_router(queries.router)

# Initialize services
lead_finder = LeadFinder()
intent_signal_finder = IntentSignalFinder()

# Create tables
Base.metadata.create_all(bind=engine)

class IntentQuery(BaseModel):
    lead_query: str

@app.post("/find-leads")
async def find_leads(query: QueryCreate):
    try:
        logger.info(f"Received query: {query.query}")
        leads = await intent_signal_finder.find_leads(query.query)
        logger.info(f"Found {len(leads)} leads")
        return {"leads": leads}
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/find-intent-signals")
async def find_intent_signals(
    request: SearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        results = await intent_signal_finder.find_intent_signals(request.query)
        print("Got results:", results)
        
        # Create new query using the correct fields
        new_query = Query(
            user_id=current_user.id,
            query_text=request.query,
            signals_to_track=results.get('successful_queries', []),
            is_paused=False,
            check_frequency_hours=24
        )
        print("Created query object:", vars(new_query))
        
        db.add(new_query)
        db.flush()
        
        # Save leads
        if results.get('contacts'):
            for contact in results['contacts']:
                lead = Lead(
                    query_id=new_query.id,
                    company_name=contact.get('company'),
                    website=contact.get('url'),
                    employee_name=contact.get('name'),
                    employee_linkedin=contact.get('linkedin_url'),
                    employee_email=contact.get('email'),
                    signals=contact.get('signals'),
                    reasoning=contact.get('reasoning'),
                    is_checked=False  # Only include existing fields
                )
                db.add(lead)
        
        db.commit()
        return results

    except Exception as e:
        db.rollback()
        print(f"Error occurred: {str(e)}")
        print(f"Error type: {type(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/get-email")
async def get_email(query: EmailQuery):
    """Get the most probable email address for an employee at a company"""
    try:
        logger.info(f"Getting email for {query.employee_name} at {query.company_name}")
        email = await intent_signal_finder.get_email(query.employee_name, query.company_name)
        logger.info(f"Found email: {email}")
        return {"email": email}
    except Exception as e:
        logger.error(f"Error getting email: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {
        "message": "Welcome to Sales Intelligence API",
        "version": "1.0.0",
        "endpoints": [
            "/find-leads",
            "/find-intent-signals"
        ]
    }

@app.get("/queries/{query_id}/leads", response_model=List[LeadResponse])
async def get_leads_for_query(
    query_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Query).filter(
            Query.id == query_id,
            Query.user_id == current_user.id
        ).first()
        
        if not query:
            raise HTTPException(
                status_code=404,
                detail="Query not found or unauthorized"
            )
        
        leads = db.query(Lead).filter(Lead.query_id == query_id).all()
        
        leads_data = []
        for lead in leads:
            # Convert signals to list if it's not already
            signals_list = lead.signals if isinstance(lead.signals, list) else []
            
            lead_dict = {
                "id": lead.id,
                "query_id": lead.query_id,
                "company_name": lead.company_name,
                "website": lead.website,
                "employee_name": lead.employee_name,
                "employee_linkedin": lead.employee_linkedin,
                "employee_email": lead.employee_email,
                "signals": signals_list,  # Ensure it's a list
                "reasoning": lead.reasoning,
                "is_checked": lead.is_checked or False,
                "created_at": lead.created_at
            }
            leads_data.append(lead_dict)
        
        return leads_data

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/queries", response_model=QueriesListResponse)
async def get_user_queries(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    queries = db.query(Query).filter(
        Query.user_id == current_user.id,
    ).order_by(Query.created_at.desc()).all()
    
    # Add remaining queries info
    max_queries = 10 if current_user.is_paid else 3
    current_queries = len(queries)
    remaining_queries = max_queries - current_queries
    
    return QueriesListResponse(
        queries=queries,
        max_queries=max_queries,
        remaining_queries=remaining_queries,
        is_paid=current_user.is_paid
    )

@app.patch("/queries/{query_id}")
async def update_query(
    query_id: UUID,
    update_data: QueryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Find query and verify ownership
    query = db.query(Query).filter(
        Query.id == query_id,
        Query.user_id == current_user.id
    ).first()
    
    if not query:
        raise HTTPException(
            status_code=404,
            detail="Query not found or unauthorized"
        )
    
    # Update only provided fields
    if update_data.is_paused is not None:
        query.is_paused = update_data.is_paused
    if update_data.check_frequency_hours is not None:
        query.check_frequency_hours = update_data.check_frequency_hours
    
    db.commit()
    return query

@app.delete("/queries/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query(
    query_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Find and verify ownership
    result = db.query(Query).filter(
        Query.id == query_id,
        Query.user_id == current_user.id
    ).delete()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Query not found or unauthorized"
        )
    
    db.commit()
    return None

@app.patch("/leads/{lead_id}")
async def update_lead(
    lead_id: UUID,
    update_data: LeadUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Find lead and verify ownership through query
    lead = db.query(Lead).join(Query).filter(
        Lead.id == lead_id,
        Query.user_id == current_user.id
    ).first()
    
    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found or unauthorized"
        )
    
    # Update only provided fields
    if update_data.is_checked is not None:
        lead.is_checked = update_data.is_checked
    if update_data.notes is not None:
        lead.notes = update_data.notes
    
    db.commit()
    return lead

@app.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Find lead and verify ownership through query
    result = db.query(Lead).join(Query).filter(
        Lead.id == lead_id,
        Query.user_id == current_user.id
    ).delete(synchronize_session=False)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Lead not found or unauthorized"
        )
    
    db.commit()
    return None

@app.get("/leads/{lead_id}")
async def get_lead(
    lead_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    lead = db.query(Lead).join(Query).filter(
        Lead.id == lead_id,
        Query.user_id == current_user.id
    ).first()
    
    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found or unauthorized"
        )
    
    return lead 
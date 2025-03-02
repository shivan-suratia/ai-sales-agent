from fastapi import APIRouter, HTTPException, Request
from core.lead_finder import LeadFinder
from core.intent_signal_finder import IntentSignalFinder
from core.query_parser import parse_query
from typing import Dict

router = APIRouter()
lead_finder = LeadFinder()
intent_signal_finder = IntentSignalFinder()

@router.post("/search")
async def search_companies(request: Request) -> Dict:
    user_input = await request.form()
    user_input = user_input.get('criteria')
    prompt = parse_query(user_input)

    # Here you would call the gpt4o-mini API with the prompt
    # response = call_gpt4o_mini(prompt)

    return {"prompt": prompt}

@router.post("/find_intent_signals")
async def find_intent_signals(request: Request) -> Dict:
    """Find intent signals for a given lead/company"""
    try:
        data = await request.json()
        user_input = data.get('lead_query')
        
        if not user_input:
            raise HTTPException(status_code=400, detail="lead_query is required")
            
        results = await intent_signal_finder.find_intent_signals(user_input)
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import APIRouter
from core.query_parser import parse_query, create_prompt
from core.data_fetcher import fetch_leads
#from core.lead_ranker import rank_leads

router = APIRouter()

@router.post("/find_leads")
async def find_leads(user_query: str):
    structured_query = parse_query(user_query)
    raw_leads = fetch_leads(structured_query)
#    ranked_leads = rank_leads(raw_leads)
    return {"leads": raw_leads}

@router.post("/search")
async def search_companies(user_input: str):
    prompt = create_prompt(user_input)
    
    # Here you would call the gpt4o-mini API with the prompt
    # response = call_gpt4o_mini(prompt)
    
    return {"prompt": prompt}  # Return the prompt or the response from gpt4o-mini

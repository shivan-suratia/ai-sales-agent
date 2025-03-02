from typing import Dict, List
from openai import OpenAI
import os
import logging
import json

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def parse_query(query: str) -> Dict:
    """
    Parse the user query to extract search queries, decision makers, and company attributes
    """
    logger.info(f"Parsing query: {query}")
    
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("OPENAI_API_KEY not found in environment variables")
        raise ValueError("OPENAI_API_KEY not configured")

    prompt = f"""

    User Query: {query}

    Analyze this lead search query and create two components:
    1. A prompt for a web search to find companies that match the user query.
    2. A list of key decision maker roles to find, job titles only.

    Output the results in JSON format.
    
    Example input:
    "top AI startups San Francisco 50-200 employees"

    Example output:
    {{
        "search_query": "top AI startups San Francisco 50-200 employees",
        "decision_makers": ["CTO", "Technical Director", "VP of Engineering"]
    }}

    Example input:
    "find me VP/Directorof Marketing for Biotech companies in New Jersey with 50-200 employees"

    Example output:
    {{
        "search_query": "biotech companies New Jersey 50-200 employees",
        "decision_makers": ["VP of Marketing", "Director of Marketing"]
    }}
    """
    
    try:
        logger.debug("Sending request to OpenAI")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates precise search queries and always responds with valid JSON."},
                {"role": "user", "content": prompt}
            ]
        )
        
        result = response.choices[0].message.content
        logger.debug(f"Raw OpenAI response: {result}")
        
        # Clean the response
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()
        
        try:
            parsed = json.loads(result)
            logger.info("Successfully parsed OpenAI response")
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Cleaned response: {result}")
            raise ValueError(f"Failed to parse OpenAI response: {e}")
            
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}", exc_info=True)
        raise

# Add any other necessary functions or imports here

async def get_search_params(query: str) -> Dict:
    """Get search parameters from ChatGPT"""
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a company search query expert."},
                {"role": "user", "content": get_prompt(query)}
            ]
        )
        result = response.choices[0].message.content
        
        # Clean the response
        result = result.strip()
        if result.startswith('```json'):
            result = result[7:]
        if result.startswith('```'):
            result = result[3:]
        if result.endswith('```'):
            result = result[:-3]
        result = result.strip()
        
        return json.loads(result)
        
    except Exception as e:
        print(f"Error getting search params: {str(e)}")
        return {}
    

def get_prompt(query: str) -> str:
    """Return the hardcoded prompt template with the user's query"""
    return f"""You are an expert at translating a user query for company search (natural language) into a Companies API /companies API call.

    The API call consists of the following:
    - attribute
    - operator
    - sign
    - values

    The attributes must match one of the following:
    - about.businessType
    - about.industries
    - about.totalEmployees
    - about.yearFounded
    - finances.revenue
    - finances.stockExchange
    - locations.headquarters.city.code
    - locations.headquarters.continent.code
    - locations.headquarters.country.code
    - locations.headquarters.state.code
    - socials
    - technologies.active
    - technologies.categories

    The operator must be 'and' or 'or'

    The sign must match one of the following:
    - equals
    - notEquals

    The values must be an array of strings which match the attribute.

    Notes:
    1. For businessType, values must be one of:
    ["educational-institution", "nonprofit", "government-agency", "partnership", "privately-held", "public-company", "self-employed", "sole-proprietorship"]

    2. For about.industry, if the industry has two words, separate them with a hyphen. 

    3. For totalEmployees, values must be one of:
    ["1-10", "10-50", "50-200", "200-500", "500-1k", "1k-5k", "5k-10k", "over-10k"]
    If the user query doesn't fit exactly, you can add multiple ranges.

    4. For location.headquarters.city.code format:
    "city-code|state-code|country-code"
    Example: "new-york|new-york|us"

    5. For location.headquarters.state.code format:
    "state-code|country-code"
    Example: "new-york|us"

    6. For location.headquarters.country.code format:
    ["country-code"]
    Example: ["us"]

    User Query: {query}

    Return only a JSON array of search parameters. Example format:
    [
        {{
            "attribute": "about.industries",
            "operator": "and",
            "sign": "equals",
            "values": ["marketing"]
        }},
        {{
            "attribute": "locations.headquarters.city.code",
            "operator": "and",
            "sign": "equals",
            "values": ["new-york|new-york|us"]
        }},
        {{
            "attribute": "about.totalEmployees",
            "operator": "and",
            "sign": "equals",
            "values": ["200-500"]
        }}
    ]"""

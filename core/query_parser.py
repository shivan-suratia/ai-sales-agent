from typing import Dict, List
import openai
from pydantic import BaseModel

class QueryComponents(BaseModel):
    company_profile: str
    decision_makers: List[str]

def parse_query(user_input: str) -> Dict:
    """
    Use GPT to parse user input into company profile and decision maker roles.
    Returns a structured JSON with these components.
    """
    system_prompt = """
    You are a B2B sales assistant. Analyze the user's company targeting criteria and:
    1. Extract the company profile/characteristics they're looking for
    2. Identify or suggest relevant decision maker roles
    
    Return ONLY a JSON with two fields:
    - company_profile: string describing target company characteristics
    - decision_makers: list of job titles for key decision makers
    """
    
    user_prompt = f"Parse this sales targeting criteria: {user_input}"
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error parsing query: {str(e)}")

def create_company_search_prompt(company_profile: str) -> str:
    """
    Create a prompt for GPT to search for companies matching the profile.
    """
    return f"""
    Search the web and find 10 companies that match this profile: {company_profile}
    
    For each company, provide:
    1. Company name
    2. Website URL
    3. Brief description
    4. Keywords/tags
    
    Return the results as a JSON list.
    """

def create_linkedin_search_query(company_name: str, job_title: str) -> str:
    """
    Create a Google X-Ray search query for LinkedIn profiles
    """
    return f'site:linkedin.com/in/ "{company_name}" "{job_title}"'

def guess_email_format(first_name: str, last_name: str, domain: str) -> List[str]:
    """
    Generate potential email formats for validation
    """
    formats = [
        f"{first_name}@{domain}",
        f"{first_name}.{last_name}@{domain}",
        f"{first_name[0]}{last_name}@{domain}",
        f"{first_name}{last_name[0]}@{domain}",
        f"{last_name}.{first_name}@{domain}"
    ]
    return formats

def create_prompt(user_input):
    """
    Create a prompt for gpt4o-mini based on user input.
    """
    prompt = f"Search for companies that meet the following criteria: {user_input}"
    return prompt

# Add any other necessary functions or imports here

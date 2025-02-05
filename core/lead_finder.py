from typing import List, Dict
import asyncio
from services.linkedin_scraper import LinkedInScraper
from services.email_validator import EmailValidator
from core.query_parser import (
    parse_query, 
    create_company_search_prompt,
    create_linkedin_search_query,
    guess_email_format
)
import random

class LeadFinder:
    def __init__(self):
        self.linkedin_scraper = LinkedInScraper()
        self.email_validator = EmailValidator()

    async def find_leads(self, user_query: str) -> Dict:
        # Step 1: Parse the query
        query_components = parse_query(user_query)
        
        # Step 2: Find matching companies
        company_prompt = create_company_search_prompt(query_components['company_profile'])
        companies = await self._search_companies(company_prompt)
        
        # Step 3: Find LinkedIn profiles for each company
        leads = []
        for company in companies:
            company_leads = await self._find_company_leads(
                company, 
                query_components['decision_makers']
            )
            leads.extend(company_leads)
        
        # Step 4: Validate emails
        validated_leads = await self._validate_lead_emails(leads)
        
        return validated_leads

    async def _search_companies(self, prompt: str) -> List[Dict]:
        """
        Use GPT with web search to find matching companies
        """
        # Implementation using GPT-4 with web search capability
        pass

    async def _find_company_leads(self, company: Dict, decision_makers: List[str]) -> List[Dict]:
        """
        Find LinkedIn profiles for each decision maker role using scraping
        """
        leads = []
        for role in decision_makers:
            profiles = await self.linkedin_scraper.search_profiles(
                company_name=company['name'],
                job_title=role,
                limit=3
            )
            
            for profile in profiles:
                leads.append({
                    'name': profile['name'],
                    'linkedin_url': profile['profile_url'],
                    'company': company['name'],
                    'company_website': company['website'],
                    'role': role,
                    'headline': profile.get('headline', ''),
                    'location': profile.get('location', '')
                })
            
            # Add delay between searches to avoid detection
            await asyncio.sleep(random.uniform(2, 5))
        
        return leads

    async def _validate_lead_emails(self, leads: List[Dict]) -> List[Dict]:
        """
        Validate and add email addresses to leads
        """
        for lead in leads:
            name_parts = lead['name'].split()
            first_name = name_parts[0]
            last_name = name_parts[-1]
            domain = lead['company_website'].split('www.')[-1]
            
            email_formats = guess_email_format(first_name, last_name, domain)
            
            for email in email_formats[:3]:  # Try up to 3 formats
                if await self.email_validator.is_valid(email):
                    lead['email'] = email
                    break
        
        return leads
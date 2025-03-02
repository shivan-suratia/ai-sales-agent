from typing import List, Dict
import asyncio
import json
from services.linkedin_scraper import LinkedInScraper
from services.web_searcher import WebSearcher
from core.query_parser import (
    parse_query
)
import random
import os
import logging
from openai import OpenAI
import aiohttp
from core.query_parser import get_search_params

logger = logging.getLogger(__name__)

class LeadFinder:
    def __init__(self):
        self.linkedin_scraper = LinkedInScraper()
        self.web_searcher = WebSearcher()
        self.companies_api_key = os.getenv('COMPANIES_API_KEY')
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    async def find_leads(self, user_query: str) -> Dict:
        try:
            # Step 1: Parse the query
            parsed = parse_query(user_query)
            search_params = await get_search_params(user_query)
            logger.info(f"search_params: {search_params}")
            
            # Step 2: Search for and analyze companies
            companies = []
            company_results = await self._search_companies(search_params)
            logger.info(f"company_results: {company_results}")
            formatted_company_results = self._analyze_companies_data(company_results, search_params)
            logger.info(f"formatted_company_results: {formatted_company_results}")
            if formatted_company_results:
                companies.extend(formatted_company_results)
            logger.info(f"companies formatted: {companies}")
            # Step 3: Find leads for each company
            all_leads = []
            for company in companies:
                logger.info(f"company: {company}")
                logger.info(f"parsed['decision_makers']: {parsed['decision_makers']}")
                company_leads = await self._find_company_leads(company, parsed['decision_makers'])
                all_leads.extend(company_leads)
            
            return {
                "companies": list(companies),
                "leads": all_leads
            }
            
        except Exception as e:
            logger.error(f"Error in find_leads: {str(e)}", exc_info=True)
            raise

    async def _search_companies(self, search_params: List[Dict]) -> List[Dict]:
        """
        Search companies using the Companies API and analyze with GPT-4
        """
        try:
            # Call Companies API
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Basic {self.companies_api_key}'}
                url = 'https://api.thecompaniesapi.com/v2/companies/'
                params = {'query': json.dumps(search_params),
                        'page': 1,
                        'size': 3}

                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        print(f"Companies API error: {response.status}")
                        return []
                    companies_data = await response.json()
                    print(f"Found companies: {companies_data}")
            return companies_data
        
        except Exception as e:
            print(f"Error in _search_companies: {str(e)}")
            return []

    def _analyze_companies_data(self, companies_data: Dict, search_params: List[Dict]) -> List[Dict]:
        """
        Filter companies data based on search parameters
        """
        try:
            filtered_companies = []
            companies = companies_data.get('companies', [])
            
            for company in companies:
                matches_all_params = True
                company_attributes = {}
                
                for param in search_params:
                    attribute = param['attribute']
                    values = param['values']
                    sign = param['sign']
                    
                    # Get the actual value from nested company data
                    actual_value = None
                    attribute_parts = attribute.split('.')
                    current_obj = company
                    
                    for part in attribute_parts:
                        if isinstance(current_obj, dict):
                            current_obj = current_obj.get(part)
                        else:
                            current_obj = None
                            break
                    
                    actual_value = current_obj
                    
                    # Compare values
                    if actual_value is None:
                        matches_all_params = False
                        break
                        
                    if sign == 'equals':
                        if isinstance(actual_value, list):
                            if not any(val in actual_value for val in values):
                                matches_all_params = False
                                break
                        elif actual_value not in values:
                            matches_all_params = False
                            break
                    elif sign == 'notEquals':
                        if isinstance(actual_value, list):
                            if any(val in actual_value for val in values):
                                matches_all_params = False
                                break
                        elif actual_value in values:
                            matches_all_params = False
                            break
                    
                    # Store matched attribute
                    company_attributes[attribute] = actual_value
                
                if matches_all_params:
                    filtered_companies.append({
                        'name': company.get('about', {}).get('name', ''),
                        'website': company.get('domain', {}).get('domain', ''),
                        'attributes': company_attributes
                    })
            
            logger.info(f"Filtered {len(filtered_companies)} companies")
            return filtered_companies

        except Exception as e:
            logger.error(f"Error in _analyze_companies_data: {str(e)}", exc_info=True)
            return []

    async def get_email(self, employee_name: str, company_name: str) -> str:
        """
        Get the most probable email address for an employee using GPT
        """
        try:
            prompt = f"""
            Based on the company name and employee name, determine the most probable email address.
            
            Company: {company_name}
            Employee: {employee_name}
            
            Return only the email address, nothing else. Use the most common business email format.
            Example: john.doe@company.com
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at determining business email formats."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            email = response.choices[0].message.content.strip()
            return email
            
        except Exception as e:
            logger.error(f"Error getting email: {str(e)}")
            return ""

    async def _find_company_leads(self, company: Dict, decision_makers: List[str]) -> List[Dict]:
        """
        Find LinkedIn profiles and generate emails for each decision maker role
        """
        leads = []
        for role in decision_makers:
            profiles = await self.linkedin_scraper.search_profiles(
                company_name=company['name'],
                job_title=role,
                limit=2
            )
            
            for profile in profiles:
                # Get probable email address
                email = await self.get_email(profile['name'], company['name'])
                
                leads.append({
                    'name': profile['name'],
                    'linkedin_url': profile['profile_url'],
                    'company': company['name'],
                    'company_website': company['website'],
                    'company_attributes': company['attributes'],
                    'role': role,
                    'headline': profile.get('headline', ''),
                    'email': email
                })
        
        return leads

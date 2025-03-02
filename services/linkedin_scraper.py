from typing import List, Dict
import aiohttp
import os
from urllib.parse import quote
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

class LinkedInScraper:
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")
            
        self.google_cx = os.getenv('GOOGLE_CUSTOM_SEARCH_CX')
        if not self.google_cx:
            raise ValueError("GOOGLE_CUSTOM_SEARCH_CX environment variable is not set")
            
        self.search_url = "https://www.googleapis.com/customsearch/v1"

    async def search_profiles(self, company_name: str, job_title: str, limit: int = 2) -> List[Dict]:
        """
        Use Google Custom Search API to find LinkedIn profiles
        """
        search_query = f'site:linkedin.com/in/ "{company_name}" "{job_title}"'
        logger.info(f"Searching LinkedIn profiles with query: {search_query}")
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'api_key': os.getenv('SCRAPINGDOG_API_KEY'),
                    'query': search_query,
                    'results': limit,
                    "country": "us",
                    "page": 0,
                    "advanced_search": "false"
                }
                logger.info(f"Making ScrapingDog API request with params: {params}")

                async with session.get('https://api.scrapingdog.com/google', params=params) as response:
                    if response.status == 200:
                        logger.info("ScrapingDog API request successful")
                        data = await response.json()
                        logger.info(f"ScrapingDog API response: {data['organic_results']}")
                        return self._parse_google_results(data, company_name)
                    else:
                        logger.error(f"ScrapingDog SERP API request failed with status: {response.status}")
                        return []

        except Exception as e:
            logger.error(f"Error during ScrapingDog SERP API search: {str(e)}")
            return []

    def _parse_google_results(self, data: Dict, company_name: str) -> List[Dict]:
        """
        Parse Google Custom Search API results to extract LinkedIn profiles
        """
        profiles = []
        
        if 'organic_results' not in data:
            logger.info(f"No organic results found in ScrapingDog API response: {data}")
            return profiles

        for item in data['organic_results']:
            if 'linkedin.com/in/' in item['link']:
                # Extract name from title - Google API returns cleaner titles
                # Usually format: "First Last - Title at Company | LinkedIn"
                title_parts = item['title'].split(' - ')
                name = title_parts[0].strip()
                
                # Extract any additional info from snippet
                snippet = item.get('snippet', '')
                logger.info(f"Snippet: {snippet}")
                profile = {
                    'name': name,
                    'profile_url': item['link'],
                    'headline': title_parts[1].split(' | ')[0] if len(title_parts) > 1 else '',
                    'summary': snippet
                }
                # Only append if company name appears in the title
                if company_name.lower() in item['title'].lower():
                    profiles.append(profile)
        
        return profiles
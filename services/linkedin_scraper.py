from typing import List, Dict
import aiohttp
import os
from urllib.parse import quote
from dotenv import load_dotenv

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

    async def search_profiles(self, company_name: str, job_title: str, limit: int = 3) -> List[Dict]:
        """
        Use Google Custom Search API to find LinkedIn profiles
        """
        search_query = f'site:linkedin.com/in/ "{company_name}" "{job_title}"'
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'key': self.google_api_key,
                    'cx': self.google_cx,
                    'q': search_query,
                    'num': min(limit, 10)  # Google API allows max 10 results per query
                }
                
                async with session.get(self.search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_google_results(data)
                    else:
                        print(f"Google API request failed with status: {response.status}")
                        return []
                        
        except Exception as e:
            print(f"Error during Google API search: {str(e)}")
            return []

    def _parse_google_results(self, data: Dict) -> List[Dict]:
        """
        Parse Google Custom Search API results to extract LinkedIn profiles
        """
        profiles = []
        
        if 'items' not in data:
            return profiles

        for item in data['items']:
            if 'linkedin.com/in/' in item['link']:
                # Extract name from title - Google API returns cleaner titles
                # Usually format: "First Last - Title at Company | LinkedIn"
                title_parts = item['title'].split(' - ')
                name = title_parts[0].strip()
                
                # Extract any additional info from snippet
                snippet = item.get('snippet', '')
                
                profile = {
                    'name': name,
                    'profile_url': item['link'],
                    'headline': title_parts[1].split(' | ')[0] if len(title_parts) > 1 else '',
                    'summary': snippet
                }
                
                profiles.append(profile)
        
        return profiles
import os
import logging
from typing import List, Dict
import requests
import json
from openai import OpenAI
import aiohttp

logger = logging.getLogger(__name__)

class WebSearcher:
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.google_cse_id = os.getenv('GOOGLE_CSE_ID')
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        if not self.google_api_key or not self.google_cse_id:
            raise ValueError("GOOGLE_API_KEY and GOOGLE_CSE_ID must be set")

    async def search_and_analyze(self, search_query: str, company_attributes: List[str]) -> List[Dict]:
        """
        Perform Google search, scrape content, and analyze with GPT
        """
        try:
            # Perform Google search
            search_results = await self._google_search(search_query, num_results=1)
            logger.info(f"Search query: {search_query}")            
            logger.info(f"Search results: {search_results}")
            # Scrape content from search results
            scraped_content = []
            for result in search_results:
                content = self._scrape_webpage(result['link'])
                if content:
                    scraped_content.append({
                        'url': result['link'],
                        'content': content
                    })
            
            # Analyze content with GPT
            return self._analyze_with_gpt(scraped_content, company_attributes)
            
        except Exception as e:
            logger.error(f"Error in search_and_analyze: {str(e)}", exc_info=True)
            return []

    async def _google_search(self, query: str, num_results: int = 1) -> List[Dict]:
        """
        Perform Google Custom Search
        """
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'key': self.google_api_key,
                    'cx': self.google_cse_id,
                    'q': query,
                    'num': min(num_results, 1)  # Google API allows max 10 results per query
                }
                
                async with session.get("https://www.googleapis.com/customsearch/v1", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Google search results: {data}")
                        return [
                            {
                                'title': item.get('title', ''),
                                'link': item.get('link', ''),
                                'snippet': item.get('snippet', '')
                            }
                            for item in data.get('items', [])
                        ]
                    else:
                        logger.error(f"Google API request failed with status: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Google search error: {str(e)}")
            return []

    def _scrape_webpage(self, url: str) -> str:
        jina_url = f"https://r.jina.ai/{url}"
        try:
            response = requests.get(jina_url)
            response.raise_for_status()
            return response.text
            
        except Exception as e:
            logger.error(f"Scraping error for {url}: {str(e)}")
            return ""

    def _analyze_with_gpt(self, scraped_content: List[Dict], company_attributes: List[str]) -> List[Dict]:
        """
        Analyze scraped content with GPT to extract company information
        """
        try:
            content_text = "\n\n".join([
                f"Content from {item['url']}:\n{item['content']}"
                for item in scraped_content
            ])
            
            prompt = f"""
            Analyze the following content and extract information about companies mentioned.
            Focus on these attributes: {', '.join(company_attributes)}
            
            For each company, determine their email format by looking for patterns or contact information.
            Use these specific format strings:
            - "first.last@domain.com"
            - "firstlast@domain.com" 
            - "flast@domain.com"
            - "first@domain.com"
            - "first-last@domain.com"
            - "first_last@domain.com"
            
            Content:
            {content_text}
            
            Respond with a JSON array of company objects. Each object should include:
            - name: company name
            - website: company website (domain only, no http/www)
            - email_format: EXACT format string from the list above
            - attributes: object containing the requested company attributes
            
            Example format:
            [
                {{
                    "name": "TechCorp AI",
                    "website": "techcorp.ai",
                    "email_format": "{{first}}.{{last}}@domain.com",
                    "attributes": {{
                        "industry": "Artificial Intelligence",
                        "location": "San Francisco",
                        "employee_count": "150",
                        "funding_stage": "Series A"
                    }}
                }}
            ]
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that analyzes company information and always responds with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            result = response.choices[0].message.content
            
            try:
                companies = json.loads(result)
                if not isinstance(companies, list):
                    logger.error("GPT response is not a list")
                    return []
                    
                return companies
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse GPT response: {e}")
                return []
                
        except Exception as e:
            logger.error(f"GPT analysis error: {str(e)}")
            return [] 
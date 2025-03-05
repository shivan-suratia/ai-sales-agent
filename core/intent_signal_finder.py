from typing import List, Dict
import os
import json
import logging
from openai import AsyncOpenAI
import aiohttp
from google.generativeai import GenerativeModel
import google.generativeai as genai
import re
import anthropic
import asyncio
from services.linkedin_scraper import LinkedInScraper

logger = logging.getLogger(__name__)

class IntentSignalFinder:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        genai.configure(api_key=os.getenv('GOOGLE_GEMINI_API_KEY'))
        self.gemini_model = GenerativeModel('gemini-2.0-flash')
        self.serp_api_key = os.getenv('SERP_API_KEY')
        self.signals_to_track = None
        self.user_input = None
        self.linkedin_scraper = LinkedInScraper()
        
    def _clean_json_string(self, response) -> str:
        """Clean JSON string from Claude's response"""
        try:
            # Get the text content from the response
            if isinstance(response, str):
                content = response
            else:
                content = response.content[0].text
            
            # Remove any leading/trailing whitespace
            content = content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```json'):
                content = re.sub(r'^```json\n', '', content)
                content = re.sub(r'\n```$', '', content)
                content = content.strip()
            elif content.startswith('```'):
                content = re.sub(r'^```\n', '', content)
                content = re.sub(r'\n```$', '', content)
                content = content.strip()
            
            # Debug logging
            logger.debug(f"Cleaned content (first 500 chars): {content[:500]}...")
            
            # Validate JSON
            try:
                json.loads(content)
                return content
            except json.JSONDecodeError as e:
                logger.error(f"JSON validation failed: {str(e)}")
                logger.error(f"Invalid JSON content: {content}")
                raise
                
        except Exception as e:
            logger.error(f"Error in _clean_json_string: {str(e)}")
            logger.error(f"Original response: {response}")
            raise
        
    async def generate_intent_signals(self, user_input: str) -> Dict:
        """Generate intent signals and search queries using Claude"""
        try:
            logger.info(f"Generating intent signals for input: {user_input}")
            
            client = anthropic.AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            response = await client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                system="You are a B2B sales intelligence analyst. Your responses must be valid JSON without any markdown formatting or additional text.",
                messages=[{
                    "role": "user", 
                    "content": f"""
                    
                    The user is looking for B2B singals that show intent to buy.
                    You are looking for websites that have content that contains companies or individuals that match the user query. 
                    First, break down the user query into intent components. Then, generate a list of signal categories that are relevant to the user query. 
                    You can use 2-5 signal categories, depending on how specific or broad the user query is.
                    Then, map out sources of information that are relevant to the user query.
                    Then, generate a list of SERP API search queries that are relevant to the user query.  
                    Use a mix of broad and specific search operators to gather a breadth of information. 

                    If the user query is looking for broad signals, you should use the following signal categories as a reference:
                    - Direct buying intent
                    - Company activity
                    - Industry trends
                    - Funding rounds
                    - Hiring signals
                    - Partnerships
                    - Changes in leadership 
                    - New product launches

                    Generate a JSON response with the following structure:

                    {{
                        "intent_components": {{
                            "primary_focus": string,
                            "industry": string,
                            "company_type": string
                        }},
                        "signal_categories": {{
                            category_name: [list of specific signals]
                        }},
                        "source_mapping": {{
                            source_type: [list of sources]
                        }},
                        "query_components": {{
                            component_type: [list of terms]
                        }},
                        "search_queries": [
                            {{
                                "query": string,
                                "signal_category": string,
                                "purpose": string,
                                "source_type": string
                            }}
                        ]
                    }}

                    Analyze this intent signal request and fill the structure above:
                    {user_input}

                    Requirements:
                    1. Response must be pure JSON (no markdown)
                    2. Include 2 search queries, depending on how specific or broad the user query is.
                    3. Use advanced search operators in queries
                    4. Ensure all queries are well-formed for SERP API
                    5. Do not search for youtube videos or pdfs
                    6. Do not include inurl in search queries
                    7. The first search query should be the user intent signal request
                    8. Do not use any time filters in search queries ("this month", "this year", "this week", "this day")
                    """
                }]
            )
            
            logger.info("Received response from Claude")
            cleaned_content = self._clean_json_string(response)
            result = json.loads(cleaned_content)
            
            # Validate response structure
            required_keys = ['intent_components', 'signal_categories', 'source_mapping', 'query_components', 'search_queries']
            missing_keys = [key for key in required_keys if key not in result]
            if missing_keys:
                raise ValueError(f"Missing required keys in response: {missing_keys}")
            
            logger.info(f"Successfully generated intent signals with {len(result['search_queries'])} queries")
            logger.info(f"Generated intent signal search data: {json.dumps(result, indent=2)}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating intent signals: {str(e)}")
            raise

    async def search_pages(self, queries: List[str], num_pages: int = 2, tbs: str = "qdr:m3") -> List[Dict]:
        """Search using SERP API and get page contents"""
        logger.info(f"Starting page search for {len(queries)} queries")
        results = []
        
        async with aiohttp.ClientSession() as session:
            # for i, query in enumerate(queries, 1):
            for i, query in enumerate(queries[:2], 1):
                try:
                    logger.info(f"Processing query {i}/{len(queries)}: {query.get('query', '')}")
                    
                    params = {
                        "api_key": os.getenv('SCRAPINGDOG_API_KEY'),
                        "query": query['query'],
                        "results": num_pages,
                        "country": "us",
                        "cr": "countryUS",
                        "tbs": tbs,
                        "page": 0,
                        "advanced_search": "false"
                    }
                    
                    async with session.get('https://api.scrapingdog.com/google', params=params) as response:
                        if response.status == 200:
                            serp_data = await response.json()
                            logger.info(f"SERP results for query {i}: {len(serp_data.get('organic_results', []))} results")
                            
                            for j, result in enumerate(serp_data.get('organic_results', [])[:num_pages], 1):
                                link = result.get('link')
                                if link:
                                    logger.info(f"Scraping content from {link}")
                                    try:
                                        jina_url = f"https://r.jina.ai/{link}"
                                        async with session.get(jina_url) as jina_response:
                                            if jina_response.status == 200:
                                                page_content = await jina_response.text()
                                                results.append({
                                                    'url': link,
                                                    'content': page_content[:5000] + "..."  # Log preview
                                                })
                                                logger.info(f"Successfully scraped content from {link}")
                                    except Exception as e:
                                        logger.error(f"Error scraping {link}: {str(e)}")
                                        continue
                except Exception as e:
                    logger.error(f"Error searching query {query['query']}: {str(e)}")
                    continue
                    
        logger.info(f"Completed page search. Found {len(results)} pages")
        return results

    async def get_decision_makers(self, company_name: str, user_input: str) -> List[str]:
        """Determine relevant decision maker roles based on company and user input"""
        try:
            prompt = f"""
            Based on the following information, determine the most relevant decision maker job titles:
            
            Company: {company_name}
            User Query/Need: {user_input}
            
            Return a JSON array of 1-3 job titles (1 for small startups, 2-3 for larger companies).
            Format your response as valid JSON only, no other text:
            ["Job Title 1", "Job Title 2", "Job Title 3"]
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at B2B sales and understanding organizational decision-making structures."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            # Clean and parse the response
            content = response.choices[0].message.content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            logger.debug(f"Cleaned decision makers response: {content}")
            
            roles = json.loads(content)
            logger.info(f"Generated decision maker roles for {company_name}: {roles}")
            return [roles[0]] if roles else []
            
        except Exception as e:
            logger.error(f"Error getting decision makers: {str(e)}")
            logger.error(f"Raw response: {response.choices[0].message.content if 'response' in locals() else 'No response'}")
            return []
        
    

    async def discover_company_email_formats(self, company_name: str) -> List[str]:
        """Find common email formats used by a company through web search and analysis"""
        try:
            logger.info(f"Discovering email formats for company: {company_name}")
            
            # Search for email format information
            logger.debug("Initializing aiohttp session for email format discovery")
            async with aiohttp.ClientSession() as session:
                params = {
                    "api_key": os.getenv('SCRAPINGDOG_API_KEY'),
                    "query": f"company email format for \"{company_name}\" (SignalHire OR LeadIQ OR RocketReach)",
                    "results": 2,
                    "country": "us",
                    "page": 0,
                    "advanced_search": "false"
                }
                
                logger.debug(f"ScrapingDog search parameters: {params}")
                email_formats = []
                scraped_content = []
                
                async with session.get('https://api.scrapingdog.com/google', params=params) as response:
                    logger.debug(f"ScrapingDog API response status: {response.status}")
                    if response.status == 200:
                        logger.debug("ScrapingDog API request successful")
                        serp_data = await response.json()
                        logger.debug(f"Found {len(serp_data.get('organic_results', []))} search results")
                        
                        # Scrape content from top 3 results
                        for result in serp_data.get('organic_results', [])[:3]:
                            link = result.get('link')
                            if link:
                                try:
                                    logger.debug(f"Attempting to scrape content from: {link}")
                                    # Scrape content using jina.ai
                                    jina_url = f"https://r.jina.ai/{link}"
                                    async with session.get(jina_url) as jina_response:
                                        if jina_response.status == 200:
                                            logger.debug(f"Successfully scraped content from {link}")
                                            content = await jina_response.text()
                                            scraped_content.append({
                                                "url": link,
                                                "content": content[:500000]  # Limit content length
                                            })
                                except Exception as e:
                                    logger.error(f"Error scraping content from {link}: {str(e)}")
                                    continue
                        
                        # Analyze all scraped content together with Gemini
                        if scraped_content:
                            logger.info(f"Analyzing {len(scraped_content)} scraped pages with Gemini")
                            # First get the domain
                            domain_prompt = f"""
                            Analyze these web pages and identify the primary email domain used by {company_name}.
                            Return only the domain as plain text (e.g. "company.com"), no other text or formatting.

                            Content to analyze:
                            {json.dumps(scraped_content, indent=2)}
                            """
                            
                            logger.debug("Requesting domain analysis from Gemini")
                            domain_response = self.gemini_model.generate_content(domain_prompt)
                            company_domain = domain_response.text.strip()
                            logger.info(f"Discovered company domain: {company_domain}")
                            
                            # Then get the email formats using the discovered domain
                            prompt = f"""
                            Analyze these web pages and identify the email format(s) used by {company_name}.
                            
                            Scraped content:
                            {json.dumps(scraped_content, indent=2)}
                            
                            Return a JSON array of the most common email formats, using these placeholders:
                            - {'{first}'} for first name
                            - {'{last}'} for last name
                            - {'{f}'} for first initial
                            - {'{l}'} for last initial
                            
                            Replace company.com with the domain you discovered.
                            
                            Example formats:
                            [
                                "{'{first}'}.{'{last}'}@company.com",
                                "{'{first}'}-{'{last}'}@company.com",
                                "{'{first}'}{'{last}'}@company.com",
                                "{'{f}'}{'{last}'}@company.com",
                                "{'{first}'}{'{l}'}@company.com",
                                "{'{f}'}.{'{last}'}@company.com",
                                "{'{first}'}_{'{last}'}@company.com"
                            ]
                            
                            Return only the JSON array, no other text.
                            """
                            
                            logger.debug("Requesting email format analysis from Gemini")
                            response = self.gemini_model.generate_content(prompt)
                            if response.text:
                                # Clean and parse the response
                                logger.debug("Cleaning Gemini response")
                                text = response.text.strip()
                                if text.startswith('```json'):
                                    text = text[7:]
                                if text.startswith('```'):
                                    text = text[3:]
                                if text.endswith('```'):
                                    text = text[:-3]
                                text = text.strip()
                                
                                email_formats = json.loads(text)
                                logger.debug(f"Parsed email formats: {email_formats}")
                
                # Remove duplicates while preserving order
                unique_formats = list(dict.fromkeys(email_formats))
                logger.info(f"Discovered email formats for {company_name}: {unique_formats}")
                return unique_formats[:3]  # Return top 3 unique formats
                
        except Exception as e:
            logger.error(f"Error discovering email formats: {str(e)}", exc_info=True)
            # Return default formats if discovery fails
            default_formats = [
                "{first}.{last}@{domain}",
                "{f}{last}@{domain}",
                "{first}{l}@{domain}"
            ]
            logger.info(f"Using default email formats: {default_formats}")
            return default_formats

    def generate_employee_emails(self, employee_name: str, email_formats: List[str]) -> List[str]:
        """Generate possible email addresses for an employee based on discovered formats"""
        try:
            logger.info(f"Generating emails for {employee_name} ")
            
            # Split name into components
            name_parts = employee_name.lower().split()
            if len(name_parts) < 2:
                logger.error(f"Invalid name format: {employee_name}")
                return []
            
            first_name = name_parts[0]
            last_name = name_parts[-1]
            first_initial = first_name[0] if first_name else ''
            last_initial = last_name[0] if last_name else ''
            
            # Generate emails based on formats
            emails = []
            for fmt in email_formats:
                try:
                    email = fmt.replace('{first}', first_name)\
                             .replace('{last}', last_name)\
                             .replace('{f}', first_initial)\
                             .replace('{l}', last_initial)
                    emails.append(email)
                except Exception as e:
                    logger.error(f"Error generating email with format {fmt}: {str(e)}")
                    continue
            
            logger.info(f"Generated emails: {emails}")
            return emails
            
        except Exception as e:
            logger.error(f"Error generating employee emails: {str(e)}")
            return []

    async def get_email(self, employee_name: str, company_name: str) -> str:
        """Get the most probable email address for an employee using discovered formats"""
        return ""
        try:
            # Extract domain from company name (you might want to enhance this)
            company_name = company_name.lower()
            
            # Check cached email formats
            if not hasattr(self, '_company_email_formats'):
                self._company_email_formats = {}
                
            if company_name in self._company_email_formats:
                logger.info(f"Using cached email formats for {company_name}")
                email_formats = self._company_email_formats[company_name]
            else:
                # Discover email formats
                email_formats = await self.discover_company_email_formats(company_name)
                self._company_email_formats[company_name] = email_formats
            
            # Generate possible emails
            possible_emails = self.generate_employee_emails(employee_name, email_formats)
            
            # Return the most likely email (first format)
            return possible_emails[0] if possible_emails else ""
            
        except Exception as e:
            logger.error(f"Error getting email: {str(e)}")
            return ""

    async def find_company_contacts(self, company: Dict, user_input: str) -> List[Dict]:
        """Find decision makers and their contact information for a company"""
        try:            
            # Get relevant decision maker roles
            roles = await self.get_decision_makers(company["company"], user_input)
            
            contacts = []
            for role in roles:
                # Search for LinkedIn profiles
                profiles = await self.linkedin_scraper.search_profiles(
                    company_name=company["company"],
                    job_title=role,
                    limit=2
                )
                
                for profile in profiles:
                    # Get email
                    email = await self.get_email(profile["name"], company["company"])

                    # Set job title based on headline or role
                    job_title = profile.get("headline") if profile.get("headline") != company["company"] else ""
                    
                    # Create contact entry
                    contact = {
                        "name": profile["name"],
                        "linkedin_url": profile["profile_url"],
                        "job_title": job_title,
                        "role": role,
                        "headline": profile.get("headline", ""),
                        "email": email,
                        "company": company["company"],
                        "signals": company["signals"],
                        "reasoning": company["reasoning"],
                        "url": company["url"]
                    }
                    contacts.append(contact)
            
            return contacts
            
        except Exception as e:
            logger.error(f"Error finding company contacts: {str(e)}")
            return []

    async def analyze_intent_signals(self, pages: List[Dict], user_input: str) -> List[Dict]:
        """Analyze pages for intent signals and find relevant contacts"""
        logger.info(f"Starting intent signal analysis for {len(pages)} pages")
        
        async def analyze_single_page(page: Dict, index: int) -> Dict:
            try:
                logger.info(f"Analyzing page {index}/{len(pages)}: {page['url']}")
                
                prompt = f"""Analyze this webpage content and identify relevant intent signals from high-quality leads only.
                You are a B2B sales intelligence analyst. The client wants to find companies (leads) that match their user query.
                Your job is to look through the content and identify signals of companies that would be strong potential customers.

                Only include companies that meet these criteria:
                - Must be actively operating businesses (not defunct or acquired)
                - Must show clear signs of being in the target market for the user's query
                - Must have recent activity or updates (within last 2 years)
                - Must be of appropriate company size/scale (no massive enterprises unless specifically requested)
                - Must demonstrate actual buying intent or pain points, not just general industry presence
                
                Content: {page['content'][:500000]}
                URL: {page['url']}
                User Query: {user_input}
                
                Return a JSON with found signals. Do not repeat companies. If you find multiple signals for the same company, only include the company once, you can include multiple signals in the signals array.
                
                For each company, carefully validate:
                1. Is this truly a good potential customer for the query?
                2. Are the signals strong indicators of buying intent?
                3. Is there enough context to qualify this as a real lead?
                
                If you're unsure about a company, exclude it. It's better to return fewer, higher-quality leads.
                
                Format your response as valid JSON only, no other text:
                {{
                    "url": "{page['url']}",
                    "intent_signals": [
                        {{
                            "company": "company name",
                            "signals": ["specific buying intent signal", "pain point identified", "relevant activity", ...etc],
                            "reasoning": "detailed explanation of why this company would be a strong lead, including evidence of fit and intent",
                            "url": "{page['url']}"
                        }}
                    ]
                }}
                """
                
                response = self.gemini_model.generate_content(prompt)
                if response.text:
                    # Clean the response
                    text = response.text.strip()
                    if text.startswith('```json'):
                        text = text[7:]
                    if text.startswith('```'):
                        text = text[3:]
                    if text.endswith('```'):
                        text = text[:-3]
                    text = text.strip()
                    
                    result = json.loads(text)
                    if result.get('intent_signals'):
                        logger.info(f"Found {len(result['intent_signals'])} signals on {page['url']}")
                        return result
                    
            except Exception as e:
                logger.error(f"Error analyzing page {page['url']}: {str(e)}")
                return None
        
        # Analyze all pages concurrently
        tasks = [analyze_single_page(page, i+1) for i, page in enumerate(pages)]
        results = await asyncio.gather(*tasks)
        
        # Filter out None results and empty results
        valid_results = [result for result in results if result and result.get('intent_signals')]
        
        # Extract all companies with their signals
        companies = []
        for result in valid_results:
            companies.extend(result['intent_signals'])
        
        # Find contacts for each company
        all_contacts = []
        for company in companies:
            contacts = await self.find_company_contacts(company, user_input)
            all_contacts.extend(contacts)
        
        logger.info(f"Found {len(all_contacts)} contacts across {len(companies)} companies")
        return all_contacts
    
    async def repeat_search(self, user_input: str = None) -> Dict:
        try:
            pages = await self.search_pages(self.signals_to_track['search_queries'], tbs="qdr:d1")
            contacts = await self.analyze_intent_signals(pages, user_input)
            

            return contacts

        except Exception as e:
            logger.error(f"Error in repeat_search: {str(e)}")
            raise


    async def find_intent_signals(self, user_input: str = None) -> Dict:
        """Main method to find intent signals and contacts"""
        try:
            if user_input:
                logger.info(f"Starting new intent signal search for: {user_input}")
                self.user_input = user_input
                signals_data = await self.generate_intent_signals(user_input)
                logger.info("Generated new signals and queries")
            elif self.signals_to_track:
                logger.info(f"Starting tracked intent signal search for: {self.user_input}")
                signals_data = self.signals_to_track
                logger.info("Using tracked signals and queries")
            else:
                raise ValueError("Either user_input or signals_to_track must be provided")
            
            # Search pages
            if self.user_input:
                pages = await self.search_pages(signals_data['search_queries'], tbs="qdr:m3")
            else:
                pages = await self.search_pages(signals_data['search_queries'], tbs="qdr:d")
            logger.info(f"Searched {len(pages)} pages")
            
            # Analyze pages and find contacts
            contacts = await self.analyze_intent_signals(pages, self.user_input)
            logger.info(f"Found {len(contacts)} contacts")
            
            # Track successful queries
            successful_queries = []
            successful_urls = {contact['url'] for contact in contacts}
            
            for query in signals_data['search_queries']:
                # Check if any contacts were found from pages resulting from this query
                for page in pages:
                    if page['url'] in successful_urls:
                        successful_queries.append(query['query'])
                        break
            
            # Update signals_to_track with successful queries
            filtered_signals_data = signals_data.copy()
            filtered_signals_data['search_queries'] = successful_queries
            self.signals_to_track = filtered_signals_data
            
            logger.info("Query tracking statistics:")
            logger.info(f"Total original queries: {len(signals_data['search_queries'])}")
            logger.info(f"Successful queries: {len(successful_queries)}")
            logger.info("Successful queries list:")
            for query in successful_queries:
                logger.info(f"Query: {query}")
            
            final_result = {
                "intent_signals": signals_data['signal_categories'],
                "successful_queries": successful_queries,  # Return only successful queries
                "contacts": contacts
            }
            
            return final_result
            
        except Exception as e:
            logger.error(f"Error in find_intent_signals: {str(e)}")
            raise

import pytest
import json
import os
from unittest.mock import Mock, patch, AsyncMock
from core.intent_signal_finder import IntentSignalFinder
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Sample test data
SAMPLE_USER_INPUT = "Find companies in the healthcare industry looking to implement AI solutions"

SAMPLE_INTENT_SIGNALS_RESPONSE = {
    "intent_components": {
        "primary_focus": "AI implementation intentions",
        "industry": "Healthcare",
        "company_type": "Healthcare providers and organizations"
    },
    "signal_categories": {
        "hiring": [
            "AI/ML engineering positions",
            "Data science roles",
            "Digital transformation leads"
        ],
        "technology_investment": [
            "AI platform acquisitions",
            "Digital infrastructure upgrades",
            "Cloud computing initiatives"
        ],
        "content_engagement": [
            "AI healthcare whitepapers",
            "Digital transformation case studies",
            "Innovation reports"
        ]
    },
    "source_mapping": {
        "job_boards": ["LinkedIn", "Indeed", "Company careers pages"],
        "news_sources": ["Healthcare IT News", "Press releases", "Industry blogs"],
        "professional_networks": ["Conference presentations", "Industry forums", "LinkedIn posts"]
    },
    "query_components": {
        "base_terms": ["healthcare", "hospital", "medical center"],
        "technology_terms": ["artificial intelligence", "machine learning", "AI implementation"],
        "intent_indicators": ["hiring", "implementing", "partnership", "initiative"]
    },
    "search_queries": [
        {
            "query": "site:linkedin.com/jobs (healthcare OR hospital) (\"AI engineer\" OR \"machine learning engineer\")",
            "signal_category": "hiring",
            "purpose": "Find AI-related job postings in healthcare",
            "source_type": "job_board"
        },
        {
            "query": "healthcare provider (\"AI implementation\" OR \"AI transformation\") case study",
            "signal_category": "content_engagement",
            "purpose": "Find healthcare organizations documenting AI initiatives",
            "source_type": "case_study"
        }
    ]
}

SAMPLE_SERP_RESPONSE = {
    "organic_results": [
        {
            "link": "https://example.com/healthcare-ai-news",
            "title": "Healthcare Company Implements AI Solution"
        },
        {
            "link": "https://example.com/medical-tech-news",
            "title": "Hospital Announces AI Partnership"
        }
    ]
}

SAMPLE_FIRECRAWL_RESPONSE = {
    "content": """
    HealthTech Inc. announced today a major initiative to implement artificial intelligence 
    solutions across their hospital network. The company is actively hiring AI engineers 
    and data scientists to support this digital transformation effort.
    """
}

SAMPLE_GEMINI_RESPONSE = {
    "company": "HealthTech Inc",
    "url": "https://example.com/healthcare-ai-news",
    "intent_signals": [
        {
            "signal": "Job postings for AI/ML engineers in healthcare",
            "context": "actively hiring AI engineers and data scientists"
        },
        {
            "signal": "Digital transformation initiatives in healthcare",
            "context": "major initiative to implement artificial intelligence solutions"
        }
    ]
}

@pytest.fixture
def intent_finder():
    # Ensure environment variables are loaded from .env
    if not all(key in os.environ for key in ['ANTHROPIC_API_KEY']):
        raise EnvironmentError("Missing required API keys in .env file. Please ensure all required API keys are set.")
    return IntentSignalFinder()

def test_clean_json_string(intent_finder):
    # Test with markdown formatting
    markdown_json = """```json
{
  "test": "value"
}
```"""
    cleaned = intent_finder._clean_json_string(markdown_json)
    assert cleaned == '{\n  "test": "value"\n}'
    
    # Test without markdown formatting
    plain_json = '{"test": "value"}'
    cleaned = intent_finder._clean_json_string(plain_json)
    assert cleaned == '{"test": "value"}'

@pytest.mark.asyncio
async def test_generate_intent_signals(intent_finder):
    """Test the generate_intent_signals method with a real API call"""
    try:
        print("\nMaking real API call to Claude...")
        print(f"\nInput Query: {SAMPLE_USER_INPUT}")
        
        result = await intent_finder.generate_intent_signals(SAMPLE_USER_INPUT)
        
        print("\nRaw Response Structure:")
        for key in result.keys():
            print(f"\n{key}:")
            print(json.dumps(result[key], indent=2))
        
        # Basic structure verification
        assert isinstance(result, dict), "Response should be a dictionary"
        assert 'intent_components' in result, "Response should have intent_components"
        assert 'signal_categories' in result, "Response should have signal_categories"
        assert 'source_mapping' in result, "Response should have source_mapping"
        assert 'query_components' in result, "Response should have query_components"
        assert 'search_queries' in result, "Response should have search_queries"
        
        # Print some statistics
        print("\nResponse Statistics:")
        print(f"Number of signal categories: {len(result['signal_categories'])}")
        print(f"Number of search queries: {len(result['search_queries'])}")
        
        # Verify search queries structure
        for i, query in enumerate(result['search_queries']):
            assert 'query' in query, f"Search query {i} missing 'query' field"
            assert 'signal_category' in query, f"Search query {i} missing 'signal_category' field"
            assert 'purpose' in query, f"Search query {i} missing 'purpose' field"
            assert 'source_type' in query, f"Search query {i} missing 'source_type' field"
        
        print("\nExample Search Queries:")
        for i, query in enumerate(result['search_queries'][:3]):  # Print first 3 queries
            print(f"\nQuery {i+1}:")
            print(f"Category: {query['signal_category']}")
            print(f"Query: {query['query']}")
            print(f"Purpose: {query['purpose']}")
            print(f"Source: {query['source_type']}")
        
        return result
        
    except Exception as e:
        print(f"\nError during test: {str(e)}")
        print("\nFull error details:")
        import traceback
        traceback.print_exc()
        raise

@pytest.mark.asyncio
async def test_search_pages(intent_finder):
    with patch('aiohttp.ClientSession.get') as mock_get:
        # Mock SERP API response
        mock_serp_response = Mock()
        mock_serp_response.status = 200
        mock_serp_response.json = AsyncMock(return_value=SAMPLE_SERP_RESPONSE)
        
        # Mock Firecrawl response
        mock_firecrawl_response = Mock()
        mock_firecrawl_response.status = 200
        mock_firecrawl_response.json = AsyncMock(return_value=SAMPLE_FIRECRAWL_RESPONSE)
        
        # Set up mock to return different responses for SERP and Firecrawl
        mock_get.side_effect = [mock_serp_response, mock_firecrawl_response]
        
        result = await intent_finder.search_pages(["healthcare AI implementation"], num_pages=1)
        
        assert len(result) > 0
        assert 'query' in result[0]
        assert 'url' in result[0]
        assert 'content' in result[0]

@pytest.mark.asyncio
async def test_analyze_intent_signals(intent_finder):
    mock_response = Mock()
    mock_response.text = json.dumps(SAMPLE_GEMINI_RESPONSE)
    
    mock_model = Mock()
    mock_model.generate_content = AsyncMock(return_value=mock_response)
    
    with patch('google.generativeai.GenerativeModel', return_value=mock_model):
        test_pages = [{
            'url': 'https://example.com/healthcare-ai-news',
            'content': SAMPLE_FIRECRAWL_RESPONSE['content']
        }]
        
        test_signals = SAMPLE_INTENT_SIGNALS_RESPONSE['intent_signals']
        
        result = await intent_finder.analyze_intent_signals(test_pages, test_signals)
        
        assert len(result) > 0
        assert 'company' in result[0]
        assert 'url' in result[0]
        assert 'intent_signals' in result[0]
        assert len(result[0]['intent_signals']) > 0

@pytest.mark.asyncio
async def test_find_intent_signals_integration(intent_finder):
    # Mock all external API calls
    with patch('core.intent_signal_finder.IntentSignalFinder.generate_intent_signals') as mock_generate, \
         patch('core.intent_signal_finder.IntentSignalFinder.search_pages') as mock_search, \
         patch('core.intent_signal_finder.IntentSignalFinder.analyze_intent_signals') as mock_analyze:
        
        # Set up mock returns
        mock_generate.return_value = SAMPLE_INTENT_SIGNALS_RESPONSE
        mock_search.return_value = [{
            'url': 'https://example.com/healthcare-ai-news',
            'content': SAMPLE_FIRECRAWL_RESPONSE['content']
        }]
        mock_analyze.return_value = [SAMPLE_GEMINI_RESPONSE]
        
        result = await intent_finder.find_intent_signals(SAMPLE_USER_INPUT)
        
        assert 'intent_signals' in result
        assert 'results' in result
        assert len(result['results']) > 0
        
        # Verify all methods were called
        mock_generate.assert_called_once_with(SAMPLE_USER_INPUT)
        mock_search.assert_called_once()
        mock_analyze.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling(intent_finder):
    # Test error handling in generate_intent_signals
    mock_completions = AsyncMock()
    mock_completions.create = AsyncMock(side_effect=Exception("API Error"))
    
    mock_chat = Mock()
    mock_chat.completions = mock_completions
    
    mock_client = Mock()
    mock_client.chat = mock_chat
    
    with patch('openai.AsyncOpenAI', return_value=mock_client):
        with pytest.raises(Exception):
            await intent_finder.generate_intent_signals(SAMPLE_USER_INPUT)
    
    # Test error handling in search_pages
    with patch('aiohttp.ClientSession.get', side_effect=Exception("Network Error")):
        result = await intent_finder.search_pages(["test query"])
        assert len(result) == 0  # Should return empty list on error
    
    # Test error handling in analyze_intent_signals
    mock_model = Mock()
    mock_model.generate_content = AsyncMock(side_effect=Exception("API Error"))
    
    with patch('google.generativeai.GenerativeModel', return_value=mock_model):
        result = await intent_finder.analyze_intent_signals([{'url': 'test', 'content': 'test'}], ["test signal"])
        assert len(result) == 0  # Should return empty list on error 
# 🧠 AI B2B Lead Finder – Backend

This is the backend service for the **AI B2B Lead Finder**, an intelligent B2B prospecting agent. The system identifies high-intent companies and decision-makers based on natural language queries and delivers enriched lead data for outbound sales.

## 🚀 Features

- Accepts natural language queries like *"Find pharma companies investing in AI"*
- Scrapes and analyzes resulting webpages for buyer intent signals
- Identifies relevant companies and decision-makers
- Enriches contacts via scraping/data enrichment APIs
- Delivers structured lead data to the frontend
- Continuously updates active queries with new leads

## 🛠️ Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL
- **Deployment:** Railway
- **Async:** `asyncio` + `httpx` for concurrent web scraping and enrichment
- **Data Parsing:** BeautifulSoup / lxml
- **Search & Enrichment APIs:** SERP API, X-ray search, enrichment platforms

## 📦 API Endpoints

### `POST /query`
Submits a new natural language query.
```json
{
  "query": "Find healthcare startups hiring data scientists"
}
```

### `GET /leads?query_id={id}`
Returns the leads found for a particular query.

### `POST /refresh`
Triggers a re-crawl and enrichment for all active queries.

## 📂 Project Structure

```
.
├── app/
│   ├── main.py          # FastAPI app entry point
│   ├── models.py        # Pydantic and DB models
│   ├── routers/
│   │   └── leads.py     # API endpoints
│   ├── services/
│   │   ├── serp.py      # SERP query generation
│   │   ├── scraper.py   # Web scraper and analyzer
│   │   └── enrich.py    # Data enrichment logic
├── db/
│   ├── database.py      # PostgreSQL connection
│   └── schema.sql       # DB schema
├── requirements.txt
└── README.md
```

## 🧪 Running Locally

1. **Clone the repo**
   ```bash
   git clone https://github.com/yourusername/ai-b2b-lead-finder.git
   cd ai-b2b-lead-finder
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   Create a `.env` file with your API keys:
   ```
   SERP_API_KEY=your_serp_api_key
   DATABASE_URL=postgresql://user:pass@localhost/dbname
   ```

4. **Run the server**
   ```bash
   uvicorn app.main:app --reload
   ```

## 📈 Future Improvements

- NLP-based query refinement
- Advanced lead scoring model


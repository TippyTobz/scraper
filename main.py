import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scraper import HiringCafeProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="HiringCafe Scraper Test", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "ok", "message": "HiringCafe Scraper API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/scrape")
async def scrape_jobs(role: str = "Software Engineer", limit: int = 20):
    """
    Scrape jobs from hiring.cafe

    Query params:
    - role: Job role to search for (default: Software Engineer)
    - limit: Number of jobs to return (default: 20)
    """
    provider = HiringCafeProvider()
    try:
        jobs = await provider.search(role=role, limit=limit)
        return {
            "success": True,
            "count": len(jobs),
            "jobs": [
                {
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "apply_url": job.apply_url,
                }
                for job in jobs
            ]
        }
    except Exception as e:
        logging.error(f"Scraping failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "jobs": []
        }

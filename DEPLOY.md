# Railway Deployment Guide

## Files Created
- `base.py` - Base classes for job providers
- `scraper.py` - HiringCafe scraper (updated to use local imports)
- `main.py` - FastAPI app with scraper endpoint
- `requirements.txt` - Python dependencies
- `Dockerfile` - Docker configuration with Chrome support
- `.dockerignore` - Files to exclude from Docker build

## Test Locally First (Optional)

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload

# Test the scraper
curl "http://localhost:8000/scrape?role=Software%20Engineer&limit=5"
```

## Deploy to Railway

### 1. Sign Up
- Go to https://railway.app
- Sign up (get $5 free credits, no credit card required initially)

### 2. Create New Project
- Click "New Project"
- Choose "Deploy from GitHub repo"
- Authorize Railway to access your GitHub
- Create a new repo for this folder or push to existing repo

### 3. Configure Deployment
Railway will auto-detect the Dockerfile. No additional config needed!

### 4. Deploy
- Railway will automatically build and deploy
- You'll get a URL like: `https://your-app.railway.app`

### 5. View Logs
- Click on your deployment
- Go to "Deployments" tab
- Click on the latest deployment
- Click "View Logs" to see scraper output and any errors

### 6. Test Your Deployment

```bash
# Health check
curl https://your-app.railway.app/health

# Test scraper
curl "https://your-app.railway.app/scrape?role=Software%20Engineer&limit=5"
```

## API Endpoints

- `GET /` - Root endpoint (status check)
- `GET /health` - Health check
- `GET /scrape?role=<job_role>&limit=<number>` - Scrape jobs
  - `role` (optional): Job title to search for (default: "Software Engineer")
  - `limit` (optional): Number of jobs to return (default: 20)

## Monitoring Costs

- Check Railway dashboard for usage
- Free $5 credits should be enough for testing
- Memory usage will be higher due to Chrome (expect ~500MB-1GB per scrape)

## Troubleshooting

If scraper fails in production:

1. **Check logs** - Look for Chrome/Selenium errors
2. **Memory issues** - Railway free tier has memory limits
3. **Timeout errors** - Increase wait times in scraper.py
4. **Rate limiting** - hiring.cafe might be blocking Railway IPs

## Next Steps

Once you identify and fix issues here, apply the same fixes to:
`/Users/gabriel/Documents/projects/hirehack-repos/hirehack-be`

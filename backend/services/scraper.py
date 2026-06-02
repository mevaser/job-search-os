import pandas as pd
from typing import List, Dict, Any
from jobspy import scrape_jobs

def fetch_live_jobs(search_term: str = "Junior ML Engineer", location: str = "Israel", results_wanted: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch real jobs using JobSpy.
    Returns a list of dictionaries with normalized keys.
    """
    try:
        # We scrape indeed and linkedin, feel free to add more like glassdoor
        jobs_df = scrape_jobs(
            site_name=["indeed", "linkedin"],
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            country_linkedin="israel", # specific for linkedin localization if needed
        )
        
        if jobs_df.empty:
            return []

        # Convert NaN to None for JSON/DB compatibility
        jobs_df = jobs_df.where(pd.notnull(jobs_df), None)

        results = []
        for _, row in jobs_df.iterrows():
            # JobSpy usually returns these columns:
            # title, company, location, description, job_url, site, date_posted...
            title = row.get("title", "") or ""
            company = row.get("company", "") or ""
            job_location = row.get("location", "") or ""
            description = row.get("description", "") or ""
            url = row.get("job_url", "") or ""
            site = row.get("site", "jobspy") or "jobspy"
            
            results.append({
                "title": title,
                "company": company,
                "location": job_location,
                "description": description,
                "url": url,
                "source": site
            })
            
        return results
    except Exception as e:
        print(f"Error scraping jobs: {e}")
        return []

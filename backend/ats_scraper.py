import requests
from bs4 import BeautifulSoup
import re
import os
import logging

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
import time
import itertools
import random
from dotenv import load_dotenv
from ddgs import DDGS

load_dotenv()

def scrape_ats_jobs(num_results=5, limit=None, existing_urls=None):
    if existing_urls is None:
        existing_urls = set()
        
    search_urls = set()
    
    domains = ["boards.greenhouse.io", "comeet.com", "jobs.lever.co", "workday.com"]
    roles = ["AI Engineer", "Machine Learning", "GenAI", "Data Engineer", "Data Analyst", "Python Developer", "Big Data Specialist", "Backend Developer"]
    experiences = ["Junior", "Student", "Graduate", "Entry Level", "No Experience"]
    locations = ["Israel", "Tel Aviv", "Herzliya", "Netanya", "Petah Tikva"]
    
    all_queries = []
    for domain in domains:
        for role, exp, loc in itertools.product(roles, experiences, locations):
            all_queries.append(f'site:{domain} "{loc}" "{exp}" "{role}"')
            
    num_queries = 3 if (limit and limit <= 5) else 45
    sampled_queries = random.sample(all_queries, min(len(all_queries), num_queries))
    
    try:
        ddgs = DDGS()
        for i, query in enumerate(sampled_queries):
            logging.info(f"Running ATS search {i+1}/{len(sampled_queries)}: {query}")
            yield {"status": f"Searching DDG ({i+1}/{len(sampled_queries)}): {query}", "type": "info"}
            
            try:
                ddg_results = ddgs.text(query, max_results=num_results)
                for result in ddg_results:
                    link = result.get('href')
                    if link:
                        search_urls.add(link)
            except Exception as inner_e:
                logging.error(f"Error for query '{query}': {inner_e}")
                continue
                
            time.sleep(1)
                
    except Exception as e:
        logging.error(f"Error during DuckDuckGo search: {e}")
        raise Exception(f"DuckDuckGo Search failed. Details: {e}")
        
    logging.info(f"DEBUG: Found {len(search_urls)} raw URLs from search before regex filtering.")
            
    if not search_urls:
        logging.info("No URLs found via DuckDuckGo.")
        yield {"status": "No URLs found via DuckDuckGo.", "type": "info"}
        return
        
    search_urls = list(search_urls)
    yield {"status": f"Found {len(search_urls)} total URLs. Filtering...", "type": "info"}

    filtered_urls = []
    for url in search_urls:
        if not url.startswith('http'):
            continue
        if '/resources/' in url:
            continue
        if 'greenhouse.io' in url and not re.search(r'/jobs/\d+', url):
            continue
        if 'lever.co' in url and not re.search(r'lever\.co/[^/]+/[0-9a-fA-F-]+', url):
            continue
        if 'comeet.com' in url and not re.search(r'/jobs/.*', url):
            continue
        if 'workday.com' in url and '/job/' not in url:
            continue
        filtered_urls.append(url)
        
    if limit is not None:
        filtered_urls = filtered_urls[:limit]
        
    yield {"status": f"Filtered down to {len(filtered_urls)} valid job URLs.", "type": "info"}

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for i, url in enumerate(filtered_urls):
        if url in existing_urls:
            logging.info(f"DEBUG: URL {url} already processed. Skipping.")
            yield {"status": f"URL already processed. Skipping.", "type": "info"}
            continue

        yield {"status": f"Parsing job {i+1}/{len(filtered_urls)}...", "type": "info"}
        logging.info(f"Processing URL: {url}")
        
        try:
            if 'comeet.com' in url:
                url_clean = url.split('?')[0].strip('/')
                parts = url_clean.split('/')
                idx = parts.index('jobs') if 'jobs' in parts else -1
                if idx != -1:
                    company_slug = parts[idx + 1] if len(parts) > idx + 1 else "Unknown"
                    token = None
                    jobid = None
                    
                    if len(parts) >= idx + 5:
                        # Format: /jobs/{company}/{token}/{slug}/{jobid}
                        token = parts[idx + 2]
                        jobid = parts[idx + 4]
                    elif len(parts) >= idx + 4:
                        # Format: /jobs/{company}/{token}/{jobid}
                        token = parts[idx + 2]
                        jobid = parts[idx + 3]
                        
                    if token and jobid:
                        api_url = f"https://www.comeet.com/resources/api/job?token={token}&jobid={jobid}"
                        resp = requests.get(api_url, headers=headers, timeout=10)
                        if resp.status_code == 200:
                            data = resp.json()
                            title = data.get('name', 'Unknown')
                            company = data.get('company_name', company_slug.title())
                            
                            loc_obj = data.get('location', {})
                            city = loc_obj.get('city', '')
                            country = loc_obj.get('country', '')
                            loc_name = loc_obj.get('name', '')
                            location_str = f"{city} {country} {loc_name}".lower()
                            
                            description_parts = []
                            for section in data.get('details', []):
                                s_name = section.get('name', '')
                                s_val = section.get('value', '')
                                if s_name:
                                    description_parts.append(f"{s_name}:\n{s_val}")
                                else:
                                    description_parts.append(s_val)
                            description = "\n\n".join(description_parts)
                            
                            is_israel = any(x in location_str for x in ['israel', 'tel aviv', 'herzliya', 'netanya', 'haifa', 'jerusalem', 'petah tikva', 'raanana'])
                            if not is_israel and ('israel' in description.lower() or 'tel aviv' in description.lower()):
                                is_israel = True
                                
                            # If the API doesn't specify location, let's assume it's Israel since DuckDuckGo matched it on our Israel query
                            if not country and not city and not is_israel:
                                is_israel = True
                                
                            is_relevant = True
                            application_notes = ""
                            
                            if not is_israel:
                                is_relevant = False
                                application_notes = "Rejected: NOT_ISRAEL"
                            elif not description or str(description).strip() == '':
                                is_relevant = False
                                application_notes = "Rejected: EMPTY_DESCRIPTION"
                                
                            yield {
                                "type": "job",
                                "job": {
                                    "title": title,
                                    "company": company,
                                    "location": f"{city}, {country}".strip(', ') if city or country else "Israel",
                                    "job_url": url,
                                    "description": description,
                                    "source": "Comeet",
                                    "is_relevant": is_relevant,
                                    "application_notes": application_notes
                                }
                            }
                            continue # Skip HTML fetching and LLM for Comeet
                        else:
                            logging.info(f"DEBUG: Comeet API failed for {url}. Skipping to prevent LLM quota waste.")
                            continue
                    else:
                        logging.info(f"DEBUG: Comeet URL missing token or jobid {url}. Skipping to prevent LLM quota waste.")
                        continue
                else:
                    logging.info(f"DEBUG: Comeet URL missing 'jobs' path {url}. Skipping to prevent LLM quota waste.")
                    continue
                        
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                logging.error(f"Failed to fetch {url}: {resp.status_code}")
                continue
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Clean HTML
            for noisy in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                noisy.decompose()
            
            html_text = soup.get_text(separator='\n', strip=True)
            

            # Pre-LLM Closed Job Filter
            html_lower = html_text.lower()
            closed_indicators = [
                "job is no longer available",
                "position has been filled",
                "this job is closed",
                "job posting has expired"
            ]
            if any(indicator in html_lower for indicator in closed_indicators):
                logging.info(f"Quick Filter: Position closed for {url}. Skipping LLM.")
                yield {
                    "type": "job",
                    "job": {
                        "title": "Unknown",
                        "company": "Unknown",
                        "location": "Israel",
                        "job_url": url,
                        "description": "Position Closed",
                        "source": "ATS (Boolean)",
                        "is_relevant": False,
                        "application_notes": "POSITION_CLOSED"
                    }
                }
                continue

            # Add pacing to avoid hitting Gemini rate limits on the free tier
            time.sleep(3)
            
            # Pass to Gemini LLM
            from backend.services.llm_parser import parse_job_html
            parsed_data = parse_job_html(html_text, url)
            
            if parsed_data is None:
                logging.warning(f"Skipping job due to LLM failure or API quota limits: {url}")
                continue
            
            title = None
            company = "Unknown"
            description = ""
            
            if parsed_data:
                title = parsed_data.get('title')
                company = parsed_data.get('company', 'Unknown')
                description = parsed_data.get('description', '')
                
            logging.info(f"DEBUG LLM Output for {url}: {parsed_data}")
                
            # Post-LLM validation
            is_relevant = True
            application_notes = ""
            
            if title == 'NOT_ISRAEL':
                logging.info(f"Marking job not in Israel: {url}")
                is_relevant = False
                application_notes = "Rejected: NOT_ISRAEL"
            elif description == 'EMPTY' or not description:
                logging.info(f"Marking generic page without specific description: {url}")
                is_relevant = False
                application_notes = "Rejected: EMPTY_DESCRIPTION"
            elif title and (str(title).strip().lower() in ['jobs', 'apply', 'job', 'careers'] or str(title).strip() == ''):
                logging.info(f"Marking job with invalid title ({title}): {url}")
                is_relevant = False
                application_notes = f"Rejected: INVALID_TITLE ({title})"
            
            # Fallbacks if LLM failed
            if not title or str(title).lower() in ["unknown", "null", "none", ""]:
                slug_parts = url.strip('/').split('/')
                if slug_parts:
                    slug = slug_parts[-1].replace('-', ' ').title()
                    title = slug
                if not title:
                    title = "Unknown"
                    
            if not company or str(company).lower() in ['greenhouse', 'lever', 'comeet', 'workday', 'unknown', 'null', 'none', '']:
                # Attempt company from URL
                if 'greenhouse.io/' in url:
                    match = re.search(r'greenhouse\.io/([^/]+)', url)
                    if match:
                        company = match.group(1).title()
                elif 'lever.co/' in url:
                    match = re.search(r'lever\.co/([^/]+)', url)
                    if match:
                        company = match.group(1).title()
                elif 'comeet.com' in url:
                    match = re.search(r'comeet\.com/jobs/([^/]+)', url)
                    if match:
                        company = match.group(1).title()
                    else:
                        company = "Comeet Company"
            
            if not description or not str(description).strip() or str(description).lower() in ["null", "none", ""]:
                description = "No description provided by the source."
                
            # Determine source
            source = "ATS (Boolean)"
            if 'greenhouse.io' in url:
                source = "Greenhouse"
            elif 'lever.co' in url:
                source = "Lever"
            elif 'comeet.com' in url:
                source = "Comeet"
            elif 'workday.com' in url:
                source = "Workday"
            
            yield {
                "type": "job",
                "job": {
                    "title": title,
                    "company": company,
                    "location": "Israel", 
                    "job_url": url,
                    "description": description,
                    "source": source,
                    "is_relevant": is_relevant,
                    "application_notes": application_notes
                }
            }
            
        except Exception as e:
            logging.error(f"Error parsing URL {url}: {e}")
            yield {"status": f"Error parsing URL {url}: {str(e)}", "type": "error"}
            
    yield {"status": "Done scanning ATS.", "type": "complete"}

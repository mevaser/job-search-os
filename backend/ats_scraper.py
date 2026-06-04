import requests
from bs4 import BeautifulSoup
import re
import os
import time
from dotenv import load_dotenv
from ddgs import DDGS

load_dotenv()

def scrape_ats_jobs(num_results=5):
    search_urls = set()
    
    domains = ["boards.greenhouse.io", "comeet.com", "jobs.lever.co", "workday.com"]
    terms = ["Israel junior data", "Israel entry level developer", "Israel junior python"]
    
    try:
        ddgs = DDGS()
        for domain in domains:
            for term in terms:
                query = f"site:{domain} {term}"
                print(f"Running flattened ATS search via DuckDuckGo: {query}")
                yield {"status": f"Searching DuckDuckGo: {query}", "type": "info"}
                
                try:
                    ddg_results = ddgs.text(query, max_results=num_results)
                    for result in ddg_results:
                        link = result.get('href')
                        if link:
                            search_urls.add(link)
                except Exception as inner_e:
                    print(f"Error for query '{query}': {inner_e}")
                    continue
                    
                time.sleep(1)
                
    except Exception as e:
        print(f"Error during DuckDuckGo search: {e}")
        raise Exception(f"DuckDuckGo Search failed. Details: {e}")
            
    if not search_urls:
        print("No URLs found via DuckDuckGo.")
        yield {"status": "No URLs found via DuckDuckGo.", "type": "info"}
        return
        
    search_urls = list(search_urls)
    yield {"status": f"Found {len(search_urls)} total URLs. Filtering...", "type": "info"}

    filtered_urls = []
    for url in search_urls:
        if not url.startswith('http'):
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
        
    yield {"status": f"Filtered down to {len(filtered_urls)} valid job URLs.", "type": "info"}

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for i, url in enumerate(filtered_urls):
        yield {"status": f"Parsing job {i+1}/{len(filtered_urls)}...", "type": "info"}
        print(f"Processing URL: {url}")
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"Failed to fetch {url}: {resp.status_code}")
                continue
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Clean HTML
            for noisy in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                noisy.decompose()
            
            html_text = soup.get_text(separator='\n', strip=True)
            
            # Pass to Gemini LLM
            from backend.services.llm_parser import parse_job_html
            parsed_data = parse_job_html(html_text, url)
            
            title = None
            company = "Unknown"
            description = ""
            
            if parsed_data:
                title = parsed_data.get('title')
                company = parsed_data.get('company', 'Unknown')
                description = parsed_data.get('description', '')
                
            print(f"DEBUG LLM Output for {url}: {parsed_data}")
                
            # Post-LLM validation
            if title == 'NOT_ISRAEL':
                print(f"Skipping job not in Israel: {url}")
                continue
            if description == 'EMPTY' or not description:
                print(f"Skipping generic page without specific description: {url}")
                continue
            if title and (str(title).strip().lower() in ['jobs', 'apply', 'job', 'careers'] or str(title).strip() == ''):
                print(f"Skipping job with invalid title ({title}): {url}")
                continue
            
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
                    "location": "Israel / Tel Aviv", # Hardcoded based on query
                    "job_url": url,
                    "description": description,
                    "source": source
                }
            }
            
        except Exception as e:
            print(f"Error parsing URL {url}: {e}")
            yield {"status": f"Error parsing URL {url}: {str(e)}", "type": "error"}
            
    yield {"status": "Done scanning ATS.", "type": "complete"}

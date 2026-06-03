import requests
from bs4 import BeautifulSoup
from googlesearch import search
import re

def scrape_ats_jobs(num_results=20):
    query = 'site:boards.greenhouse.io OR site:comeet.com OR site:jobs.lever.co OR site:workday.com ("junior" OR "entry level" OR "data") ("Israel" OR "Tel Aviv")'
    print(f"Running boolean ATS search: {query}")
    
    results = []
    
    try:
        # Perform Google search
        search_urls = search(query, num_results=num_results, sleep_interval=2)
    except Exception as e:
        print(f"Error during Google search: {e}")
        return results

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for url in search_urls:
        if not url.startswith('http'):
            continue
            
        print(f"Processing URL: {url}")
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"Failed to fetch {url}: {resp.status_code}")
                continue
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extract basic info
            title = None
            company = "Unknown"
            description = ""
            
            # Extract description from meta tag as fallback
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc.get('content').strip()
            
            # Extract title and company from HTML title
            page_title = soup.find('title')
            page_title_text = page_title.text.strip() if page_title else ""
            
            if page_title_text:
                title_parts = [t.strip() for t in re.split(r' at | - | \| ', page_title_text) if t.strip()]
                if title_parts:
                    title = title_parts[0]
                    if len(title_parts) > 1:
                        company = title_parts[-1]
            
            # Fallback to URL slug
            if not title:
                slug_parts = url.strip('/').split('/')
                if slug_parts:
                    slug = slug_parts[-1].replace('-', ' ').title()
                    title = slug
                if not title:
                    title = "Unknown"
                    
            if not company or company.lower() in ['greenhouse', 'lever', 'comeet', 'workday', 'unknown']:
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
            
            if not description or not str(description).strip():
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
            
            results.append({
                "title": title,
                "company": company,
                "location": "Israel / Tel Aviv", # Hardcoded based on query
                "job_url": url,
                "description": description,
                "source": source
            })
            
        except Exception as e:
            print(f"Error parsing URL {url}: {e}")
            
    return results

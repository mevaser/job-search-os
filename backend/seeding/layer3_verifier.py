import requests
import re
import sqlite3
from urllib.parse import urlparse
from .models import DB_PATH, add_sniper_target, init_db

# Headers to appear as a normal client during verification
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def verify_ats_endpoint(company_name: str, slug: str):
    """
    Given a company slug, tests known ATS URL formats.
    If it returns 200 and has valid content, adds it to the Sniper DB.
    """
    platforms = {
        "Greenhouse": f"https://boards.greenhouse.io/{slug}",
        "Lever": f"https://jobs.lever.co/{slug}",
        "Comeet": f"https://www.comeet.co/jobs/{slug}/all",
        "Workable": f"https://apply.workable.com/{slug}"
    }

    for platform, url in platforms.items():
        try:
            # We don't allow redirects for ATS endpoints to avoid hitting main landing pages
            response = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=False)
            
            if response.status_code == 200:
                # Basic validation: ensure the page is actually an ATS board
                text = response.text.lower()
                if "job" in text or "careers" in text or "openings" in text:
                    print(f"[SUCCESS] Verified {company_name} on {platform}: {url}")
                    add_sniper_target(company_name, platform, url)
                    return True
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to check {url}: {e}")
            
    print(f"[FAIL] Could not verify ATS for {company_name} ({slug})")
    return False

def process_pending_verifications():
    """Reads from PendingVerification table and attempts to verify"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Fetch pending entries
    cursor.execute("SELECT id, company_name, raw_url FROM PendingVerification WHERE status = 'pending'")
    rows = cursor.fetchall()
    
    for row in rows:
        db_id, company_name, raw_url = row
        
        # Determine slug
        slug = ""
        if company_name and company_name != "Unknown (From Email)":
            # Basic slugification
            slug = re.sub(r'[^a-zA-Z0-9]', '', company_name).lower()
        elif raw_url:
            # Try to extract a slug from the raw URL (e.g., if it's a linkedin redirect)
            # This is complex, but for MVP we might just use the hostname parts
            domain = urlparse(raw_url).netloc
            parts = domain.split('.')
            if len(parts) > 1:
                # Try to use the core domain name as the slug (e.g. startup from www.startup.com)
                slug = parts[-2]
                company_name = slug.capitalize()
                
        if slug:
            print(f"Testing slug: {slug} for {company_name}")
            success = verify_ats_endpoint(company_name, slug)
            new_status = 'verified' if success else 'failed'
            
            # Update status in DB
            cursor.execute("UPDATE PendingVerification SET status = ? WHERE id = ?", (new_status, db_id))
            conn.commit()
            
    conn.close()

if __name__ == "__main__":
    process_pending_verifications()

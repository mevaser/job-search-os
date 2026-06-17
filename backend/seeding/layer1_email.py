import imaplib
import email
import re
import logging
from email.header import decode_header
import os
from bs4 import BeautifulSoup
from .models import add_pending_company, init_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Gmail IMAP settings
IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = os.environ.get("GMAIL_ADDRESS", "jobs@careerflow.ai")
EMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

def connect_imap():
    logging.info(f"Connecting to IMAP server: {IMAP_SERVER}")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    logging.info("Successfully logged into IMAP.")
    return mail

def extract_urls(text, is_html=False):
    urls = []
    if is_html:
        try:
            soup = BeautifulSoup(text, 'html.parser')
            for a in soup.find_all('a', href=True):
                urls.append(a['href'])
        except Exception as e:
            logging.error(f"BeautifulSoup parsing error: {e}")
            
    # Basic URL extraction regex - slightly more forgiving
    url_pattern = re.compile(r'(?:https?://|www\.)[^\s<>"]+')
    urls.extend(url_pattern.findall(text))
    return urls

def fetch_job_alerts():
    logging.info("Initializing database...")
    init_db()
    
    try:
        mail = connect_imap()
    except Exception as e:
        logging.error(f"Failed to connect to IMAP: {e}")
        return
        
    mail.select("inbox")
    
    # Search for ALL emails to be forgiving for MVP testing
    logging.info("Searching for recent emails in Inbox (ignoring Read/Unread status)...")
    status, messages = mail.search(None, 'ALL')
    
    if not messages or not messages[0]:
        logging.info("No emails found in the inbox.")
        mail.close()
        mail.logout()
        return

    email_ids = messages[0].split()
    # For MVP, let's just process the 10 most recent emails to avoid huge runtimes
    recent_email_ids = email_ids[-10:]
    logging.info(f"Found {len(email_ids)} total emails. Processing the {len(recent_email_ids)} most recent ones.")
    
    for e_id in recent_email_ids:
        status, msg_data = mail.fetch(e_id, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                sender = msg.get("From", "")
                subject_header = msg.get("Subject", "")
                
                if not subject_header:
                    logging.info("Skipped non-job email: [Empty Subject]")
                    continue

                subject, encoding = decode_header(subject_header)[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8', errors='ignore')
                
                if not subject:
                    logging.info("Skipped non-job email: [Empty Subject]")
                    continue

                subject_lower = subject.lower()
                sender_lower = sender.lower()
                
                # Check for skip conditions
                if "security alert" in subject_lower or "2-step verification" in subject_lower:
                    logging.info(f"Skipped non-job email: {subject}")
                    continue
                    
                # Check for include conditions
                if "linkedin.com" in sender_lower or "job alert" in subject_lower or "fwd:" in subject_lower:
                    logging.info(f"--- Processing email: '{subject}' from '{sender}' ---")
                else:
                    logging.info(f"Skipped non-job email: {subject}")
                    continue
                
                urls_found = []
                
                # Extract body
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type in ["text/plain", "text/html"]:
                            body = part.get_payload(decode=True).decode(errors='ignore')
                            urls_found.extend(extract_urls(body, is_html=(content_type == "text/html")))
                else:
                    content_type = msg.get_content_type()
                    body = msg.get_payload(decode=True).decode(errors='ignore')
                    urls_found.extend(extract_urls(body, is_html=(content_type == "text/html")))
                
                unique_urls = set(urls_found)
                if not unique_urls:
                    logging.info("No URLs found in this email.")
                else:
                    logging.info(f"Extracted {len(unique_urls)} unique URLs.")
                    inserted_count = 0
                    for url in unique_urls:
                        try:
                            # add_pending_company explicitly calls conn.commit() internally
                            add_pending_company(company_name="Unknown (From Email)", raw_url=url, source="email")
                            inserted_count += 1
                        except Exception as e:
                            logging.error(f"Failed to insert URL {url} into database: {e}")
                    
                    logging.info(f"Successfully inserted {inserted_count} URLs into PendingVerification table.")

    mail.close()
    mail.logout()
    logging.info("Finished processing emails.")

if __name__ == "__main__":
    fetch_job_alerts()

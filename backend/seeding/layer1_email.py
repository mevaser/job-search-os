import imaplib
import email
import re
import logging
from email.header import decode_header
import os
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

def extract_urls(text):
    # Basic URL extraction regex - slightly more forgiving
    url_pattern = re.compile(r'(?:https?://|www\.)[^\s<>"]+')
    return url_pattern.findall(text)

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
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8')
                
                logging.info(f"--- Processing email: '{subject}' ---")
                
                urls_found = []
                
                # Extract body
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain" or part.get_content_type() == "text/html":
                            body = part.get_payload(decode=True).decode(errors='ignore')
                            urls_found.extend(extract_urls(body))
                else:
                    body = msg.get_payload(decode=True).decode(errors='ignore')
                    urls_found.extend(extract_urls(body))
                
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

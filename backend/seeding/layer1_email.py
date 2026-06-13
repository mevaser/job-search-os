import imaplib
import email
import re
from email.header import decode_header
import os
from .models import add_pending_company, init_db

# Gmail IMAP settings
IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = os.environ.get("GMAIL_ADDRESS", "jobs@careerflow.ai")
EMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

def connect_imap():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    return mail

def extract_urls(text):
    # Basic URL extraction regex
    url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
    return url_pattern.findall(text)

def fetch_job_alerts():
    init_db()
    try:
        mail = connect_imap()
    except Exception as e:
        print(f"Failed to connect to IMAP: {e}")
        return
        
    mail.select("inbox")
    
    # Search for unread emails (you can narrow this to Specific Sender like Indeed/LinkedIn)
    status, messages = mail.search(None, '(UNSEEN)')
    
    if not messages or not messages[0]:
        print("No new emails found.")
        mail.close()
        mail.logout()
        return

    email_ids = messages[0].split()
    
    for e_id in email_ids:
        status, msg_data = mail.fetch(e_id, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8')
                
                print(f"Processing email: {subject}")
                
                # Extract body
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors='ignore')
                            urls = extract_urls(body)
                            for url in set(urls): # Unique URLs
                                add_pending_company(company_name="Unknown (From Email)", raw_url=url, source="email")
                else:
                    body = msg.get_payload(decode=True).decode(errors='ignore')
                    urls = extract_urls(body)
                    for url in set(urls):
                        add_pending_company(company_name="Unknown (From Email)", raw_url=url, source="email")
                        
    mail.close()
    mail.logout()
    print("Finished processing emails.")

if __name__ == "__main__":
    fetch_job_alerts()

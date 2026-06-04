import os
import json
from openai import OpenAI
from pydantic import BaseModel
from typing import Optional

class ExtractedJob(BaseModel):
    title: str
    company: str
    description: str

def parse_job_html(html_text: str, url: str) -> Optional[dict]:
    if not html_text or not html_text.strip():
        print(f"Skipping LLM parsing: HTML content is empty for {url}")
        return None
        
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise Exception("GEMINI_API_KEY is not set.")
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    prompt = f"""
    You are an expert ATS parser. Extract the actual Job Role/Title (ignoring generic ATS site titles), 
    the actual hiring Company Name, and the FULL, complete Job Description from the provided raw website text.
    
    CRITICAL RULES:
    1. LOCATION: You MUST check the location. If the job is NOT located in Israel (or Remote within Israel), you MUST return 'NOT_ISRAEL' as the title. If the location mentions any Israeli city (e.g., Tel Aviv, Herzliya, Haifa, Netanya, Jerusalem, Petah Tikva, Raanana), you MUST consider it as Israel. Do NOT return 'NOT_ISRAEL' for these.
    2. TITLE: Extract the exact, real Job Role (e.g. 'Junior Data Engineer'). Do NOT return generic words like 'Apply', 'Jobs', or numbers.
    3. DESCRIPTION: You MUST extract the FULL job description. If this is a generic page without a specific job description, return 'EMPTY' as the description.
    
    If the company name cannot be found in the text, you may try to infer it from the URL: {url}
    
    Respond strictly in JSON matching this schema:
    {{
        "title": "str",
        "company": "str",
        "description": "str"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gemini-1.5-flash",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Raw Text:\n{html_text}"}
            ],
            response_format={"type": "json_object"}
        )
        raw_content = response.choices[0].message.content
        result = json.loads(raw_content)
        return result
    except Exception as e:
        print(f"Error parsing with OpenAI SDK: {e}")
        return None

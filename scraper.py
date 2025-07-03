
import gspread
from google.oauth2.service_account import Credentials
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
from serpapi import GoogleSearch
from dotenv import load_dotenv
import os
import requests

load_dotenv()
# Load Google credentials from environment variable
creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

# Open the Google Sheet
sheet = client.open("Google Scraper Data").sheet1

# Load search config
with open('config.json', 'r') as f:
    config = json.load(f)

vertical = config['vertical']
keywords = config['freight_keywords']
location = config.get('location', '')

results = []
seen_domains = set()

states_to_search = ["Arizona"]

for state in states_to_search:
    for keyword in keywords:
        query = f'"{vertical}" + "{keyword}" + {state}'
        api_key = os.getenv("SERPAPI_API_KEY")

        print(f"Searching for: {query}")

        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key
        }

result = {}
search = GoogleSearch(params)
all_results = []

while True:
    result = search.get_dict()
    all_results.extend(result.get("organic_results", []))

    # Follow the "next" link if available
    next_page = result.get("serpapi_pagination", {}).get("next")
    if not next_page:
        break

    # Update the query params to go to the next page
    search = GoogleSearch({
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "start": len(all_results)
    })

    time.sleep(2)  # Small delay to avoid hitting rate limits

print(json.dumps(result, indent=2))

import re
from urllib.parse import urlparse
import re

for g in all_results:
    link = g.get("link")
    if not link:
        continue
    # Extract root domain from URL
    parsed_url = urlparse(link)
    domain = parsed_url.netloc.replace('www.', '')

    # Skip bad domains with logging
    bad_extensions = (".gov", ".org", ".edu")
    bad_domains = ["linkedin.com", "facebook.com", "twitter.com", "instagram.com"]

    if domain.endswith(bad_extensions):
        print(f"Skipping {domain} due to bad extension")
        continue

    if any(bad in domain for bad in bad_domains):
        print(f"Skipping {domain} due to bad domain match")
        continue

    # Try to find Contact page
    contact_url = None
    contact_paths = ["/contact", "/contact-us", "/contactus"]
    for path in contact_paths:
        if path in link:
            contact_url = link
            break
    if not contact_url:
        contact_url = link.rstrip("/") + "/contact"

    # Fetch Contact page content
    try:
        response = requests.get(contact_url, timeout=5)
        if response.status_code != 200:
            text = ""
        else:
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(" ", strip=True)

    except requests.exceptions.RequestException:
        text = ""

    # Extract phone number from Contact page
    phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    phone_number = phone_match.group() if phone_match else ''

    # Try to extract state from Contact page
    states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
              "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
              "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
              "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
              "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
              "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
              "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]

state = next((s for s in states_to_search if s.lower() in text.lower()), '')

# Only append if we have a phone number (state is optional)
if not phone_number:
    print(f"No phone number found for {domain}")
else:
    print(f"✅ VALID ENTRY: {domain}, {phone_number}, {state}")
    sheet.append_row([
        domain,
        state,
        phone_number
    ])
    seen_domains.add(domain)

    time.sleep(3)  # Avoid rate-limiting

# Upload results to Google Sheet
sheet = client.open("Google Scraper Data").sheet1
print(f"Total domains found: {len(seen_domains)}")

print("Scraping complete. Results saved to output.csv")

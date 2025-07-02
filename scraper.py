
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

states_to_search = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
]

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

        search = GoogleSearch(params)
        result = search.get_dict()

import re
from urllib.parse import urlparse
import re

for g in result.get("organic_results", []):
    link = g.get("link")
    if not link:
        continue

    # Extract root domain from URL
    parsed_url = urlparse(link)
    domain = parsed_url.netloc.replace('www.', '')

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
            raise Exception("Bad status")
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

    if domain and domain not in seen_domains:
        sheet.append_row([
            domain,
            state,
            phone_number
        ])
        seen_domains.add(domain)

    time.sleep(3)  # Avoid rate-limiting

# Upload results to Google Sheet
sheet = client.open("Google Scraper Data").sheet1
sheet.clear()  # optional: remove existing content

print("Scraping complete. Results saved to output.csv")

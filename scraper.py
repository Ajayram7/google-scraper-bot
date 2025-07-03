
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

states_to_search = [""]

for state in states_to_search:
    for keyword in keywords:
        query = f'{vertical} + "{keyword}"'
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

import requests

freight_keywords = ["ltl", "ltl shipping", "less than truckload", "freight", "ltl freight"]
found_websites = []

for g in all_results:
    link = g.get("link")
    if not link:
        continue

    print(f"Checking link: {link}")

try:
    response = requests.get(link, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code == 200:
        page_text = response.text.lower()
        if any(keyword in page_text for keyword in freight_keywords):
            print(f"✅ Freight keyword found on: {link}")
            found_websites.append(link)
        else:
            print(f"❌ No freight keywords on: {link}")
    else:
        print(f"⚠️ Failed to fetch {link} — status code {response.status_code}")
except Exception as e:
    print(f"❌ Error fetching {link}: {e}")

# Save found URLs to CSV
import csv

with open("output.csv", mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["URL"])
    for url in found_websites:
        writer.writerow([url])

from urllib.parse import urljoin, urlparse

# Start with homepage
contact_urls_to_check = [link]

try:
    response = requests.get(link, timeout=5)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(link, href)

            # Only add internal links
            if urlparse(full_url).netloc == urlparse(link).netloc:
                if full_url not in contact_urls_to_check:
                    contact_urls_to_check.append(full_url)
except requests.exceptions.RequestException:
    pass

phone_number = ''
text = ''

for page_url in contact_urls_to_check:
    try:
        response = requests.get(page_url, timeout=5)
        if response.status_code == 200:
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(" ", strip=True)

            phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
            if phone_match:
                phone_number = phone_match.group()
                break  # Stop once we find a phone number
    except requests.exceptions.RequestException:
        continue

    # Try to extract state from Contact page
    states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
              "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
              "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
              "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
              "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
              "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
              "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]

state = next((s for s in states_to_search if s.lower() in text.lower()), '')

parsed_url = urlparse(link)
domain = parsed_url.netloc.replace('www.', '')

print(f"✅ VALID ENTRY: {domain}")
sheet.append_row([domain])
seen_domains.add(domain)

    time.sleep(3)  # Avoid rate-limiting

# Upload results to Google Sheet
sheet = client.open("Google Scraper Data").sheet1
print(f"Total domains found: {len(seen_domains)}")

print("Scraping complete. Results saved to output.csv")

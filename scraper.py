
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
from urllib.parse import urlparse
import csv

# -------------------------------
# LOAD CREDS
# -------------------------------
load_dotenv()

creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

sheet = client.open("Google Scraper Data").sheet1

# -------------------------------
# LOAD CONFIG
# -------------------------------
with open("config.json", "r") as f:
    config = json.load(f)

vertical = config["vertical"]
freight_keywords = config["freight_keywords"]
location = config.get("location", "")

results = []
seen_domains = set()

# -------------------------------
# GOOGLE SEARCH
# -------------------------------
states_to_search = [""]

for state in states_to_search:
    for keyword in freight_keywords:
        query = f'{vertical} "{keyword}"'
        api_key = os.getenv("SERPAPI_API_KEY")

        print(f"\n🔍 Searching Google for: {query}")

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

    next_page = result.get("serpapi_pagination", {}).get("next")
    if not next_page:
        break

    search = GoogleSearch({
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "start": len(all_results)
    })

    time.sleep(2)

print(f"\nTotal Google results collected: {len(all_results)}\n")

# -------------------------------
# PROCESS RESULTS
# -------------------------------
found_websites = []

if not all_results:
    print("❌ No Google search results returned.")
    exit()

shipping_indicators = ["shipping", "delivery", "freight", "shipping-info", "returns", "policies"]

for g in all_results:
    link = g.get("link")
    if not link:
        continue

    print(f"\n🔗 Checking link: {link}")

    # Extract domain
    domain = urlparse(link).netloc.replace("www.", "")
    if domain in seen_domains:
        print(f"🔁 Already saved, skipping: {domain}")
        continue

    # URL-based freight signals
    url_flag = any(ind in link.lower() for ind in shipping_indicators)

    # Fetch page
    try:
        response = requests.get(link, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            page_text = response.text.lower()

            # Check for freight keywords in page text
            keyword_flag = any(k.lower() in page_text for k in freight_keywords)

            if url_flag or keyword_flag:
                print(f"✅ MATCH FOUND: {domain} (Reason: {'URL' if url_flag else 'Keyword'})")
                found_websites.append(domain)
                seen_domains.add(domain)
                sheet.append_row([domain])  # Save to Google Sheet
            else:
                print(f"❌ No freight match for: {link}")

        else:
            print(f"⚠️ Failed to fetch {link} (status {response.status_code})")

    except Exception as e:
        print(f"❌ Error fetching {link}: {e}")

# -------------------------------
# WRITE TO CSV
# -------------------------------
with open("output.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["URL"])
    for url in found_websites:
        writer.writerow([url])

print("\n----------------------------------------")
print(f"🎉 SCRAPING COMPLETE — {len(found_websites)} VALID FREIGHT DOMAINS FOUND")
print("📄 Results saved to output.csv AND Google Sheets")
print("----------------------------------------")


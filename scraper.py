
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
# BLACKLIST SYSTEM
# -------------------------------

# 1️⃣ Exact domain blacklist
blacklisted_domains = {
    # SOCIAL / NEWS / BLOGS
    "facebook.com", "m.facebook.com", "youtube.com", "vimeo.com", "reddit.com", 
    "linkedin.com", "steamcommunity.com", "turbobricks.com",
    "apnews.com", "nzherald.co.nz", "financialpost.com", "law360.com",
    "airqualitynews.com", "theguardian.com", "marketbeat.com", "stuff.co.nz",
    "hola.com", "krcgtv.com", "stomp.sg", "currently.att.yahoo.com",
    "finance.yahoo.com", "industrialscenery.blogspot.com", "theloadstar.com",
    "supplychaindive.com", "finehomebuilding.com", "floorcoveringweekly.com",
    "fcnews.net", "housedigest.com", "vocal.media", "mennogazendam.substack.com",

    # MARKETPLACES / RETAIL
    "temu.com", "wayfair.com", "sell.wayfair.com", "chegg.com",
    "targetfmi.com", "planetexpress.com",

    # GOVERNMENT
    "customs.gov.sg", "wisconsindot.gov", "ncdot.gov", "gov.uk",
    "app.leg.wa.gov", "governor.virginia.gov", "dir.ca.gov", "ops.fhwa.dot.gov",
    "safer.fmcsa.dot.gov", "law.cornell.edu", "open.alberta.ca",
    "portlibertynewyork.com", "portoflosangeles.org", "portseattle.org",

    # COMPETITOR LOGISTICS / COURIERS
    "tnt.com", "paisleyfreight.com", "tforcefreight.com",
    "eurosender.com", "regencyfreight.co.uk", "reliancecourierservices.com",
    "eastgatefreight.com", "kapoklogcn.com", "globalgatesshipping.com",
    "global-gate.us", "atlantic-gate.com", "oceangatesdelivery.com",
    "bamfreight.com", "directdrivelogistics.com", "loadshift.com.au",
    "roserocket.com", "maplegatefreight.com", "freight-gate.com",
    "freightgate.net", "freightrun.com", "flow.space", "forwardair.com",
    "partner3pl.com", "tps-global.com", "sdilogistics-shippings.com",
    "interwf.com", "freightsmith.net", "m.jctrans.com", "azfreight.com",
    "shipfli.com", "shipsgates.com", "airfreight.news",

    # RAIL / CARRIERS (won't use brokers)
    "jbhunt.com", "bnsf.com", "up.com", "norfolksouthern.com", "wabteccorp.com",
}

# 2️⃣ Substring blacklist
blacklisted_substrings = [
    "youtube", "facebook", "reddit", "gov", "news", "blog", "wiki",
    "courier", "shipping company", "carrier", "tracking",
    "railroad", "railway", "ups.com", "fedex.com", "dhl.com"
]

# Function to check blacklist
def is_blacklisted(domain):
    domain = domain.lower()

    # Exact matches
    if domain in blacklisted_domains:
        return True

    # Substring matches
    return any(bad in domain for bad in blacklisted_substrings)


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

    # Skip duplicates
    if domain in seen_domains:
        print(f"🔁 Already saved, skipping: {domain}")
        continue

    # Apply blacklist check
    if is_blacklisted(domain):
        print(f"⛔ BLACKLISTED, skipping: {domain}")
        continue

    # URL-based freight signals
    url_flag = any(ind in link.lower() for ind in shipping_indicators)

    # Fetch page
    try:
        response = requests.get(link, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            page_text = response.text.lower()

            # Check for freight keywords inside the site
            keyword_flag = any(k.lower() in page_text for k in freight_keywords)

            if url_flag or keyword_flag:
                print(f"✅ MATCH FOUND: {domain} (Reason: {'URL' if url_flag else 'Keyword'})")

                found_websites.append(domain)
                seen_domains.add(domain)
                sheet.append_row([domain])
            else:
                print(f"❌ No freight match for: {link}")

        else:
            print(f"⚠️ Failed




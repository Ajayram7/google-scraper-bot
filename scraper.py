
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
from serpapi import GoogleSearch
from dotenv import load_dotenv
import os

load_dotenv()

# Load search config
with open('config.json', 'r') as f:
    config = json.load(f)

vertical = config['vertical']
keywords = config['freight_keywords']
location = config.get('location', '')

results = []

for keyword in keywords:
    query = f'"{vertical}" + "{keyword}" + {location}'
    api_key = os.getenv("SERPAPI_API_KEY")

    print(f"Searching for: {query}")
params = {
    "engine": "google",
    "q": query,
    "api_key": api_key
}

search = GoogleSearch(params)
result = search.get_dict()
print("SERPAPI RESPONSE:", result)

import re
from urllib.parse import urlparse

for g in result.get("organic_results", []):
    link = g.get("link")
    snippet = g.get("snippet", "")

    # Extract phone number using regex
    phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', snippet)
    phone_number = phone_match.group() if phone_match else ''

    # Try to extract state by checking known U.S. states in snippet
    states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
              "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
              "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
              "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
              "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
              "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
              "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]

    state = next((s for s in states if s.lower() in snippet.lower()), '')

    # Extract root domain from URL
    domain = ''
    if link:
        parsed_url = urlparse(link)
        domain = parsed_url.netloc.replace('www.', '')

    if domain:
        results.append({
            'Website': domain,
            'State': state,
            'Phone Number': phone_number
        })

time.sleep(5)  # avoid hitting Google too quickly

# Save results
df = pd.DataFrame(results)
df.to_csv("output.csv", index=False)
print("Scraping complete. Results saved to output.csv")

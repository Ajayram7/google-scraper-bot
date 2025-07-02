
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
from serpapi.google_search_results import GoogleSearch
from dotenv import load_dotenv
import os

load_dotenv()

# Load search config
with open('../config.json', 'r') as f:
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

for g in result.get("organic_results", []):
    title = g.get("title")
    link = g.get("link")
    snippet = g.get("snippet")

    if title and link:
        results.append({
            'title': title,
            'link': link,
            'snippet': snippet if snippet else ''
        })

    time.sleep(5)  # avoid hitting Google too quickly

# Save results
df = pd.DataFrame(results)
df.to_csv("output.csv", index=False)
print("Scraping complete. Results saved to output.csv")

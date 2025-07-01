import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time

# Load search config
with open('../config.json', 'r') as f:
    config = json.load(f)

vertical = config['vertical']
keywords = config['freight_keywords']
location = config.get('location', '')

results = []

for keyword in keywords:
    query = f'"{vertical}" + "{keyword}" + {location}'
    print(f"Searching for: {query}")

    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.text, "html.parser")
    for g in soup.select('div.tF2Cxc'):
        title = g.select_one('h3')
        link = g.select_one('a')
        snippet = g.select_one('.VwiC3b')

        if title and link:
            results.append({
                'title': title.text,
                'link': link['href'],
                'snippet': snippet.text if snippet else ''
            })

    time.sleep(5)  # avoid hitting Google too quickly

# Save results
df = pd.DataFrame(results)
df.to_csv("output.csv", index=False)
print("Scraping complete. Results saved to output.csv")

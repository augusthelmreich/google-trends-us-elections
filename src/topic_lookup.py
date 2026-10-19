"""
Resolve a search term to Google Trends topic IDs and show the options.

Uses the public autocomplete endpoint of trends.google.com (no key needed). The first
match is NOT automatically right: "health care" once resolved to a logistics company.
Read the titles, pick the entity that means the concept, then validate it by
geography with fetch_regions() before it goes into data/raw/topics.csv.

    python src/topic_lookup.py "climate change" "education" "crime"
"""
import json
import sys
import urllib.parse
import urllib.request

for term in sys.argv[1:] or ["climate change", "education", "crime"]:
    url = "https://trends.google.com/trends/api/autocomplete/" + urllib.parse.quote(term) + "?hl=en-US&tz=-60"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8")
    raw = raw[raw.index("{"):]                                   # strip the )]}' prefix
    topics = json.loads(raw).get("default", {}).get("topics", [])
    print(f'\n"{term}"')
    for t in topics[:8]:
        print(f"   {t.get('mid', ''):<14} {t.get('title', '')}  |  {t.get('type', '')}")

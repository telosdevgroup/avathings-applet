import sys
sys.path.insert(0, r"c:\Users\dev\Code\tdg\avathings")
import log_stream
import os
import json
from collections import Counter, defaultdict
from pathlib import Path
import requests

for site, path in log_stream.LOG_SOURCES.items():
    if not os.path.exists(path):
        continue
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            log_stream.classify_line_fast(line_str, site)

print(f"Total citations extracted: {len(log_stream.citations_list)}")

domains = {
    "AvaScry": "https://avascry.com",
    "VetGems": "https://vetgems.com",
    "AvaSpecs": "https://avaspecs.com",
    "AvaMinder": "https://avaminder.com"
}

url_counts = Counter()
url_sources = defaultdict(set)
url_site = {}

for c in log_stream.citations_list:
    dom = domains.get(c["site"], "")
    if not dom:
        continue
    full_url = dom + c["route"]
    url_counts[full_url] += 1
    url_sources[full_url].add(c["source"])
    url_site[full_url] = c["site"]

ranked = []
for rank, (url, count) in enumerate(url_counts.most_common(), start=1):
    ranked.append({
        "rank": rank,
        "url": url,
        "citations": count,
        "site": url_site[url],
        "sources": sorted(list(url_sources[url]))
    })

print(f"Unique cited content URLs: {len(ranked)}")

out_dir = Path(r"c:\Users\dev\Code\tdg\avathings\exports")
out_dir.mkdir(parents=True, exist_ok=True)
urls_txt = out_dir / "citations_ranked_urls.txt"
with open(urls_txt, "w", encoding="utf-8") as f:
    for r in ranked:
        f.write(r["url"] + "\n")

json_out = out_dir / "citations_ranked.json"
with open(json_out, "w", encoding="utf-8") as f:
    json.dump(ranked, f, indent=2)

print(f"[OK] Wrote: {urls_txt}")
print(f"[OK] Wrote: {json_out}")

# IndexNow submission via bing
by_host = defaultdict(list)
for item in ranked:
    host = item["url"].split("/")[2]
    by_host[host].append(item["url"])

for host, urls in by_host.items():
    key = "b3901b0f58d0445bb8d15a9e334df58a"
    payload = {
        "host": host,
        "key": key,
        "keyLocation": f"https://{host}/{key}.txt",
        "urlList": urls
    }
    print(f"\nSubmitting {len(urls)} URLs for {host} to www.bing.com/indexnow...")
    try:
        r = requests.post("https://www.bing.com/indexnow", json=payload, timeout=20)
        print(f"  -> www.bing.com status: HTTP {r.status_code} ({r.text or 'Accepted'})")
    except Exception as e:
        print(f"  -> Error: {e}")

print("\n--- ALL RANKED CITATION URLS (STARTING FROM THE TOP) ---")
for r in ranked:
    print(f"[{r['rank']:2d}] (Hits: {r['citations']}) {r['url']}")

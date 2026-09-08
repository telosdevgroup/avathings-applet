import asyncio
import json
import os
from collections import Counter, defaultdict, deque
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

LOG_SOURCES = {
    "AvaScry": r"C:\avascry_data\logs\access.log",
    "VetGems": r"C:\Users\dev\Code\tdg\vetgems-lake\logs\access.log",
    "AvaMinder": r"C:\Users\dev\Code\tdg\avaminder\logs\access.log",
    "AvaSpecs": r"C:\Users\dev\Code\tdg\avaspecs-v2\logs\access.log",
    "VethaGolf": r"C:\Users\dev\Code\tdg\vethagolf-v1\logs\access.log",
}

# In-memory history buffer per site (up to 100,000 lines per site in RAM)
recent_logs_by_site = defaultdict(lambda: deque(maxlen=100000))
recent_logs_all = deque(maxlen=100000)

site_stats = defaultdict(lambda: {
    "sources": Counter(),
    "surfaces": Counter(),
    "formats": Counter(),
    "total": 0
})

citations_list = []
stats_ready = False

def classify_line_fast(line_str: str, site_name: str = ""):
    lower = line_str.lower()
    
    source = "Untrusted Browser"
    tier = "untrusted"
    is_citation = False
    
    # Pre-check: If probing for sensitive files or returning error, it is a scanner regardless of User-Agent
    is_probe_signature = (
        any(k in lower for k in ("docker-compose", "service-account", "amplifyconfiguration", ".env", "wp-login", "wp-admin", "xmlrpc.php", "/api/env", "/_environment", "/webroot/"))
        or (" 404 " in line_str and not any(k in lower for k in ("/printing/", "/similar/", "/company/", "/practice/", "/artist/")))
        or " 403 " in line_str
    )

    if is_probe_signature:
        source = "Security Scanners / Probes"
        tier = "scanner"
    elif " 136.32.78." in line_str:
        source = "Dev: You (136.x)"
        tier = "internal"
    elif "siteblaster" in lower:
        source = "SiteBlaster 9001"
        tier = "internal"
    # TARGETS: CITATIONS (Live user prompts on valid content)
    elif "chatgpt-user" in lower:
        source = "ChatGPT: User (Live Citation)"
        tier = "citation"
        is_citation = True
    elif "claude-user" in lower:
        source = "Claude: User (Live Citation)"
        tier = "citation"
        is_citation = True
    elif "perplexity-user" in lower:
        source = "Perplexity: User (Live Citation)"
        tier = "citation"
        is_citation = True
    # TARGETS: SEARCH
    elif "oai-search" in lower:
        source = "OpenAI: Search Index"
        tier = "search"
    elif "claude-search" in lower:
        source = "Claude: Search Index"
        tier = "search"
    elif "googlebot-image" in lower:
        source = "Google: Image Search"
        tier = "search"
    elif "googleother" in lower:
        source = "Google: Other / Features"
        tier = "search"
    elif "googlebot" in lower:
        source = "Google: Web Search"
        tier = "search"
    elif "bingbot" in lower:
        source = "Bingbot: Search Index"
        tier = "search"
    # LEECHES
    elif "shapbot" in lower or "cloud:spider" in lower:
        source = "ShapBot: Scraper (No Citations)"
        tier = "leech"
    elif "perplexity" in lower:
        source = "Perplexity: Model Training"
        tier = "leech"
    elif "claudebot" in lower or "ai:claude" in lower:
        source = "Claude: Model Training"
        tier = "leech"
    elif "gptbot" in lower or "ai:openai" in lower:
        source = "OpenAI: Model Training"
        tier = "leech"
    elif "meta" in lower or "facebook" in lower or "meta-externalagent" in lower:
        source = "Meta AI: Model Training"
        tier = "leech"
    elif "amazonbot" in lower or "amazon" in lower:
        source = "Amazon: Model Training"
        tier = "leech"
    elif "applebot" in lower or "apple" in lower:
        source = "Apple: Model Training"
        tier = "leech"
    elif "ccbot" in lower:
        source = "Common Crawl"
        tier = "leech"
    elif any(k in lower for k in ("testclient", "werkzeug", "dev:script", "crusader")):
        source = "Local Dev / Tests"
        tier = "internal"
    elif any(k in lower for k in ("probe", "scanner", "shield", "wordpress")):
        source = "Security Scanners / Probes"
        tier = "scanner"
    elif "bot:aws" in lower or "[bot:aws]" in lower:
        source = "Scraper (AWS Bot)"
        tier = "leech"
    elif "[scraper:" in lower or "[cloud:" in lower:
        prefix = "[scraper:" if "[scraper:" in lower else "[cloud:"
        idx1 = lower.find(prefix) + len(prefix)
        idx2 = lower.find("]", idx1)
        s_name = line_str[idx1:idx2].strip() if idx2 > idx1 else "Cloud"
        source = f"Scraper ({s_name})"
        tier = "leech"
    elif "[browser:" in lower:
        idx1 = lower.find("[browser:") + 9
        idx2 = lower.find("]", idx1)
        b_name = line_str[idx1:idx2].strip() if idx2 > idx1 else "Generic"
        source = f"Browser ({b_name})"
        tier = "browser"

    # Surface & Route Extraction
    surface = None
    route = "/"
    method = "GET"
    arr_arrow = line_str.split(" -> ")
    if len(arr_arrow) > 1:
        req_part = arr_arrow[1].strip()
        parts = req_part.split(" ")
        method = parts[0] if len(parts) > 0 else "GET"
        route = parts[1] if len(parts) > 1 else "/"
        p = route
        p_lower = p.lower()

        # Discard probe, scanner, and infrastructure garbage from surfaces
        is_surface_garbage = (
            tier == "scanner"
            or any(p_lower.startswith(k) for k in (
                "/.git", "//", "/wp-", "/wordpress", "/robots.txt", 
                "/favicon.ico", "/manifest.json", "/llms", "/.env", 
                "/admin", "/config", "/api/env", "/_environment"
            ))
        )

        if not is_surface_garbage:
            if p == "/" or p == "":
                surface = "/"
            else:
                clean_p = p.split("?")[0]
                slash_parts = clean_p.split("/")
                first_part = slash_parts[1] if len(slash_parts) > 1 else ""
                if first_part and not first_part.startswith("."):
                    surface = f"/{first_part}/*"

    # Format
    fmt = "HTML Pages"
    if "[JSON]" in line_str or ".json" in lower:
        fmt = "JSON (.json)"
    elif "[CSV]" in line_str or ".csv" in lower:
        fmt = "CSV (.csv)"
    elif "[MD]" in line_str or ".md" in lower:
        fmt = "Markdown (.md)"
    elif "[XML]" in line_str or ".xml" in lower:
        fmt = "XML (.xml)"
    elif any(ext in lower for ext in (".jpg", ".png", ".webp", ".gif")):
        fmt = "Images (JPG/PNG)"
    elif "[OTHR]" in line_str:
        fmt = "Other / Assets"

    # Timestamp extraction (ISO at start of line)
    timestamp = line_str[:26] if len(line_str) >= 26 else ""

    if is_citation and site_name:
        p_lower = route.lower()
        is_infra_or_probe = (
            any(k in p_lower for k in (
                "docker-compose", "service-account", "amplify", ".env", "wp-", 
                "config", "admin", "secret", "token", "aws", "credentials",
                "robots.txt", "sitemap", "favicon.ico", ".well-known"
            ))
            or " 404 " in line_str
            or " 403 " in line_str
            or route in ("/", "")
            or route.startswith("/?")
        )

        # ONLY genuine content citations enter the Citations Ledger!
        if not is_infra_or_probe:
            citations_list.append({
                "site": site_name,
                "source": source,
                "route": route,
                "surface": surface,
                "format": fmt,
                "method": method,
                "timestamp": timestamp,
                "raw": line_str
            })

    return (source, tier), surface, fmt

async def async_ingest_all():
    global stats_ready
    loop = asyncio.get_running_loop()
    
    def worker():
        for site, path in LOG_SOURCES.items():
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    (src, tier), surface, fmt = classify_line_fast(line_str, site)
                    
                    recent_logs_by_site[site].append(line_str)
                    recent_logs_all.append((site, line_str))

                    site_stats[site]["sources"][(src, tier)] += 1
                    if surface:
                        site_stats[site]["surfaces"][surface] += 1
                    site_stats[site]["formats"][fmt] += 1
                    site_stats[site]["total"] += 1
                    
                    site_stats["ALL"]["sources"][(src, tier)] += 1
                    if surface:
                        site_stats["ALL"]["surfaces"][surface] += 1
                    site_stats["ALL"]["formats"][fmt] += 1
                    site_stats["ALL"]["total"] += 1

    await loop.run_in_executor(None, worker)
    stats_ready = True
    print(f"Stats ready: {site_stats['ALL']['total']:,} total requests, {len(citations_list)} citations loaded.")

subscribers: set[asyncio.Queue] = set()
tasks: list[asyncio.Task] = []

async def tail_file(site_name: str, file_path: str):
    try:
        while True:
            if not os.path.exists(file_path):
                await asyncio.sleep(1)
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(0, os.SEEK_END)
                    while True:
                        line = f.readline()
                        if line:
                            line_str = line.strip()
                            (src, tier), surface, fmt = classify_line_fast(line_str, site_name)
                            
                            recent_logs_by_site[site_name].append(line_str)
                            recent_logs_all.append((site_name, line_str))

                            site_stats[site_name]["sources"][(src, tier)] += 1
                            if surface:
                                site_stats[site_name]["surfaces"][surface] += 1
                            site_stats[site_name]["formats"][fmt] += 1
                            site_stats[site_name]["total"] += 1
                            
                            site_stats["ALL"]["sources"][(src, tier)] += 1
                            if surface:
                                site_stats["ALL"]["surfaces"][surface] += 1
                            site_stats["ALL"]["formats"][fmt] += 1
                            site_stats["ALL"]["total"] += 1
                            
                            payload = json.dumps({
                                "site": site_name,
                                "raw": line_str
                            })
                            for queue in list(subscribers):
                                try:
                                    queue.put_nowait(payload)
                                except asyncio.QueueFull:
                                    pass
                        else:
                            await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(async_ingest_all())
    for site_name, path in LOG_SOURCES.items():
        tasks.append(asyncio.create_task(tail_file(site_name, path)))
    yield
    for t in tasks:
        t.cancel()

app = FastAPI(title="Ava Log Stream Watcher", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def event_generator(site_filter: str = "ALL") -> AsyncGenerator[str, None]:
    queue: asyncio.Queue = asyncio.Queue(maxsize=2000)
    subscribers.add(queue)
    try:
        yield f"event: ping\ndata: {json.dumps({'status': 'connected'})}\n\n"

        # Replay generous initial lines from RAM so the user never sees an empty screen!
        if site_filter != "ALL" and site_filter in recent_logs_by_site:
            hist = list(recent_logs_by_site[site_filter])[-500:]
            for raw_line in hist:
                yield f"data: {json.dumps({'site': site_filter, 'raw': raw_line})}\n\n"
        else:
            # Replay recent 500 lines across all sites
            hist = list(recent_logs_all)[-500:]
            for s_name, raw_line in hist:
                yield f"data: {json.dumps({'site': s_name, 'raw': raw_line})}\n\n"

        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=1.0)
                yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        subscribers.discard(queue)

@app.get("/stream")
async def stream(site: str = "ALL"):
    return StreamingResponse(
        event_generator(site),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@app.get("/api/stats")
async def get_stats():
    if not stats_ready:
        return JSONResponse({"loading": True})
    
    result = {}
    for site_key, data in site_stats.items():
        def source_sort_key(item):
            (name, tier), count = item
            tier_priority = {
                "citation": 0,
                "search": 1,
                "internal": 2,
                "leech": 3,
                "browser": 4,
                "scanner": 5,
                "untrusted": 6
            }.get(tier, 9)
            return (tier_priority, -count)

        sorted_sources = [
            {"name": name, "tier": tier, "count": count}
            for (name, tier), count in sorted(data["sources"].items(), key=source_sort_key)
        ]
        
        sorted_surfaces = [
            {"name": k, "count": v}
            for k, v in data["surfaces"].most_common(25)
        ]
        
        sorted_formats = [
            {"name": k, "count": v}
            for k, v in data["formats"].most_common(12)
        ]
        
        result[site_key] = {
            "total": data["total"],
            "sources": sorted_sources,
            "surfaces": sorted_surfaces,
            "formats": sorted_formats
        }
    return JSONResponse(result)

@app.get("/api/citations")
async def get_citations():
    """Returns detailed citation records and top-cited leaderboard."""
    if not stats_ready:
        return JSONResponse({"loading": True})
    
    # Leaderboard of top cited routes
    route_counts = Counter()
    for c in citations_list:
        route_counts[(c["site"], c["route"])] += 1

    leaderboard = [
        {"site": s, "route": r, "count": count}
        for (s, r), count in route_counts.most_common(50)
    ]

    # Return reverse chronological (newest first)
    return JSONResponse({
        "total": len(citations_list),
        "leaderboard": leaderboard,
        "items": list(reversed(citations_list))
    })

@app.get("/api/recent")
async def get_recent_logs(site: str = "ALL", limit: int = 1000):
    """Returns recent lines from in-memory RAM buffer for instant client hydration."""
    if site != "ALL" and site in recent_logs_by_site:
        raw_items = list(recent_logs_by_site[site])[-limit:]
        items = [{"site": site, "raw": line} for line in raw_items]
    else:
        raw_items = list(recent_logs_all)[-limit:]
        items = [{"site": s, "raw": line} for s, line in raw_items]
    return JSONResponse({"site": site, "count": len(items), "lines": items})

@app.get("/citations", response_class=HTMLResponse)
async def serve_citations():
    html_path = os.path.join(os.path.dirname(__file__), "citations.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>citations.html not found</h1>"

@app.get("/stats", response_class=HTMLResponse)
async def serve_stats():
    html_path = os.path.join(os.path.dirname(__file__), "stats.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>stats.html not found</h1>"

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    html_path = os.path.join(os.path.dirname(__file__), "log_stream.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>log_stream.html not found</h1>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("log_stream:app", host="127.0.0.1", port=8000, reload=False, timeout_graceful_shutdown=0)

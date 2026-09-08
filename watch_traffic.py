#!/usr/bin/env python3
"""
AvaThings Unified Terminal Traffic Watcher 2.0
Multi-site modular live traffic watcher across all Telos ecosystem sites:
  AvaScry (MTG, NEC, DOM, SWU), AvaSpecs, VetGems, AvaMinder, and VethaGolf.
"""

import os
import sys
import time
import threading
from collections import deque, Counter, defaultdict
from datetime import datetime

# Windows ANSI / non-blocking keypress
if os.name == 'nt':
    os.system('')
try:
    import msvcrt
except ImportError:
    msvcrt = None

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from sites import ALL_PARSERS, SITE_REGISTRY, FORMAT_BADGES
from sites.base import CYAN, GREEN, YELLOW, RED, BLUE, MAGENTA, ORANGE, BOLD, DIM, RESET

class TrafficHub:
    def __init__(self):
        self.site_filter = "ALL"        # "ALL", "avascry", "avaspecs", "vetgems", "avaminder", "vethagolf"
        self.avascry_sub_filter = "ALL" # "ALL", "MTG", "NEC", "DOM", "SWU"
        # Keep generous queues in RAM - 500,000 hits per queue (~1GB RAM headroom)
        self.recent_hits = deque(maxlen=500000)
        self.site_recent_hits = defaultdict(lambda: deque(maxlen=500000))
        self.subsite_recent_hits = defaultdict(lambda: deque(maxlen=500000))
        self.total_requests = 0

        # Stats counters
        self.source_counts = Counter()
        self.surface_counts = Counter()
        self.format_counts = Counter()
        self.site_counts = Counter()
        self.subsite_counts = Counter()

    def add_hit(self, hit: dict):
        self.total_requests += 1
        self.recent_hits.appendleft(hit)

        site = hit["site"]
        sub = hit.get("subsite", "")
        caller = hit["caller_name"]
        surf = hit["surface_code"]
        fmt = hit["format_code"]

        self.site_recent_hits[site].appendleft(hit)
        if sub:
            self.subsite_recent_hits[sub].appendleft(hit)

        self.site_counts[site] += 1
        if sub:
            self.subsite_counts[sub] += 1

        self.source_counts[(site, sub, caller)] += 1
        self.surface_counts[(site, sub, surf)] += 1
        self.format_counts[(site, sub, fmt)] += 1

    def reset(self):
        self.recent_hits.clear()
        self.site_recent_hits.clear()
        self.subsite_recent_hits.clear()
        self.total_requests = 0
        self.source_counts.clear()
        self.surface_counts.clear()
        self.format_counts.clear()
        self.site_counts.clear()
        self.subsite_counts.clear()

def tail_parser_worker(parser, hub: TrafficHub):
    """Continuously tails the log file for a specific site parser."""
    path = parser.default_log_path
    while not os.path.exists(path):
        time.sleep(1)

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            # Seed generously from the log file (up to 25MB or entire file if smaller)
            f.seek(0, os.SEEK_END)
            size = f.tell()
            seek_bytes = min(size, 25 * 1024 * 1024)
            seek_pos = max(0, size - seek_bytes)
            f.seek(seek_pos)
            if seek_pos > 0:
                f.readline() # drop partial line

            for seed_line in f:
                line_str = seed_line.strip()
                if line_str:
                    hit = parser.parse_line(line_str)
                    if hit:
                        hub.add_hit(hit)

            while True:
                line = f.readline()
                if line:
                    line_str = line.strip()
                    if line_str:
                        hit = parser.parse_line(line_str)
                        if hit:
                            hub.add_hit(hit)
                else:
                    time.sleep(0.08)
    except Exception:
        time.sleep(1)

def pad_str(s: str, w: int) -> str:
    """Pad string taking into account plain character length."""
    return s[:w].ljust(w)

def render_screen(hub: TrafficHub):
    lines = []
    lines.append(f"{CYAN}{BOLD}===================================================================================================={RESET}")
    lines.append(f"  {BOLD}⚡ AVATHINGS UNIFIED TRAFFIC WATCHER 2.0{RESET}  |  {DIM}(Press [1-6] Filter | [r] Reset | [q] Quit){RESET}")
    lines.append(f"{CYAN}===================================================================================================={RESET}")

    # Top KPI Bar
    tot_scry = hub.site_counts['avascry']
    tot_specs = hub.site_counts['avaspecs']
    tot_vet = hub.site_counts['vetgems']
    tot_mndr = hub.site_counts['avaminder']
    tot_golf = hub.site_counts['vethagolf']
    
    lines.append(
        f"  {BOLD}TOTAL:{RESET} {GREEN}{hub.total_requests:,}{RESET}  |  "
        f"{YELLOW}AvaScry:{RESET} {tot_scry:,} "
        f"({YELLOW}MTG:{hub.subsite_counts['MTG']}{RESET} {RED}NEC:{hub.subsite_counts['NEC']}{RESET} {CYAN}DOM:{hub.subsite_counts['DOM']}{RESET} {MAGENTA}SWU:{hub.subsite_counts['SWU']}{RESET} {GREEN}MC:{hub.subsite_counts['MINE']}{RESET})  |  "
        f"{ORANGE}Specs:{RESET} {tot_specs:,}  |  "
        f"{GREEN}VetGems:{RESET} {tot_vet:,}  |  "
        f"{MAGENTA}Minder:{RESET} {tot_mndr:,}  |  "
        f"{GREEN}Golf:{RESET} {tot_golf:,}"
    )
    lines.append(f"{CYAN}----------------------------------------------------------------------------------------------------{RESET}")

    # 3-Column Spectrum: Sources | Surfaces | Formats
    lines.append(f"  {BOLD}{'TOP TRAFFIC SOURCES':<30} | {'TOP SURFACES / ROUTES':<30} | {'CONTENT FORMAT':<30}{RESET}")
    lines.append(f"  {'-'*30} | {'-'*30} | {'-'*30}")

    # Aggregate stats based on active filter
    src_map = Counter()
    surf_map = Counter()
    for (s, sub, caller), count in hub.source_counts.items():
        if hub.site_filter == "ALL" or hub.site_filter == s:
            if s == "avascry" and hub.avascry_sub_filter != "ALL" and hub.avascry_sub_filter != sub:
                continue
            src_map[caller] += count

    for (s, sub, surf), count in hub.surface_counts.items():
        if hub.site_filter == "ALL" or hub.site_filter == s:
            if s == "avascry" and hub.avascry_sub_filter != "ALL" and hub.avascry_sub_filter != sub:
                continue
            surf_map[f"[{surf}]"] += count

    fmt_map = Counter()
    for (s, sub, fmt), count in hub.format_counts.items():
        if hub.site_filter == "ALL" or hub.site_filter == s:
            if s == "avascry" and hub.avascry_sub_filter != "ALL" and hub.avascry_sub_filter != sub:
                continue
            fmt_map[fmt] += count

    top_src = src_map.most_common(7)
    top_surf = surf_map.most_common(7)
    top_fmt = fmt_map.most_common(7)

    max_rows = max(len(top_src), len(top_surf), len(top_fmt), 1)
    for i in range(max_rows):
        col1 = f"● {top_src[i][0][:20]:<20} {top_src[i][1]:>6,}" if i < len(top_src) else ""
        col2 = f"● {top_surf[i][0][:20]:<20} {top_surf[i][1]:>6,}" if i < len(top_surf) else ""
        col3 = f"● {top_fmt[i][0].upper()[:20]:<20} {top_fmt[i][1]:>6,}" if i < len(top_fmt) else ""
        lines.append(f"  {col1:<30} | {col2:<30} | {col3:<30}")

    lines.append(f"{CYAN}----------------------------------------------------------------------------------------------------{RESET}")

    # Filter Status & Hotkey Helper
    filter_label = hub.site_filter.upper()
    if hub.site_filter == "avascry" and hub.avascry_sub_filter != "ALL":
        filter_label += f" ({hub.avascry_sub_filter})"
    lines.append(f"  {BOLD}⚡ LIVE STREAM FEED — ACTIVE FILTER:{RESET} {YELLOW}{filter_label}{RESET}  {DIM}(Press [1] All | [2] AvaScry | [3] Specs | [4] Vet | [5] Minder | [6] Golf){RESET}")
    lines.append(f"{CYAN}----------------------------------------------------------------------------------------------------{RESET}")

    # Render Live Stream Hits directly from the appropriate queue
    try:
        term_height = os.get_terminal_size().lines
        # Header + top stats take ~16 lines, reserve 2 lines at bottom
        max_feed_lines = max(24, term_height - 18)
    except Exception:
        max_feed_lines = 32

    # Select dedicated queue based on active filter
    if hub.site_filter == "ALL":
        target_queue = hub.recent_hits
    elif hub.site_filter == "avascry" and hub.avascry_sub_filter != "ALL":
        target_queue = hub.subsite_recent_hits[hub.avascry_sub_filter]
    else:
        target_queue = hub.site_recent_hits[hub.site_filter]

    rendered = 0
    for hit in target_queue:
        if rendered >= max_feed_lines:
            break

        site_b = hit["site_badge"]
        caller_b = hit["caller_badge"]
        lat = f"({hit['latency']:3d}ms)" if hit['latency'] else "  -   "
        surf_b = hit["surface_badge"]
        fmt_b = FORMAT_BADGES.get(hit["format_code"], f"{DIM}[OTHR]{RESET}")
        method = hit.get("method", "GET")
        path = hit["path"][:50]

        lines.append(f"  {site_b} {caller_b} {lat} {surf_b} {fmt_b} -> {method} {path}")
        rendered += 1

    if rendered == 0:
        lines.append(f"\n  {DIM}Waiting for traffic matching filter '{filter_label}'...{RESET}\n")

    lines.append(f"{CYAN}===================================================================================================={RESET}")

    # Output to terminal
    sys.stdout.write("\033[H\033[J" + "\n".join(lines) + "\n")
    sys.stdout.flush()

def handle_keys(hub: TrafficHub):
    """Non-blocking keyboard controls."""
    if not msvcrt:
        return

    scry_cycle = ["ALL", "MTG", "NEC", "DOM", "SWU", "MINE"]
    while True:
        try:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in (b'q', b'Q', b'\x03'):
                    sys.exit(0)
                elif ch == b'1':
                    hub.site_filter = "ALL"
                    hub.avascry_sub_filter = "ALL"
                elif ch == b'2':
                    if hub.site_filter != "avascry":
                        hub.site_filter = "avascry"
                        hub.avascry_sub_filter = "ALL"
                    else:
                        # Cycle through sub-sites
                        curr_idx = scry_cycle.index(hub.avascry_sub_filter) if hub.avascry_sub_filter in scry_cycle else 0
                        hub.avascry_sub_filter = scry_cycle[(curr_idx + 1) % len(scry_cycle)]
                elif ch == b'3':
                    hub.site_filter = "avaspecs"
                elif ch == b'4':
                    hub.site_filter = "vetgems"
                elif ch == b'5':
                    hub.site_filter = "avaminder"
                elif ch == b'6':
                    hub.site_filter = "vethagolf"
                elif ch in (b'r', b'R'):
                    hub.reset()
        except Exception:
            pass
        time.sleep(0.04)

def main():
    hub = TrafficHub()

    # Start a background tailer thread for each site parser
    for parser in ALL_PARSERS:
        t = threading.Thread(target=tail_parser_worker, args=(parser, hub), daemon=True)
        t.start()

    # Start keyboard handling thread
    k_thread = threading.Thread(target=handle_keys, args=(hub,), daemon=True)
    k_thread.start()

    # Main UI render loop (10-15 fps refresh rate)
    try:
        while True:
            render_screen(hub)
            time.sleep(0.12)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    main()

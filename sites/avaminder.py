import re
from .base import (
    BaseSiteParser,
    YELLOW, CYAN, MAGENTA, RED, GREEN, BLUE, BOLD, DIM, RESET
)

class AvaMinderParser(BaseSiteParser):
    site_key = "avaminder"
    display_name = "AvaMinder"
    default_log_path = r"C:\Users\dev\Code\tdg\avaminder\logs\access.log"
    site_badge = f"{MAGENTA}{BOLD}[MNDR]{RESET}"

    SURFACE_BADGES = {
        "WAIT": f"{GREEN}{BOLD}[WAIT]{RESET}",
        "API":  f"{YELLOW}{BOLD}[API ]{RESET}",
        "DOCS": f"{MAGENTA}[DOCS]{RESET}",
        "SHLD": f"{RED}[SHLD]{RESET}",
        "ASST": f"{DIM}[ASST]{RESET}",
        "HOME": f"{CYAN}[HOME]{RESET}",
        "OTHR": f"{DIM}[OTHR]{RESET}",
    }

    LINE_REGEX = re.compile(
        r'^(?P<ts>\S+)\s+(?P<ip>\S+)\s+(?P<badge>\[[^\]]+\])\s+(?P<status>\d{3})\s+\(\s*(?P<lat>\d+)ms\)(?P<tags>(?:\s+\[[^\]]*\])*)\s+->\s+(?P<method>[A-Z]+)\s+(?P<path>\S+)'
    )

    def parse_line(self, line: str) -> dict:
        m = self.LINE_REGEX.match(line)
        if not m:
            return None

        path = m.group("path")
        clean_p = path.split("?")[0].lower()

        if clean_p.startswith("/waitlist"):
            surf = "WAIT"
        elif clean_p.startswith("/api/"):
            surf = "API"
        elif clean_p.startswith("/docs"):
            surf = "DOCS"
        elif clean_p.startswith("/shield") or "shield" in clean_p:
            surf = "SHLD"
        elif clean_p.startswith(("/static/", "/assets/")):
            surf = "ASST"
        elif clean_p in ("/", "/index", "/home"):
            surf = "HOME"
        else:
            surf = "OTHR"

        tags_str = m.group("tags") or ""
        caller_name, caller_badge = self.classify_caller(m.group("badge"), line)
        format_code = self.classify_format(path, tags_str)
        lat = int(m.group("lat")) if m.group("lat") else 0

        return {
            "site": self.site_key,
            "subsite": "MNDR",
            "site_badge": self.site_badge,
            "caller_name": caller_name,
            "caller_badge": caller_badge,
            "latency": lat,
            "surface_code": surf,
            "surface_badge": self.SURFACE_BADGES.get(surf, self.SURFACE_BADGES["OTHR"]),
            "format_code": format_code,
            "method": m.group("method"),
            "path": path,
            "status": int(m.group("status")),
            "ts": m.group("ts"),
            "raw": line
        }

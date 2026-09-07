import re
from .base import (
    BaseSiteParser,
    YELLOW, CYAN, MAGENTA, RED, GREEN, BLUE, BOLD, DIM, RESET
)

class VetGemsParser(BaseSiteParser):
    site_key = "vetgems"
    display_name = "VetGems"
    default_log_path = r"C:\Users\dev\Code\tdg\vetgems-lake\logs\access.log"
    site_badge = f"{GREEN}{BOLD}[VET ]{RESET}"

    SURFACE_BADGES = {
        "PRACT": f"{GREEN}{BOLD}[PRAC]{RESET}",
        "SRCH":  f"{CYAN}[SRCH]{RESET}",
        "CITY":  f"{BLUE}[CITY]{RESET}",
        "STTE":  f"{YELLOW}[STTE]{RESET}",
        "LLMS":  f"{MAGENTA}[LLMS]{RESET}",
        "HOME":  f"{CYAN}[HOME]{RESET}",
        "OTHR":  f"{DIM}[OTHR]{RESET}",
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

        if clean_p.startswith(("/practice/", "/vet/")):
            surf = "PRACT"
        elif clean_p.startswith("/search") or clean_p.startswith("/find"):
            surf = "SRCH"
        elif clean_p.startswith("/city/"):
            surf = "CITY"
        elif clean_p.startswith("/state/"):
            surf = "STTE"
        elif clean_p.startswith("/llms"):
            surf = "LLMS"
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
            "subsite": "VET",
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

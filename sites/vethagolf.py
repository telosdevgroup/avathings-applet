import re
from .base import (
    BaseSiteParser,
    YELLOW, CYAN, MAGENTA, RED, GREEN, BLUE, BOLD, DIM, RESET
)

class VethaGolfParser(BaseSiteParser):
    site_key = "vethagolf"
    display_name = "VethaGolf"
    default_log_path = r"C:\Users\dev\Code\tdg\vethagolf-v1\logs\access.log"
    site_badge = f"{GREEN}{BOLD}[GOLF]{RESET}"

    SURFACE_BADGES = {
        "VENU": f"{GREEN}{BOLD}[VENU]{RESET}",
        "SRCH": f"{CYAN}[SRCH]{RESET}",
        "API":  f"{YELLOW}[API ]{RESET}",
        "LLMS": f"{MAGENTA}[LLMS]{RESET}",
        "HOME": f"{CYAN}[HOME]{RESET}",
        "ASST": f"{DIM}[ASST]{RESET}",
        "OTHR": f"{DIM}[OTHR]{RESET}",
    }

    # Custom log regex matching:
    # 2026-09-07T14:30:18.620746+00:00 66.249.68.105 [Googlebot] 200 (  5ms) [VENU] [HTML] -> GET /venue/hillside-golf-course
    LINE_REGEX_TAGGED = re.compile(
        r'^(?P<ts>\S+)\s+(?P<ip>\S+)\s+(?P<badge>\[[^\]]+\])\s+(?P<status>\d{3})\s+\(\s*(?P<lat>\d+)ms\)(?P<tags>(?:\s+\[[^\]]*\])*)\s+->\s+(?P<method>[A-Z]+)\s+(?P<path>\S+)'
    )

    # Legacy/Apache fallback matching:
    # 66.249.76.44 - - [06/Sep/2026:20:53:23 +0000] "GET /" 200 - "Mozilla/..."
    LINE_REGEX_APACHE = re.compile(
        r'^(?P<ip>\S+)\s+-\s+-\s+\[(?P<ts>[^\]]+)\]\s+"(?P<method>[A-Z]+)\s+(?P<path>[^\s"]+)[^"]*"\s+(?P<status>\d{3})\s+\S+\s+"(?P<ua>[^"]*)"'
    )

    def parse_line(self, line: str) -> dict:
        m = self.LINE_REGEX_TAGGED.match(line)
        if m:
            path = m.group("path")
            tags_str = m.group("tags") or ""
            caller_badge = m.group("badge")
            caller_name, col_caller = self.classify_caller(caller_badge, line)
            lat = int(m.group("lat")) if m.group("lat") else 0
            method = m.group("method")
            status = int(m.group("status"))
            ts = m.group("ts")

            # Extract surface
            tokens = re.findall(r'\[([A-Z0-9_\s]{2,5})\]', tags_str)
            surf = ""
            for t in tokens:
                t_clean = t.strip().upper()
                if t_clean in self.SURFACE_BADGES:
                    surf = t_clean
                    break
            if not surf:
                surf = self._infer_surface(path)
            format_code = self.classify_format(path, tags_str)
        else:
            m_ap = self.LINE_REGEX_APACHE.match(line)
            if not m_ap:
                return None
            path = m_ap.group("path")
            ua = m_ap.group("ua") or ""
            caller_name, col_caller = self.classify_caller("", ua)
            lat = 0
            method = m_ap.group("method")
            status = int(m_ap.group("status"))
            ts = m_ap.group("ts")
            surf = self._infer_surface(path)
            format_code = self.classify_format(path)

        return {
            "site": self.site_key,
            "subsite": "GOLF",
            "site_badge": self.site_badge,
            "caller_name": caller_name,
            "caller_badge": col_caller,
            "latency": lat,
            "surface_code": surf,
            "surface_badge": self.SURFACE_BADGES.get(surf, self.SURFACE_BADGES["OTHR"]),
            "format_code": format_code,
            "method": method,
            "path": path,
            "status": status,
            "ts": ts,
            "raw": line
        }

    def _infer_surface(self, path: str) -> str:
        clean_p = path.split("?")[0].lower()
        if clean_p.startswith("/venue/"):
            return "VENU"
        elif clean_p.startswith("/search") or clean_p.startswith("/find"):
            return "SRCH"
        elif clean_p.startswith("/api/"):
            return "API"
        elif clean_p.startswith("/llms"):
            return "LLMS"
        elif clean_p in ("/", "/index", "/home"):
            return "HOME"
        elif clean_p.startswith("/static/") or clean_p.endswith((".css", ".js", ".svg", ".ico")):
            return "ASST"
        return "OTHR"

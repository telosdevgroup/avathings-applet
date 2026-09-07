import re
from .base import (
    BaseSiteParser,
    YELLOW, CYAN, MAGENTA, RED, GREEN, BLUE, BOLD, DIM, RESET
)

class AvaScryParser(BaseSiteParser):
    site_key = "avascry"
    display_name = "AvaScry Network"
    default_log_path = r"C:\avascry_data\logs\access.log"

    # 4 Sub-site badges
    SUBSITE_BADGES = {
        "MTG": f"{YELLOW}{BOLD}[MTG ]{RESET}",
        "NEC": f"{RED}{BOLD}[NEC ]{RESET}",
        "DOM": f"{CYAN}{BOLD}[DOM ]{RESET}",
        "SWU": f"{MAGENTA}{BOLD}[SWU ]{RESET}",
    }

    SURFACE_BADGES = {
        "PRIN": f"{GREEN}{BOLD}[PRIN]{RESET}",
        "SIM":  f"{MAGENTA}{BOLD}[SIM ]{RESET}",
        "VECT": f"{CYAN}{BOLD}[VECT]{RESET}",
        "ARTS": f"{BLUE}{BOLD}[ARTS]{RESET}",
        "SETS": f"{YELLOW}[SETS]{RESET}",
        "CMDR": f"{YELLOW}{BOLD}[CMDR]{RESET}",
        "WEAP": f"{RED}{BOLD}[WEAP]{RESET}",
        "TRAT": f"{YELLOW}[TRAT]{RESET}",
        "HOUS": f"{MAGENTA}[HOUS]{RESET}",
        "SKIL": f"{BLUE}[SKIL]{RESET}",
        "CARD": f"{CYAN}{BOLD}[CARD]{RESET}",
        "EXPN": f"{YELLOW}[EXPN]{RESET}",
        "IMG":  f"{BLUE}[IMG ]{RESET}",
        "LLMS": f"{MAGENTA}[LLMS]{RESET}",
        "HOME": f"{CYAN}[HOME]{RESET}",
        "OTHR": f"{DIM}[OTHR]{RESET}",
    }

    # Matches lines with optional [SUBSITE] tag
    LINE_REGEX = re.compile(
        r'^(?P<ts>\S+)\s+(?P<ip>\S+)\s+(?P<badge>\[[^\]]+\])\s+(?:\[(?P<subsite>[A-Z0-9_\s]{2,5})\]\s+)?(?P<status>\d{3})\s+\(\s*(?P<lat>\d+)ms\)(?P<tags>(?:\s+\[[^\]]*\])*)\s+->\s+(?P<method>[A-Z]+)\s+(?P<path>\S+)'
    )

    def parse_line(self, line: str) -> dict:
        m = self.LINE_REGEX.match(line)
        if not m:
            return None

        path = m.group("path")
        sub_raw = (m.group("subsite") or "").strip().upper()
        clean_p = path.split("?")[0].lower()

        # 1. Determine subsite (MTG, NEC, DOM, SWU)
        if sub_raw in self.SUBSITE_BADGES:
            subsite = sub_raw
        elif clean_p.startswith("/necromunda"):
            subsite = "NEC"
        elif clean_p.startswith("/dominion"):
            subsite = "DOM"
        elif clean_p.startswith("/swu"):
            subsite = "SWU"
        else:
            subsite = "MTG"

        # 2. Extract surface from tags or path
        tags_str = m.group("tags") or ""
        tag_tokens = re.findall(r'\[([A-Z0-9_\s]{2,5})\]', tags_str)
        raw_surf = ""
        for t in tag_tokens:
            t_clean = t.strip().upper()
            if t_clean in self.SURFACE_BADGES:
                raw_surf = t_clean
                break

        if not raw_surf:
            if clean_p.startswith(("/printing/", "/card/")):
                raw_surf = "CARD" if subsite in ("DOM", "SWU") else "PRIN"
            elif clean_p.startswith("/similar/"):
                raw_surf = "SIM"
            elif clean_p.startswith("/vector"):
                raw_surf = "VECT"
            elif clean_p.startswith("/artist/"):
                raw_surf = "ARTS"
            elif clean_p.startswith("/set/") or clean_p in ("/sets", "/set"):
                raw_surf = "SETS"
            elif clean_p.startswith(("/commander", "/commanders")):
                raw_surf = "CMDR"
            elif clean_p.startswith("/weapon/"):
                raw_surf = "WEAP"
            elif clean_p.startswith("/trait/"):
                raw_surf = "TRAT"
            elif clean_p.startswith("/house/"):
                raw_surf = "HOUS"
            elif clean_p.startswith("/skill/"):
                raw_surf = "SKIL"
            elif clean_p.startswith("/images/") or clean_p.endswith((".jpg", ".png", ".webp")):
                raw_surf = "IMG"
            elif clean_p.startswith("/llms"):
                raw_surf = "LLMS"
            elif clean_p in ("/", "/index", "/home", "/favicon.ico"):
                raw_surf = "HOME"
            else:
                raw_surf = "OTHR"

        caller_name, caller_badge = self.classify_caller(m.group("badge"), line)
        format_code = self.classify_format(path, tags_str)
        lat = int(m.group("lat")) if m.group("lat") else 0

        return {
            "site": self.site_key,
            "subsite": subsite,
            "site_badge": self.SUBSITE_BADGES.get(subsite, self.SUBSITE_BADGES["MTG"]),
            "caller_name": caller_name,
            "caller_badge": caller_badge,
            "latency": lat,
            "surface_code": raw_surf,
            "surface_badge": self.SURFACE_BADGES.get(raw_surf, self.SURFACE_BADGES["OTHR"]),
            "format_code": format_code,
            "method": m.group("method"),
            "path": path,
            "status": int(m.group("status")),
            "ts": m.group("ts"),
            "raw": line
        }

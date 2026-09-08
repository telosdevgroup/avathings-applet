# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
ORANGE = "\033[38;5;208m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

FORMAT_BADGES = {
    "html": f"{CYAN}[HTML]{RESET}",
    "md":   f"{MAGENTA}{BOLD}[MD  ]{RESET}",
    "json": f"{YELLOW}[JSON]{RESET}",
    "xml":  f"{YELLOW}{BOLD}[XML ]{RESET}",
    "csv":  f"{GREEN}{BOLD}[CSV ]{RESET}",
    "img":  f"{BLUE}[IMG ]{RESET}",
    "txt":  f"{YELLOW}[TXT ]{RESET}",
    "css":  f"{BLUE}[CSS ]{RESET}",
    "js":   f"{BLUE}[JS  ]{RESET}",
    "other": f"{DIM}[OTHR]{RESET}",
}

class BaseSiteParser:
    site_key = "base"
    display_name = "Base"
    default_log_path = ""
    site_badge = f"{DIM}[BASE]{RESET}"

    def parse_line(self, line: str) -> dict:
        """Parse raw log line into normalized dictionary record."""
        raise NotImplementedError

    def classify_caller(self, badge: str, lower_line: str) -> tuple[str, str]:
        """Classify caller into (caller_display, colorized_badge)."""
        raw_b = badge.strip("[] ") if badge else ""
        low_b = raw_b.lower()
        low_l = lower_line.lower()

        # Known search crawlers & leeches
        # Google brand colors: G(blue), o(red), o(yellow), g(blue), l(green), e(red)
        _g_brand = f"{BLUE}G{RESET}{RED}o{RESET}{YELLOW}o{RESET}{BLUE}g{RESET}{GREEN}l{RESET}{RED}e{RESET}"
        if "googlebot-image" in low_b or "googlebot-image" in low_l:
            return "Google Images", f"[{_g_brand}:Img]"
        if "googleother" in low_b or "googleother" in low_l:
            return "GoogleOther", f"[{_g_brand}Othr]"
        if "googlebot" in low_b or "googlebot" in low_l or "google" in low_b:
            suffix = raw_b.replace("Google", "").replace("google", "").strip("[] :-_")
            tag_name = f"{_g_brand}{suffix}" if suffix else f"{_g_brand}bot"
            return "Googlebot", f"[{tag_name:<19}]"
        if "bingbot" in low_b or "bing" in low_l:
            return "Bingbot", f"{GREEN}[Bingbot   ]{RESET}"
        if "applebot" in low_b or "apple" in low_b or "apple" in low_l:
            return "AppleBot", f"{CYAN}[AppleBot  ]{RESET}"
        if "amazonbot" in low_b or "amazon" in low_b or "amazon" in low_l:
            return "Amazonbot", f"{YELLOW}[Amazonbot ]{RESET}"
        if "meta" in low_b or "meta-externalagent" in low_l or "facebook" in low_l:
            return "Meta AI", f"{YELLOW}[Meta:AI   ]{RESET}"
        if "claudebot" in low_b or "claude" in low_b:
            return "ClaudeBot", f"{YELLOW}[ClaudeBot ]{RESET}"
        if "gptbot" in low_b or "ai:openai" in low_b or "openai" in low_b:
            return "GPTBot", f"{YELLOW}[GPTBot    ]{RESET}"
        if "perplexity" in low_b or "perplexity" in low_l:
            return "Perplexity", f"{YELLOW}[Perplexity]{RESET}"
        if "shapbot" in low_b or "shapbot" in low_l:
            return "ShapBot", f"{BLUE}[ShapBot   ]{RESET}"
        if "dev:script" in low_b or "testclient" in low_l or "127.0.0.1" in low_l:
            return "Local Dev", f"{DIM}[Local:Dev ]{RESET}"
        if "siteblaster" in low_l:
            return "SiteBlaster", f"{DIM}[Blaster   ]{RESET}"
        if "136.32.78." in low_l:
            return "Dev: You", f"{BLUE}[Dev:You   ]{RESET}"
        if "browser:" in low_b:
            name = raw_b.replace("browser:", "").replace("Browser:", "").strip()[:8]
            return f"Browser ({name})", f"{CYAN}[{name:<10}]{RESET}"
        if "scraper:" in low_b or "cloud:" in low_b:
            name = raw_b.split(":")[-1].strip()[:8]
            return f"Scraper ({name})", f"{YELLOW}[{name:<10}]{RESET}"
        if raw_b:
            return raw_b[:12], f"[{raw_b[:10]:<10}]"
        return "Unknown", f"{DIM}[Unknown   ]{RESET}"

    def classify_format(self, path: str, tags_str: str = "") -> str:
        clean = path.split("?")[0].lower()
        if "[json]" in tags_str.lower() or clean.endswith(".json"):
            return "json"
        if "[csv]" in tags_str.lower() or clean.endswith(".csv"):
            return "csv"
        if "[md]" in tags_str.lower() or clean.endswith(".md"):
            return "md"
        if "[xml]" in tags_str.lower() or clean.endswith(".xml") or "sitemap" in clean:
            return "xml"
        if any(clean.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".ico", ".svg")):
            return "img"
        if clean.endswith(".txt"):
            return "txt"
        if clean.endswith(".css"):
            return "css"
        if clean.endswith(".js"):
            return "js"
        return "html"

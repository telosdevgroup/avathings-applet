from .base import BaseSiteParser, FORMAT_BADGES
from .avascry import AvaScryParser
from .avaspecs import AvaSpecsParser
from .vetgems import VetGemsParser
from .avaminder import AvaMinderParser
from .vethagolf import VethaGolfParser

ALL_PARSERS = [
    AvaScryParser(),
    AvaSpecsParser(),
    VetGemsParser(),
    AvaMinderParser(),
    VethaGolfParser(),
]

SITE_REGISTRY = {p.site_key: p for p in ALL_PARSERS}

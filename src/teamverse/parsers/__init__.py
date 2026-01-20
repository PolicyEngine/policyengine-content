"""Content parsers for various sources."""

from teamverse.parsers.google_docs import GoogleDocsParser, parse_google_doc
from teamverse.parsers.web import WebParser, parse_url
from teamverse.parsers.utils import detect_audience, extract_quotes, extract_key_points

__all__ = [
    "GoogleDocsParser",
    "parse_google_doc",
    "WebParser",
    "parse_url",
    "detect_audience",
    "extract_quotes",
    "extract_key_points",
]

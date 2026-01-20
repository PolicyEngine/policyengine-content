"""Web page content parser."""

import re
from typing import Optional

import httpx

# Optional dependency for HTML parsing
try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# Optional dependency for markdown conversion
try:
    import html2text

    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False


class WebParser:
    """Parser for web page content."""

    def __init__(self, timeout: float = 30.0):
        """Initialize the web parser.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    async def fetch_content(self, url: str) -> str:
        """Fetch content from a URL.

        Args:
            url: Web page URL

        Returns:
            HTML content of the page
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text

    def extract_title(self, html: str) -> str:
        """Extract page title from HTML.

        Args:
            html: HTML content

        Returns:
            Page title or empty string
        """
        if BS4_AVAILABLE:
            soup = BeautifulSoup(html, "html.parser")
            title_tag = soup.find("title")
            if title_tag:
                return title_tag.get_text().strip()
            # Try og:title
            og_title = soup.find("meta", property="og:title")
            if og_title:
                return og_title.get("content", "").strip()
            # Try h1
            h1 = soup.find("h1")
            if h1:
                return h1.get_text().strip()
        else:
            # Simple regex fallback
            match = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def extract_main_content(self, html: str) -> str:
        """Extract main article content from HTML.

        Attempts to find the main content area, excluding navigation,
        headers, footers, and sidebars.

        Args:
            html: HTML content

        Returns:
            Main content text
        """
        if BS4_AVAILABLE:
            soup = BeautifulSoup(html, "html.parser")

            # Remove unwanted elements
            for tag in soup.find_all(
                ["nav", "header", "footer", "aside", "script", "style", "noscript"]
            ):
                tag.decompose()

            # Try to find main content containers
            main = (
                soup.find("article")
                or soup.find("main")
                or soup.find(class_=re.compile(r"article|content|post", re.I))
                or soup.find("body")
            )

            if main:
                return main.get_text(separator="\n", strip=True)

        # Simple fallback: strip all tags
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.I)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.I)
        text = re.sub(r"<[^>]+>", "", text)
        return text.strip()

    def to_markdown(self, html: str) -> str:
        """Convert HTML content to Markdown.

        Args:
            html: HTML content

        Returns:
            Markdown formatted text
        """
        if HTML2TEXT_AVAILABLE:
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.body_width = 0  # Don't wrap
            return h.handle(html)

        # Simple fallback conversion
        text = html

        # Convert headings
        for i in range(6, 0, -1):
            pattern = rf"<h{i}[^>]*>([^<]+)</h{i}>"
            replacement = "#" * i + r" \1\n"
            text = re.sub(pattern, replacement, text, flags=re.I)

        # Convert bold/strong
        text = re.sub(r"<(?:strong|b)[^>]*>([^<]+)</(?:strong|b)>", r"**\1**", text, flags=re.I)

        # Convert italic/em
        text = re.sub(r"<(?:em|i)[^>]*>([^<]+)</(?:em|i)>", r"*\1*", text, flags=re.I)

        # Convert list items
        text = re.sub(r"<li[^>]*>([^<]+)</li>", r"- \1\n", text, flags=re.I)

        # Convert paragraphs
        text = re.sub(r"<p[^>]*>([^<]+)</p>", r"\1\n\n", text, flags=re.I)

        # Remove remaining tags
        text = re.sub(r"<[^>]+>", "", text)

        return text.strip()


async def parse_url(url: str) -> dict:
    """Parse a web page from URL.

    Convenience function for parsing web pages.

    Args:
        url: Web page URL

    Returns:
        Dictionary with:
        - title: Page title
        - content: Plain text content
        - markdown: Markdown formatted content
        - url: Original URL
    """
    parser = WebParser()
    html = await parser.fetch_content(url)

    return {
        "title": parser.extract_title(html),
        "content": parser.extract_main_content(html),
        "markdown": parser.to_markdown(html),
        "url": url,
    }

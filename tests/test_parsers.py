"""Tests for content source parsers."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from teamverse.parsers.google_docs import GoogleDocsParser, parse_google_doc
from teamverse.parsers.web import WebParser, parse_url
from teamverse.models.content import Audience


class TestGoogleDocsParser:
    """Tests for Google Docs content parsing."""

    def test_extracts_doc_id_from_url(self):
        """Test extracting document ID from various URL formats."""
        urls = [
            ("https://docs.google.com/document/d/1abc123/edit", "1abc123"),
            ("https://docs.google.com/document/d/1abc123/edit?tab=t.0", "1abc123"),
            ("https://docs.google.com/document/d/1abc123", "1abc123"),
            ("docs.google.com/document/d/xyz789/edit#heading=h.123", "xyz789"),
        ]

        parser = GoogleDocsParser()
        for url, expected_id in urls:
            assert parser.extract_doc_id(url) == expected_id

    def test_raises_on_invalid_doc_url(self):
        """Test that invalid URLs raise ValueError."""
        invalid_urls = [
            "https://google.com/search",
            "https://docs.google.com/spreadsheets/d/123/edit",
            "not-a-url",
        ]

        parser = GoogleDocsParser()
        for url in invalid_urls:
            with pytest.raises(ValueError, match="Invalid Google Docs URL"):
                parser.extract_doc_id(url)

    def test_fetches_document_content(self):
        """Test fetching document content via API."""
        import teamverse.parsers.google_docs as gdocs_module

        mock_build = MagicMock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock the documents().get().execute() chain
        mock_doc = {
            "title": "Test Document",
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Hello World\n"}}
                            ]
                        }
                    }
                ]
            },
        }
        mock_service.documents.return_value.get.return_value.execute.return_value = mock_doc

        with patch.object(gdocs_module, "get_google_credentials", return_value=MagicMock()), \
             patch.object(gdocs_module, "build", mock_build, create=True):
            parser = GoogleDocsParser()
            content = parser.fetch_content("test-doc-id")

            assert "Hello World" in content
            mock_build.assert_called_once()

    def test_parse_google_doc_function(self):
        """Test the convenience function for parsing Google Docs."""
        import teamverse.parsers.google_docs as gdocs_module

        mock_build = MagicMock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_doc = {
            "title": "Blog Post Title",
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Introduction paragraph.\n"}}
                            ]
                        }
                    }
                ]
            },
        }
        mock_service.documents.return_value.get.return_value.execute.return_value = mock_doc

        with patch.object(gdocs_module, "get_google_credentials", return_value=MagicMock()), \
             patch.object(gdocs_module, "build", mock_build, create=True):
            result = parse_google_doc(
                "https://docs.google.com/document/d/test123/edit"
            )

            assert result["title"] == "Blog Post Title"
            assert "Introduction paragraph" in result["content"]


class TestWebParser:
    """Tests for web page content parsing."""

    @pytest.mark.asyncio
    async def test_fetches_webpage(self):
        """Test fetching content from a URL."""
        html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Main Heading</h1>
                <p>First paragraph of content.</p>
                <p>Second paragraph.</p>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = html
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("teamverse.parsers.web.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            parser = WebParser()
            content = await parser.fetch_content("https://example.com/article")

            assert html == content

    def test_extracts_title_from_html(self):
        """Test extracting title from HTML."""
        html = "<html><head><title>Article Title</title></head><body></body></html>"

        parser = WebParser()
        title = parser.extract_title(html)

        assert title == "Article Title"

    def test_extracts_main_content(self):
        """Test extracting main article content from HTML."""
        html = """
        <html>
            <body>
                <nav>Navigation stuff</nav>
                <article>
                    <h1>Article Title</h1>
                    <p>Important content here.</p>
                </article>
                <footer>Footer stuff</footer>
            </body>
        </html>
        """

        parser = WebParser()
        content = parser.extract_main_content(html)

        assert "Important content" in content
        # Should not include nav/footer
        assert "Navigation stuff" not in content or len(content) < len(html)

    def test_converts_html_to_markdown(self):
        """Test converting HTML content to Markdown."""
        html = """
        <article>
            <h1>Title</h1>
            <p>A paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </article>
        """

        parser = WebParser()
        markdown = parser.to_markdown(html)

        assert "# Title" in markdown
        assert "**bold**" in markdown
        assert "*italic*" in markdown or "_italic_" in markdown
        assert "- Item 1" in markdown or "* Item 1" in markdown


class TestParseUrl:
    """Tests for the parse_url convenience function."""

    @pytest.mark.asyncio
    async def test_parses_url_to_content(self):
        """Test parsing a URL to structured content."""
        html = """
        <html>
            <head><title>Blog Post Title</title></head>
            <body>
                <article>
                    <p>Blog post content goes here.</p>
                </article>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = html
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("teamverse.parsers.web.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await parse_url("https://example.com/blog/post")

            assert result["title"] == "Blog Post Title"
            assert "Blog post content" in result["content"]


class TestAudienceDetection:
    """Tests for automatically detecting content audience."""

    def test_detects_uk_audience(self):
        """Test detecting UK-specific content."""
        content = "The Chancellor announced changes to National Insurance."

        from teamverse.parsers.utils import detect_audience

        audience = detect_audience(content)
        assert audience == Audience.UK

    def test_detects_us_audience(self):
        """Test detecting US-specific content."""
        content = "The IRS released new guidance on the Earned Income Tax Credit."

        from teamverse.parsers.utils import detect_audience

        audience = detect_audience(content)
        assert audience == Audience.US

    def test_defaults_to_global(self):
        """Test that generic content defaults to global audience."""
        content = "PolicyEngine released a new feature for policy analysis."

        from teamverse.parsers.utils import detect_audience

        audience = detect_audience(content)
        assert audience == Audience.GLOBAL


class TestContentExtraction:
    """Tests for extracting structured content from raw text."""

    def test_extracts_quotes(self):
        """Test extracting quoted text and attributions."""
        text = '''
        "This is a great tool for policy analysis," said John Doe, CEO of Example Corp.
        '''

        from teamverse.parsers.utils import extract_quotes

        quotes = extract_quotes(text)

        assert len(quotes) >= 1
        assert "great tool" in quotes[0]["text"]
        assert quotes[0]["name"] == "John Doe"
        assert "CEO" in quotes[0]["title"]

    def test_extracts_key_points(self):
        """Test extracting key points/bullet points from content."""
        text = """
        Key highlights:
        - First important point
        - Second important point
        - Third important point
        """

        from teamverse.parsers.utils import extract_key_points

        points = extract_key_points(text)

        assert len(points) == 3
        assert "First important" in points[0]

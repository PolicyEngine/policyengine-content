"""Tests for HTTP API endpoints."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile

from PIL import Image


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_returns_ok(self, client):
        """Health endpoint should return 200 with status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestRenderSocialEndpoint:
    """Tests for POST /render-social endpoint."""

    def test_render_social_valid_request(self, client, mock_render_social_image):
        """Valid SocialPost should return image path."""
        payload = {
            "headline_prefix": "PolicyEngine reaches",
            "headline_highlight": "10,000 users",
            "subtext": "Our platform continues to grow",
            "audience": "uk",
            "badge": "Major Milestone",
        }
        response = client.post("/render-social", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "image_path" in data
        assert data["success"] is True

    def test_render_social_with_quote(self, client, mock_render_social_image):
        """SocialPost with quote should render successfully."""
        payload = {
            "headline_prefix": "PolicyEngine reaches",
            "headline_highlight": "10,000 users",
            "subtext": "Our platform continues to grow",
            "audience": "us",
            "quote": {
                "text": "This is amazing!",
                "name": "Jane Doe",
                "title": "CEO",
            },
        }
        response = client.post("/render-social", json=payload)
        assert response.status_code == 200

    def test_render_social_missing_fields(self, client):
        """Missing required fields should return 422."""
        payload = {
            "headline_prefix": "PolicyEngine reaches",
            # Missing headline_highlight, subtext, audience
        }
        response = client.post("/render-social", json=payload)
        assert response.status_code == 422

    def test_render_social_invalid_audience(self, client):
        """Invalid audience value should return 422."""
        payload = {
            "headline_prefix": "Test",
            "headline_highlight": "Test",
            "subtext": "Test",
            "audience": "invalid_audience",
        }
        response = client.post("/render-social", json=payload)
        assert response.status_code == 422

    def test_render_social_chrome_not_found(self, client, mock_no_chrome):
        """Should return 500 when Chrome is not available."""
        payload = {
            "headline_prefix": "Test",
            "headline_highlight": "Test",
            "subtext": "Test",
            "audience": "uk",
        }
        response = client.post("/render-social", json=payload)
        assert response.status_code == 500
        assert "Chrome" in response.json()["detail"]


class TestValidateImageEndpoint:
    """Tests for POST /validate-image endpoint."""

    def test_validate_valid_image(self, client, valid_image_path):
        """Valid image should return validation success."""
        payload = {"image_path": str(valid_image_path)}
        response = client.post("/validate-image", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["errors"] == []

    def test_validate_invalid_dimensions(self, client, invalid_dimension_image_path):
        """Image with wrong dimensions should return validation errors."""
        payload = {"image_path": str(invalid_dimension_image_path)}
        response = client.post("/validate-image", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_validate_nonexistent_file(self, client):
        """Nonexistent file should return validation error."""
        payload = {"image_path": "/nonexistent/path/to/image.png"}
        response = client.post("/validate-image", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert any("does not exist" in e for e in data["errors"])

    def test_validate_missing_path(self, client):
        """Missing image_path should return 422."""
        response = client.post("/validate-image", json={})
        assert response.status_code == 422

    def test_validate_custom_dimensions(self, client, valid_image_path):
        """Should accept custom expected dimensions."""
        payload = {
            "image_path": str(valid_image_path),
            "expected_width": 800,
            "expected_height": 600,
        }
        response = client.post("/validate-image", json=payload)
        assert response.status_code == 200
        data = response.json()
        # Should fail because image is 1200x630, not 800x600
        assert data["valid"] is False


class TestParseSourceEndpoint:
    """Tests for POST /parse-source endpoint."""

    def test_parse_source_valid_url(self, client, mock_web_parser):
        """Valid URL should return parsed content."""
        payload = {"url": "https://policyengine.org/blog/test-post"}
        response = client.post("/parse-source", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "content" in data
        assert "markdown" in data
        assert "url" in data

    def test_parse_source_invalid_url(self, client):
        """Invalid URL should return 422."""
        payload = {"url": "not-a-valid-url"}
        response = client.post("/parse-source", json=payload)
        assert response.status_code == 422

    def test_parse_source_missing_url(self, client):
        """Missing URL should return 422."""
        response = client.post("/parse-source", json={})
        assert response.status_code == 422

    def test_parse_source_fetch_error(self, client, mock_web_parser_error):
        """Fetch error should return 500."""
        payload = {"url": "https://example.com/not-found"}
        response = client.post("/parse-source", json=payload)
        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()


# Fixtures
@pytest.fixture
def client():
    """Create test client for the API."""
    from fastapi.testclient import TestClient
    from teamverse.api import app

    return TestClient(app)


@pytest.fixture
def valid_image_path(tmp_path):
    """Create a valid 1200x630 image with correct colors."""
    img_path = tmp_path / "valid.png"
    img = Image.new("RGB", (1200, 630), color=(26, 35, 50))
    img.save(img_path)
    return img_path


@pytest.fixture
def invalid_dimension_image_path(tmp_path):
    """Create an image with wrong dimensions."""
    img_path = tmp_path / "invalid.png"
    img = Image.new("RGB", (800, 600), color=(26, 35, 50))
    img.save(img_path)
    return img_path


@pytest.fixture
def mock_render_social_image(tmp_path):
    """Mock the render_social_image function."""
    output_path = tmp_path / "output.png"
    # Create a valid image file
    img = Image.new("RGB", (1200, 630), color=(26, 35, 50))
    img.save(output_path)

    with patch("teamverse.api.render_social_image") as mock:
        mock.return_value = output_path
        yield mock


@pytest.fixture
def mock_no_chrome():
    """Mock Chrome not being available."""
    with patch("teamverse.api.render_social_image") as mock:
        mock.side_effect = RuntimeError("Chrome not found. Install Google Chrome to render images.")
        yield mock


@pytest.fixture
def mock_web_parser():
    """Mock the web parser for successful fetch."""
    mock_result = {
        "title": "Test Blog Post",
        "content": "This is the main content of the blog post.",
        "markdown": "# Test Blog Post\n\nThis is the main content.",
        "url": "https://policyengine.org/blog/test-post",
    }
    with patch("teamverse.api.parse_url", new_callable=AsyncMock) as mock:
        mock.return_value = mock_result
        yield mock


@pytest.fixture
def mock_web_parser_error():
    """Mock the web parser for fetch error."""
    with patch("teamverse.api.parse_url", new_callable=AsyncMock) as mock:
        mock.side_effect = Exception("Failed to fetch URL: Connection error")
        yield mock

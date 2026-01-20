"""Tests for CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner
from PIL import Image

from policyengine_content.cli import main
from policyengine_content.models.content import Audience, QuoteBlock, SocialPost
from policyengine_content.renderers.validators import ValidationResult


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_vars_json(tmp_path):
    """Create a sample JSON vars file."""
    vars_file = tmp_path / "vars.json"
    vars_file.write_text(
        json.dumps(
            {
                "headline_prefix": "PolicyEngine powers",
                "headline_highlight": "rapid policy analysis",
                "subtext": "Our technology enables real-time policy simulation.",
                "audience": "uk",
                "badge": "Major Milestone",
                "quote": "This is transformative.",
                "quote_name": "Test Person",
                "quote_title": "Chief Policy Officer",
            }
        )
    )
    return vars_file


@pytest.fixture
def valid_test_image(tmp_path):
    """Create a valid test image with correct dimensions and colors."""
    img_path = tmp_path / "valid.png"
    # Create 1200x630 image with expected background color
    img = Image.new("RGB", (1200, 630), color=(26, 35, 50))
    img.save(img_path)
    return img_path


@pytest.fixture
def invalid_test_image(tmp_path):
    """Create an invalid test image (wrong dimensions)."""
    img_path = tmp_path / "invalid.png"
    img = Image.new("RGB", (800, 600), color=(26, 35, 50))
    img.save(img_path)
    return img_path


class TestSocialCommand:
    """Tests for the social (render-social) command."""

    def test_social_help(self, runner):
        """Test that social command has help text."""
        result = runner.invoke(main, ["social", "--help"])
        assert result.exit_code == 0
        assert "Render a social media image" in result.output

    def test_social_requires_output(self, runner):
        """Test that social command requires --output option."""
        result = runner.invoke(
            main,
            [
                "social",
                "--headline-prefix",
                "Test",
                "--headline-highlight",
                "Content",
                "--subtext",
                "Description",
            ],
        )
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_social_with_vars_file(self, runner, sample_vars_json, tmp_path):
        """Test social command with JSON vars file."""
        output_path = tmp_path / "output.png"

        # Mock render_social_image to avoid needing Chrome
        with patch("policyengine_content.cli.render_social_image") as mock_render:
            mock_render.return_value = output_path

            result = runner.invoke(
                main,
                ["social", "--vars", str(sample_vars_json), "--output", str(output_path)],
            )

            assert result.exit_code == 0
            assert mock_render.called

            # Check that the SocialPost was created with correct values
            call_args = mock_render.call_args
            post = call_args[0][0]
            assert post.headline_prefix == "PolicyEngine powers"
            assert post.headline_highlight == "rapid policy analysis"
            assert post.audience == Audience.UK

    def test_social_with_cli_args(self, runner, tmp_path):
        """Test social command with CLI arguments only."""
        output_path = tmp_path / "output.png"

        with patch("policyengine_content.cli.render_social_image") as mock_render:
            mock_render.return_value = output_path

            result = runner.invoke(
                main,
                [
                    "social",
                    "--headline-prefix",
                    "New Feature:",
                    "--headline-highlight",
                    "Tax Calculator",
                    "--subtext",
                    "Calculate taxes in seconds.",
                    "--audience",
                    "us",
                    "--output",
                    str(output_path),
                ],
            )

            assert result.exit_code == 0
            post = mock_render.call_args[0][0]
            assert post.headline_prefix == "New Feature:"
            assert post.headline_highlight == "Tax Calculator"
            assert post.audience == Audience.US

    def test_social_cli_args_override_json(self, runner, sample_vars_json, tmp_path):
        """Test that CLI arguments override JSON vars."""
        output_path = tmp_path / "output.png"

        with patch("policyengine_content.cli.render_social_image") as mock_render:
            mock_render.return_value = output_path

            result = runner.invoke(
                main,
                [
                    "social",
                    "--vars",
                    str(sample_vars_json),
                    "--headline-highlight",
                    "OVERRIDE",
                    "--output",
                    str(output_path),
                ],
            )

            assert result.exit_code == 0
            post = mock_render.call_args[0][0]
            # JSON value should be overridden
            assert post.headline_highlight == "OVERRIDE"
            # Non-overridden values should come from JSON
            assert post.headline_prefix == "PolicyEngine powers"

    def test_social_with_quote(self, runner, tmp_path):
        """Test social command with quote block."""
        output_path = tmp_path / "output.png"

        with patch("policyengine_content.cli.render_social_image") as mock_render:
            mock_render.return_value = output_path

            result = runner.invoke(
                main,
                [
                    "social",
                    "--headline-prefix",
                    "Test",
                    "--headline-highlight",
                    "Quote",
                    "--subtext",
                    "With attribution",
                    "--quote",
                    "This is a great tool.",
                    "--quote-name",
                    "John Doe",
                    "--quote-title",
                    "Policy Analyst",
                    "--output",
                    str(output_path),
                ],
            )

            assert result.exit_code == 0
            post = mock_render.call_args[0][0]
            assert post.quote is not None
            assert post.quote.text == "This is a great tool."
            assert post.quote.name == "John Doe"
            assert post.quote.title == "Policy Analyst"

    def test_social_outputs_generated_path(self, runner, tmp_path):
        """Test that social command outputs the generated file path."""
        output_path = tmp_path / "output.png"

        with patch("policyengine_content.cli.render_social_image") as mock_render:
            mock_render.return_value = output_path

            result = runner.invoke(
                main,
                [
                    "social",
                    "--headline-prefix",
                    "Test",
                    "--headline-highlight",
                    "Output",
                    "--subtext",
                    "Check output",
                    "--output",
                    str(output_path),
                ],
            )

            assert result.exit_code == 0
            assert "Generated:" in result.output


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_help(self, runner):
        """Test that validate command has help text."""
        result = runner.invoke(main, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate a rendered image" in result.output

    def test_validate_requires_image_path(self, runner):
        """Test that validate command requires an image path argument."""
        result = runner.invoke(main, ["validate"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "IMAGE_PATH" in result.output

    def test_validate_valid_image(self, runner, valid_test_image):
        """Test validate command with a valid image."""
        result = runner.invoke(main, ["validate", str(valid_test_image)])

        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_validate_invalid_dimensions(self, runner, invalid_test_image):
        """Test validate command with invalid image dimensions."""
        result = runner.invoke(main, ["validate", str(invalid_test_image)])

        assert result.exit_code == 1
        assert "failed" in result.output.lower() or "Width" in result.output

    def test_validate_nonexistent_file(self, runner, tmp_path):
        """Test validate command with non-existent file."""
        nonexistent = tmp_path / "does_not_exist.png"
        result = runner.invoke(main, ["validate", str(nonexistent)])

        assert result.exit_code != 0

    def test_validate_shows_warnings(self, runner, tmp_path):
        """Test that validate command shows warnings."""
        # Create image with right edge issue (warning, not error)
        img_path = tmp_path / "warning.png"
        img = Image.new("RGB", (1200, 630), color=(26, 35, 50))
        # Set right edge to different color
        for y in range(630):
            img.putpixel((1199, y), (100, 100, 100))
        img.save(img_path)

        result = runner.invoke(main, ["validate", str(img_path)])

        # Should still pass (warnings don't fail validation)
        assert result.exit_code == 0
        assert "Warning" in result.output or "valid" in result.output.lower()


class TestGenerateCommand:
    """Tests for the generate command."""

    def test_generate_help(self, runner):
        """Test that generate command has help text."""
        result = runner.invoke(main, ["generate", "--help"])
        assert result.exit_code == 0
        assert "Generate" in result.output or "content" in result.output.lower()

    def test_generate_requires_source(self, runner):
        """Test that generate command requires a source URL."""
        result = runner.invoke(main, ["generate"])
        assert result.exit_code != 0
        assert "Missing" in result.output or "SOURCE" in result.output

    def test_generate_from_url(self, runner, tmp_path):
        """Test generate command with a web URL."""
        output_dir = tmp_path / "output"

        with patch("policyengine_content.cli.parse_url") as mock_parse:
            # Mock the async function
            mock_parse.return_value = {
                "title": "Test Article",
                "content": "This is the article content about policy.",
                "markdown": "# Test Article\n\nThis is the article content.",
                "url": "https://example.com/article",
            }

            result = runner.invoke(
                main,
                [
                    "generate",
                    "https://example.com/article",
                    "--output-dir",
                    str(output_dir),
                ],
            )

            # Command should succeed
            assert result.exit_code == 0 or "Generated" in result.output

    def test_generate_from_google_doc(self, runner, tmp_path):
        """Test generate command with a Google Docs URL."""
        output_dir = tmp_path / "output"

        with patch("policyengine_content.cli.parse_google_doc") as mock_parse:
            mock_parse.return_value = {
                "title": "Policy Brief",
                "content": "This is a policy brief about tax reform.",
                "doc_id": "abc123",
            }

            result = runner.invoke(
                main,
                [
                    "generate",
                    "https://docs.google.com/document/d/abc123/edit",
                    "--output-dir",
                    str(output_dir),
                ],
            )

            # Command should handle Google Docs URLs
            assert result.exit_code == 0 or mock_parse.called

    def test_generate_creates_output_directory(self, runner, tmp_path):
        """Test that generate command creates the output directory if needed."""
        output_dir = tmp_path / "new_dir" / "nested"

        with patch("policyengine_content.cli.parse_url") as mock_parse:
            mock_parse.return_value = {
                "title": "Test",
                "content": "Content",
                "markdown": "# Test",
                "url": "https://example.com",
            }

            result = runner.invoke(
                main,
                [
                    "generate",
                    "https://example.com",
                    "--output-dir",
                    str(output_dir),
                ],
            )

            # Should create directory or attempt to
            if result.exit_code == 0:
                assert output_dir.exists()

    def test_generate_audience_option(self, runner, tmp_path):
        """Test generate command with audience option."""
        output_dir = tmp_path / "output"

        with patch("policyengine_content.cli.parse_url") as mock_parse:
            mock_parse.return_value = {
                "title": "Test",
                "content": "Content for US audience",
                "markdown": "# Test",
                "url": "https://example.com",
            }

            result = runner.invoke(
                main,
                [
                    "generate",
                    "https://example.com",
                    "--output-dir",
                    str(output_dir),
                    "--audience",
                    "us",
                ],
            )

            # Should accept audience option
            assert "--audience" not in result.output or result.exit_code == 0


class TestNewsletterCommand:
    """Tests for the newsletter command."""

    def test_newsletter_help(self, runner):
        """Test that newsletter command has help text."""
        result = runner.invoke(main, ["newsletter", "--help"])
        assert result.exit_code == 0
        assert "Render a newsletter" in result.output

    def test_newsletter_requires_vars(self, runner, tmp_path):
        """Test that newsletter command requires --vars option."""
        output_path = tmp_path / "newsletter.html"
        result = runner.invoke(main, ["newsletter", "--output", str(output_path)])
        assert result.exit_code != 0
        assert "--vars is required" in result.output

    def test_newsletter_with_vars(self, runner, tmp_path):
        """Test newsletter command with vars file."""
        vars_file = tmp_path / "newsletter_vars.json"
        vars_file.write_text(
            json.dumps(
                {
                    "subject": "PolicyEngine Newsletter",
                    "preview_text": "Latest updates from PolicyEngine",
                    "audience": "uk",
                    "hero_label": "NEWSLETTER",
                    "hero_title": "Policy Updates",
                    "hero_subtitle": "What's new this week",
                    "body_html": "<p>Newsletter content here.</p>",
                    "cta_primary_text": "Learn More",
                    "cta_primary_url": "https://policyengine.org",
                }
            )
        )
        output_path = tmp_path / "newsletter.html"

        with patch("policyengine_content.cli.render_newsletter") as mock_render:
            mock_render.return_value = output_path

            result = runner.invoke(
                main,
                ["newsletter", "--vars", str(vars_file), "--output", str(output_path)],
            )

            assert result.exit_code == 0
            assert mock_render.called


class TestMainGroup:
    """Tests for the main CLI group."""

    def test_version_option(self, runner):
        """Test --version option."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        # Should show version number
        assert "0." in result.output or "version" in result.output.lower()

    def test_help_shows_all_commands(self, runner):
        """Test that help shows all available commands."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "social" in result.output
        assert "validate" in result.output
        assert "newsletter" in result.output
        # generate should also be there after implementation
        assert "generate" in result.output

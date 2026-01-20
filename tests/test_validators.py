"""Tests for image validators."""

import pytest
from pathlib import Path
from PIL import Image
import tempfile

from teamverse.renderers.validators import validate_image, ValidationResult


class TestValidateImage:
    def test_valid_image(self, tmp_path):
        """Test validation of a correctly sized image with correct edge colors."""
        img_path = tmp_path / "test.png"

        # Create a 1200x630 image with the expected background color
        img = Image.new("RGB", (1200, 630), color=(26, 35, 50))  # #1a2332
        img.save(img_path)

        result = validate_image(img_path)
        assert result.valid
        assert len(result.errors) == 0

    def test_wrong_dimensions(self, tmp_path):
        """Test validation catches wrong dimensions."""
        img_path = tmp_path / "test.png"

        # Create wrong-sized image
        img = Image.new("RGB", (800, 600), color=(26, 35, 50))
        img.save(img_path)

        result = validate_image(img_path)
        assert not result.valid
        assert any("Width" in e for e in result.errors)
        assert any("Height" in e for e in result.errors)

    def test_white_ribbon_detection(self, tmp_path):
        """Test that white bottom edge is detected (the ribbon bug)."""
        img_path = tmp_path / "test.png"

        # Create image with white bottom row
        img = Image.new("RGB", (1200, 630), color=(26, 35, 50))
        for x in range(1200):
            img.putpixel((x, 629), (255, 255, 255))  # White bottom row
        img.save(img_path)

        result = validate_image(img_path)
        assert not result.valid
        assert any("white ribbon" in e.lower() for e in result.errors)

    def test_missing_file(self, tmp_path):
        """Test validation of non-existent file."""
        result = validate_image(tmp_path / "nonexistent.png")
        assert not result.valid
        assert any("does not exist" in e for e in result.errors)

    def test_edge_tolerance(self, tmp_path):
        """Test that colors within tolerance pass."""
        img_path = tmp_path / "test.png"

        # Create image with slightly off color (within tolerance)
        img = Image.new("RGB", (1200, 630), color=(30, 40, 55))  # Close to #1a2332
        img.save(img_path)

        result = validate_image(img_path, edge_tolerance=15)
        assert result.valid

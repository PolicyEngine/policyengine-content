"""Image and content validators."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image


@dataclass
class ValidationResult:
    """Result of a validation check."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_image(
    image_path: Path,
    expected_width: int = 1200,
    expected_height: int = 630,
    check_edges: bool = True,
    expected_edge_color: tuple[int, int, int] = (26, 35, 50),  # #1a2332
    edge_tolerance: int = 10,
) -> ValidationResult:
    """Validate a rendered image.

    Args:
        image_path: Path to the image file
        expected_width: Expected width in pixels
        expected_height: Expected height in pixels
        check_edges: Whether to check edge colors (detects white ribbon bug)
        expected_edge_color: RGB tuple for expected edge color
        edge_tolerance: Allowed deviation from expected color per channel

    Returns:
        ValidationResult with valid flag and any errors/warnings
    """
    errors = []
    warnings = []

    if not image_path.exists():
        return ValidationResult(valid=False, errors=["Image file does not exist"])

    try:
        with Image.open(image_path) as img:
            # Check dimensions
            width, height = img.size
            if width != expected_width:
                errors.append(f"Width is {width}, expected {expected_width}")
            if height != expected_height:
                errors.append(f"Height is {height}, expected {expected_height}")

            # Check edge colors (bottom edge especially for white ribbon bug)
            if check_edges and img.mode in ("RGB", "RGBA"):
                # Sample bottom edge
                bottom_row = [img.getpixel((x, height - 1))[:3] for x in range(0, width, 100)]
                for i, pixel in enumerate(bottom_row):
                    if not _color_within_tolerance(pixel, expected_edge_color, edge_tolerance):
                        errors.append(
                            f"Bottom edge pixel at x={i*100} is {pixel}, "
                            f"expected near {expected_edge_color} (white ribbon detected?)"
                        )
                        break  # One error is enough

                # Sample right edge
                right_col = [img.getpixel((width - 1, y))[:3] for y in range(0, height, 100)]
                for i, pixel in enumerate(right_col):
                    if not _color_within_tolerance(pixel, expected_edge_color, edge_tolerance):
                        warnings.append(
                            f"Right edge pixel at y={i*100} is {pixel}, "
                            f"expected near {expected_edge_color}"
                        )
                        break

    except Exception as e:
        return ValidationResult(valid=False, errors=[f"Failed to open image: {e}"])

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def _color_within_tolerance(
    actual: tuple[int, int, int],
    expected: tuple[int, int, int],
    tolerance: int,
) -> bool:
    """Check if a color is within tolerance of expected."""
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected))

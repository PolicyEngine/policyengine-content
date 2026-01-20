"""Social media image renderer using Chrome headless."""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from jinja2 import Environment, PackageLoader

from policyengine_content.models.content import SocialPost
from policyengine_content.renderers.validators import validate_image


def get_chrome_path() -> Optional[str]:
    """Find Chrome executable path."""
    paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "google-chrome",
    ]
    for path in paths:
        if Path(path).exists():
            return path
        result = subprocess.run(["which", path], capture_output=True)
        if result.returncode == 0:
            return path
    return None


def render_social_image(
    post: SocialPost,
    output_path: Path,
    width: int = 1200,
    height: int = 630,
) -> Path:
    """Render a social media image from a SocialPost model.

    Args:
        post: SocialPost model with content
        output_path: Where to save the PNG
        width: Image width (default 1200)
        height: Image height (default 630)

    Returns:
        Path to the generated image

    Raises:
        RuntimeError: If Chrome is not found or rendering fails
        ValueError: If the rendered image fails validation
    """
    chrome_path = get_chrome_path()
    if not chrome_path:
        raise RuntimeError("Chrome not found. Install Google Chrome to render images.")

    # Load and render template
    env = Environment(loader=PackageLoader("policyengine_content", "templates"))
    template = env.get_template("social-image.html")

    html_content = template.render(
        headline_prefix=post.headline_prefix,
        headline_highlight=post.headline_highlight,
        subtext=post.subtext,
        flags=post.flags,
        badge=post.badge,
        quote=post.quote.text if post.quote else "",
        attribution_name=post.quote.name if post.quote else "",
        attribution_title=post.quote.title if post.quote else "",
        headshot_url=str(post.quote.headshot_url) if post.quote and post.quote.headshot_url else "",
        logo_url=str(post.logo_url),
    )

    # Write HTML to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False
    ) as f:
        f.write(html_content)
        temp_html = Path(f.name)

    try:
        # Render with Chrome headless
        cmd = [
            chrome_path,
            "--headless",
            "--disable-gpu",
            f"--screenshot={output_path}",
            f"--window-size={width},{height}",
            "--hide-scrollbars",
            f"file://{temp_html.absolute()}",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Chrome rendering failed: {result.stderr}")

        if not output_path.exists():
            raise RuntimeError("Chrome did not create output file")

        # Validate the rendered image
        validation_result = validate_image(
            output_path,
            expected_width=width,
            expected_height=height,
        )
        if not validation_result.valid:
            raise ValueError(f"Image validation failed: {validation_result.errors}")

        return output_path

    finally:
        temp_html.unlink(missing_ok=True)

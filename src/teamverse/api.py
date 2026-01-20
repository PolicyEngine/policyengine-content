"""HTTP API for CRM integration.

Exposes endpoints for rendering social images, validating images,
and parsing web content.

Usage:
    uvicorn teamverse.api:app --reload
"""

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

from teamverse.models.content import SocialPost, Audience, QuoteBlock
from teamverse.renderers.social import render_social_image
from teamverse.renderers.validators import validate_image, ValidationResult
from teamverse.parsers.web import parse_url

__version__ = "0.1.0"

app = FastAPI(
    title="Teamverse API",
    description="API for PolicyEngine content generation - social images, validation, and content parsing",
    version=__version__,
)


# Request/Response Models


class QuoteBlockRequest(BaseModel):
    """Quote block for social posts."""

    text: str
    name: str
    title: str
    headshot_url: Optional[HttpUrl] = None


class RenderSocialRequest(BaseModel):
    """Request model for rendering social images."""

    headline_prefix: str
    headline_highlight: str
    subtext: str
    audience: str  # Will be validated to Audience enum
    badge: str = "Major Milestone"
    quote: Optional[QuoteBlockRequest] = None
    logo_url: Optional[HttpUrl] = None


class RenderSocialResponse(BaseModel):
    """Response model for rendered social images."""

    success: bool
    image_path: str
    message: str = "Image rendered successfully"


class ValidateImageRequest(BaseModel):
    """Request model for image validation."""

    image_path: str
    expected_width: int = 1200
    expected_height: int = 630
    check_edges: bool = True


class ValidateImageResponse(BaseModel):
    """Response model for image validation."""

    valid: bool
    errors: list[str]
    warnings: list[str]


class ParseSourceRequest(BaseModel):
    """Request model for parsing web content."""

    url: HttpUrl


class ParseSourceResponse(BaseModel):
    """Response model for parsed content."""

    title: str
    content: str
    markdown: str
    url: str


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    version: str


# Endpoints


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.

    Returns the service status and version.
    """
    return HealthResponse(status="ok", version=__version__)


@app.post("/render-social", response_model=RenderSocialResponse)
async def render_social(request: RenderSocialRequest):
    """Render a social media image from SocialPost data.

    Args:
        request: SocialPost data including headline, subtext, audience, etc.

    Returns:
        Path to the rendered image file.

    Raises:
        HTTPException 422: Invalid request data
        HTTPException 500: Rendering failed (e.g., Chrome not available)
    """
    # Validate audience
    try:
        audience = Audience(request.audience)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid audience '{request.audience}'. Must be one of: {[a.value for a in Audience]}",
        )

    # Build QuoteBlock if provided
    quote = None
    if request.quote:
        quote = QuoteBlock(
            text=request.quote.text,
            name=request.quote.name,
            title=request.quote.title,
            headshot_url=request.quote.headshot_url,
        )

    # Build SocialPost
    post_kwargs = {
        "headline_prefix": request.headline_prefix,
        "headline_highlight": request.headline_highlight,
        "subtext": request.subtext,
        "audience": audience,
        "badge": request.badge,
        "quote": quote,
    }
    if request.logo_url:
        post_kwargs["logo_url"] = request.logo_url

    post = SocialPost(**post_kwargs)

    # Create output path in temp directory
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        output_path = Path(f.name)

    try:
        result_path = render_social_image(post, output_path)
        return RenderSocialResponse(
            success=True,
            image_path=str(result_path),
            message="Image rendered successfully",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate-image", response_model=ValidateImageResponse)
async def validate_image_endpoint(request: ValidateImageRequest):
    """Validate a rendered image.

    Checks dimensions and edge colors to detect rendering issues
    like the "white ribbon" bug.

    Args:
        request: Image path and optional expected dimensions.

    Returns:
        Validation result with valid flag, errors, and warnings.
    """
    image_path = Path(request.image_path)

    result = validate_image(
        image_path,
        expected_width=request.expected_width,
        expected_height=request.expected_height,
        check_edges=request.check_edges,
    )

    return ValidateImageResponse(
        valid=result.valid,
        errors=result.errors,
        warnings=result.warnings,
    )


@app.post("/parse-source", response_model=ParseSourceResponse)
async def parse_source(request: ParseSourceRequest):
    """Parse content from a web URL.

    Fetches the URL, extracts title and main content,
    and converts to markdown.

    Args:
        request: URL to parse.

    Returns:
        Parsed content including title, content, and markdown.

    Raises:
        HTTPException 500: Failed to fetch or parse URL
    """
    try:
        result = await parse_url(str(request.url))
        return ParseSourceResponse(
            title=result["title"],
            content=result["content"],
            markdown=result["markdown"],
            url=result["url"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing URL: {str(e)}")

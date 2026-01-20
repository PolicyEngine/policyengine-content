"""Content models for blog posts, newsletters, and social media."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, HttpUrl


class Audience(str, Enum):
    """Target audience for content."""

    UK = "uk"
    US = "us"
    GLOBAL = "global"


class QuoteBlock(BaseModel):
    """A quote with attribution."""

    text: str
    name: str
    title: str
    headshot_url: Optional[HttpUrl] = None


class SocialPost(BaseModel):
    """Social media image content."""

    headline_prefix: str
    headline_highlight: str
    subtext: str
    audience: Audience
    badge: str = "Major Milestone"
    quote: Optional[QuoteBlock] = None
    logo_url: HttpUrl = "https://raw.githubusercontent.com/PolicyEngine/policyengine-app/master/src/images/logos/policyengine/white.png"

    @property
    def flags(self) -> str:
        """Get emoji flags for audience."""
        return {
            Audience.UK: "🇬🇧",
            Audience.US: "🇺🇸 🇬🇧",
            Audience.GLOBAL: "🇺🇸 🇬🇧",
        }[self.audience]


class BlogPost(BaseModel):
    """Blog post content."""

    title: str
    description: str
    content: str  # Markdown content
    authors: list[str]
    tags: list[str]
    image_filename: Optional[str] = None

    # Optional social media metadata
    social: Optional[SocialPost] = None


class NewsletterSection(BaseModel):
    """A section within a newsletter."""

    type: str  # "hero", "quote", "body", "features", "cta"
    content: dict  # Type-specific content


class Newsletter(BaseModel):
    """Newsletter email content."""

    subject: str
    preview_text: str
    audience: Audience
    hero_label: str
    hero_title: str
    hero_subtitle: str
    quote: Optional[QuoteBlock] = None
    body_html: str
    cta_primary_text: str
    cta_primary_url: HttpUrl
    cta_secondary_text: Optional[str] = None
    cta_secondary_url: Optional[HttpUrl] = None


class ContentBundle(BaseModel):
    """A bundle of related content for a single announcement."""

    source_url: Optional[HttpUrl] = None
    blog_post: Optional[BlogPost] = None
    newsletters: dict[Audience, Newsletter] = {}
    social_posts: dict[Audience, SocialPost] = {}
    social_copy: dict[str, str] = {}  # platform -> text

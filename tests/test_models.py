"""Tests for content models."""

import pytest

from policyengine_content.models.content import (
    Audience,
    QuoteBlock,
    SocialPost,
    BlogPost,
    Newsletter,
)


class TestAudience:
    def test_audience_values(self):
        assert Audience.UK.value == "uk"
        assert Audience.US.value == "us"
        assert Audience.GLOBAL.value == "global"


class TestSocialPost:
    def test_flags_uk(self):
        post = SocialPost(
            headline_prefix="Test",
            headline_highlight="Headline",
            subtext="Some text",
            audience=Audience.UK,
        )
        assert post.flags == "🇬🇧"

    def test_flags_us(self):
        post = SocialPost(
            headline_prefix="Test",
            headline_highlight="Headline",
            subtext="Some text",
            audience=Audience.US,
        )
        assert post.flags == "🇺🇸 🇬🇧"

    def test_flags_global(self):
        post = SocialPost(
            headline_prefix="Test",
            headline_highlight="Headline",
            subtext="Some text",
            audience=Audience.GLOBAL,
        )
        assert post.flags == "🇺🇸 🇬🇧"

    def test_with_quote(self):
        quote = QuoteBlock(
            text="This is a quote",
            name="John Doe",
            title="CEO",
        )
        post = SocialPost(
            headline_prefix="Test",
            headline_highlight="Headline",
            subtext="Some text",
            audience=Audience.UK,
            quote=quote,
        )
        assert post.quote.text == "This is a quote"
        assert post.quote.name == "John Doe"


class TestBlogPost:
    def test_basic_post(self):
        post = BlogPost(
            title="Test Post",
            description="A test post",
            content="# Heading\n\nContent here.",
            authors=["max-ghenis"],
            tags=["global", "org"],
        )
        assert post.title == "Test Post"
        assert "max-ghenis" in post.authors


class TestNewsletter:
    def test_basic_newsletter(self):
        nl = Newsletter(
            subject="Test Newsletter",
            preview_text="Preview",
            audience=Audience.UK,
            hero_label="Announcement",
            hero_title="Big News",
            hero_subtitle="Something happened",
            body_html="<p>Content</p>",
            cta_primary_text="Read More",
            cta_primary_url="https://policyengine.org",
        )
        assert nl.subject == "Test Newsletter"
        assert nl.audience == Audience.UK

"""Command-line interface for policyengine_content content generation."""

import asyncio
import json
from pathlib import Path

import click

from policyengine_content.models.content import Audience, ContentBundle, QuoteBlock, SocialPost, Newsletter
from policyengine_content.parsers import parse_google_doc, parse_url
from policyengine_content.renderers.social import render_social_image
from policyengine_content.renderers.newsletter import render_newsletter


@click.group()
@click.version_option()
def main():
    """Teamverse - Content generation for PolicyEngine."""
    pass


@main.command()
@click.option("--vars", "-v", type=click.Path(exists=True), help="JSON file with template variables")
@click.option("--headline-prefix", help="First line of headline")
@click.option("--headline-highlight", help="Highlighted second line")
@click.option("--subtext", help="Supporting description")
@click.option("--audience", type=click.Choice(["uk", "us", "global"]), default="uk")
@click.option("--badge", default="Major Milestone", help="Badge text")
@click.option("--quote", help="Pull quote text")
@click.option("--quote-name", help="Quote attribution name")
@click.option("--quote-title", help="Quote attribution title")
@click.option("--headshot-url", help="URL to headshot image")
@click.option("--output", "-o", type=click.Path(), required=True, help="Output PNG path")
def social(
    vars,
    headline_prefix,
    headline_highlight,
    subtext,
    audience,
    badge,
    quote,
    quote_name,
    quote_title,
    headshot_url,
    output,
):
    """Render a social media image."""
    # Load from JSON file if provided
    data = {}
    if vars:
        with open(vars) as f:
            data = json.load(f)

    # CLI args override JSON
    data.update({k: v for k, v in {
        "headline_prefix": headline_prefix,
        "headline_highlight": headline_highlight,
        "subtext": subtext,
        "audience": audience,
        "badge": badge,
    }.items() if v is not None})

    # Build quote if provided
    quote_block = None
    if quote or data.get("quote"):
        quote_block = QuoteBlock(
            text=quote or data.get("quote", ""),
            name=quote_name or data.get("quote_name", ""),
            title=quote_title or data.get("quote_title", ""),
            headshot_url=headshot_url or data.get("headshot_url"),
        )

    post = SocialPost(
        headline_prefix=data.get("headline_prefix", ""),
        headline_highlight=data.get("headline_highlight", ""),
        subtext=data.get("subtext", ""),
        audience=Audience(data.get("audience", "uk")),
        badge=data.get("badge", "Major Milestone"),
        quote=quote_block,
    )

    output_path = Path(output)
    result = render_social_image(post, output_path)
    click.echo(f"Generated: {result}")


@main.command()
@click.option("--vars", "-v", type=click.Path(exists=True), help="JSON file with newsletter data")
@click.option("--output", "-o", type=click.Path(), required=True, help="Output HTML path")
def newsletter(vars, output):
    """Render a newsletter HTML file."""
    if not vars:
        raise click.UsageError("--vars is required for newsletter generation")

    with open(vars) as f:
        data = json.load(f)

    quote_block = None
    if data.get("quote_text"):
        quote_block = QuoteBlock(
            text=data["quote_text"],
            name=data.get("quote_name", ""),
            title=data.get("quote_title", ""),
            headshot_url=data.get("quote_headshot"),
        )

    nl = Newsletter(
        subject=data["subject"],
        preview_text=data["preview_text"],
        audience=Audience(data.get("audience", "uk")),
        hero_label=data["hero_label"],
        hero_title=data["hero_title"],
        hero_subtitle=data["hero_subtitle"],
        quote=quote_block,
        body_html=data["body_html"],
        cta_primary_text=data["cta_primary_text"],
        cta_primary_url=data["cta_primary_url"],
        cta_secondary_text=data.get("cta_secondary_text"),
        cta_secondary_url=data.get("cta_secondary_url"),
    )

    output_path = Path(output)
    result = render_newsletter(nl, output_path)
    click.echo(f"Generated: {result}")


@main.command()
@click.argument("image_path", type=click.Path(exists=True))
def validate(image_path):
    """Validate a rendered image."""
    from policyengine_content.renderers.validators import validate_image

    result = validate_image(Path(image_path))

    if result.valid:
        click.echo(click.style("✓ Image is valid", fg="green"))
    else:
        click.echo(click.style("✗ Validation failed:", fg="red"))
        for error in result.errors:
            click.echo(f"  - {error}")

    if result.warnings:
        click.echo(click.style("Warnings:", fg="yellow"))
        for warning in result.warnings:
            click.echo(f"  - {warning}")

    raise SystemExit(0 if result.valid else 1)


@main.command()
@click.argument("source")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default=".",
    help="Output directory for generated content",
)
@click.option(
    "--audience",
    type=click.Choice(["uk", "us", "global"]),
    default="uk",
    help="Target audience for content",
)
def generate(source, output_dir, audience):
    """Generate a content bundle from a source URL.

    SOURCE is a URL to parse - can be a web page or Google Docs link.

    Generates social images, newsletter content, and blog post drafts.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Detect source type and parse
    is_google_doc = "docs.google.com/document" in source

    if is_google_doc:
        try:
            parsed = parse_google_doc(source)
        except Exception as e:
            raise click.ClickException(f"Failed to parse Google Doc: {e}")
    else:
        # Web URL - use async parser
        try:
            parsed = asyncio.run(parse_url(source))
        except Exception as e:
            raise click.ClickException(f"Failed to parse URL: {e}")

    title = parsed.get("title", "Untitled")
    content = parsed.get("content", "")

    # Create content bundle
    bundle = ContentBundle(
        source_url=source,
    )

    # Save parsed content to JSON
    bundle_file = output_path / "content_bundle.json"
    bundle_data = {
        "source_url": source,
        "title": title,
        "content": content,
        "audience": audience,
    }
    with open(bundle_file, "w") as f:
        json.dump(bundle_data, f, indent=2)

    click.echo(f"Generated content bundle from: {title}")
    click.echo(f"Output directory: {output_path.absolute()}")
    click.echo(f"  - content_bundle.json")


if __name__ == "__main__":
    main()

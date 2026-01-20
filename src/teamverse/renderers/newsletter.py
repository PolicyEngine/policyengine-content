"""Newsletter HTML renderer."""

from pathlib import Path

from jinja2 import Environment, PackageLoader

from teamverse.models.content import Newsletter


def render_newsletter(
    newsletter: Newsletter,
    output_path: Path,
) -> Path:
    """Render a newsletter to HTML.

    Args:
        newsletter: Newsletter model with content
        output_path: Where to save the HTML file

    Returns:
        Path to the generated HTML file
    """
    env = Environment(loader=PackageLoader("teamverse", "templates"))
    template = env.get_template("newsletter.html")

    html_content = template.render(
        subject=newsletter.subject,
        preview_text=newsletter.preview_text,
        audience=newsletter.audience.value,
        hero_label=newsletter.hero_label,
        hero_title=newsletter.hero_title,
        hero_subtitle=newsletter.hero_subtitle,
        quote_text=newsletter.quote.text if newsletter.quote else "",
        quote_name=newsletter.quote.name if newsletter.quote else "",
        quote_title=newsletter.quote.title if newsletter.quote else "",
        quote_headshot=str(newsletter.quote.headshot_url) if newsletter.quote and newsletter.quote.headshot_url else "",
        body_html=newsletter.body_html,
        cta_primary_text=newsletter.cta_primary_text,
        cta_primary_url=str(newsletter.cta_primary_url),
        cta_secondary_text=newsletter.cta_secondary_text or "",
        cta_secondary_url=str(newsletter.cta_secondary_url) if newsletter.cta_secondary_url else "",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content)

    return output_path

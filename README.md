# policyengine-content

Content generation for PolicyEngine - social images, newsletters, blog posts.

## Features

- **Social Image Generation**: Create 1200x630 OG images with Chrome headless rendering
- **Content Source Parsing**: Parse Google Docs and web URLs for content extraction
- **GitHub Publishing**: Publish content to GitHub repositories
- **CLI Commands**: Command-line interface for content generation workflows
- **HTTP API**: FastAPI endpoints for CRM integration

## Installation

```bash
pip install policyengine-content
```

Or for development:

```bash
pip install -e ".[dev]"
```

## Usage

### CLI

```bash
# Generate social image
policyengine-content social --headline "PolicyEngine meets PM" --badge "Major Milestone"

# Validate image dimensions
policyengine-content validate image.png

# Parse content from URL
policyengine-content parse-source https://example.com/article

# Generate content bundle
policyengine-content generate --source https://example.com/article
```

### Python API

```python
from policyengine_content.models.content import SocialPost, Audience
from policyengine_content.renderers.social import SocialRenderer

# Create social post
post = SocialPost(
    headline="PolicyEngine meets PM",
    subheadline="Policy analysis at 10 Downing Street",
    badge="Major Milestone",
    audience=Audience.UK,
)

# Render to image
renderer = SocialRenderer()
path = renderer.render(post)
```

### HTTP API

```bash
# Start server
uvicorn policyengine_content.api:app

# Health check
curl http://localhost:8000/health

# Render social image
curl -X POST http://localhost:8000/render-social \
  -H "Content-Type: application/json" \
  -d '{"headline": "Test", "audience": "global"}'
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black . -l 88
ruff check .
```

## License

MIT

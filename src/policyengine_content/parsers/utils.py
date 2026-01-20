"""Parser utilities for content extraction and analysis."""

import re
from typing import Optional

from policyengine_content.models.content import Audience


# UK-specific terms
UK_INDICATORS = [
    r"\bchancellor\b",
    r"\btreasury\b",
    r"\bdowning street\b",
    r"\bnational insurance\b",
    r"\bNHS\b",
    r"\bDWP\b",
    r"\buniversal credit\b",
    r"\bcouncil tax\b",
    r"\bchild benefit\b",
    r"\bHMRC\b",
    r"\bpensions?\s+credit\b",
    r"\bhousing benefit\b",
    r"\bworking tax credit\b",
    r"\bincome support\b",
    r"\bjobseeker'?s? allowance\b",
    r"\battendance allowance\b",
    r"\bPIP\b",  # Personal Independence Payment
    r"\bESA\b",  # Employment and Support Allowance
    r"\bstate pension\b",
    r"\b£\d",  # Pound sign with numbers
]

# US-specific terms
US_INDICATORS = [
    r"\bIRS\b",
    r"\bcongress\b",
    r"\bsenate\b",
    r"\bwhite house\b",
    r"\bsocial security\b",
    r"\bSNAP\b",
    r"\bEITC\b",
    r"\bearned income tax credit\b",
    r"\bchild tax credit\b",
    r"\bCTC\b",
    r"\bmedicaid\b",
    r"\bmedicare\b",
    r"\bsection 8\b",
    r"\bSSI\b",  # Supplemental Security Income
    r"\bTANF\b",  # Temporary Assistance for Needy Families
    r"\bWIC\b",  # Women, Infants, and Children
    r"\b401\(k\)",
    r"\bForm 1040\b",
    r"\b\$\d",  # Dollar sign with numbers
]


def detect_audience(content: str) -> Audience:
    """Detect the target audience based on content analysis.

    Analyzes content for UK-specific or US-specific terms and phrases
    to determine the most likely target audience.

    Args:
        content: Text content to analyze

    Returns:
        Detected Audience (UK, US, or GLOBAL)
    """
    content_lower = content.lower()

    uk_score = 0
    us_score = 0

    for pattern in UK_INDICATORS:
        if re.search(pattern, content, re.IGNORECASE):
            uk_score += 1

    for pattern in US_INDICATORS:
        if re.search(pattern, content, re.IGNORECASE):
            us_score += 1

    # Determine audience based on scores
    if uk_score > us_score and uk_score >= 2:
        return Audience.UK
    elif us_score > uk_score and us_score >= 2:
        return Audience.US
    else:
        return Audience.GLOBAL


def extract_quotes(text: str) -> list[dict]:
    """Extract quoted text with attributions.

    Looks for patterns like:
    - "Quote text," said Name, Title.
    - "Quote text." - Name, Title

    Args:
        text: Text to search for quotes

    Returns:
        List of dictionaries with 'text', 'name', and 'title' keys
    """
    quotes = []

    # Pattern: "Quote," said/says Name[,] Title
    pattern1 = re.compile(
        r'"([^"]+)"[,.]?\s+(?:said|says|according to)\s+'
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'  # Name
        r'(?:,\s*(.+?))?(?:\.|$)',  # Optional title
        re.MULTILINE,
    )

    for match in pattern1.finditer(text):
        quote_text = match.group(1).strip()
        name = match.group(2).strip()
        title = match.group(3).strip() if match.group(3) else ""

        quotes.append(
            {
                "text": quote_text,
                "name": name,
                "title": title,
            }
        )

    # Pattern: "Quote" - Name, Title
    pattern2 = re.compile(
        r'"([^"]+)"\s*[-–—]\s*'
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'  # Name
        r'(?:,\s*(.+?))?(?:\.|$)',
        re.MULTILINE,
    )

    for match in pattern2.finditer(text):
        quote_text = match.group(1).strip()
        name = match.group(2).strip()
        title = match.group(3).strip() if match.group(3) else ""

        # Avoid duplicates
        if not any(q["text"] == quote_text for q in quotes):
            quotes.append(
                {
                    "text": quote_text,
                    "name": name,
                    "title": title,
                }
            )

    return quotes


def extract_key_points(text: str) -> list[str]:
    """Extract key points or bullet items from text.

    Looks for:
    - Bulleted lists (-, *, •)
    - Numbered lists (1., 2., etc.)
    - Lines following "Key points:" or similar headers

    Args:
        text: Text to search for key points

    Returns:
        List of key point strings
    """
    points = []

    # Find bullet points
    bullet_pattern = re.compile(r"^\s*[-*•]\s+(.+)$", re.MULTILINE)
    for match in bullet_pattern.finditer(text):
        point = match.group(1).strip()
        if point and len(point) > 5:  # Filter out very short items
            points.append(point)

    # Find numbered items
    numbered_pattern = re.compile(r"^\s*\d+[.)]\s+(.+)$", re.MULTILINE)
    for match in numbered_pattern.finditer(text):
        point = match.group(1).strip()
        if point and len(point) > 5:
            points.append(point)

    return points


def localize_spelling(text: str, audience: Audience) -> str:
    """Convert spelling to match target audience.

    Converts between UK and US spelling conventions.

    Args:
        text: Text to localize
        audience: Target audience

    Returns:
        Text with localized spelling
    """
    # UK to US conversions
    uk_to_us = {
        "colour": "color",
        "favour": "favor",
        "honour": "honor",
        "labour": "labor",
        "neighbour": "neighbor",
        "organisation": "organization",
        "recognise": "recognize",
        "realise": "realize",
        "analyse": "analyze",
        "centre": "center",
        "metre": "meter",
        "defence": "defense",
        "licence": "license",
        "programme": "program",
        "behaviour": "behavior",
        "travelling": "traveling",
        "modelling": "modeling",
    }

    if audience == Audience.US:
        for uk, us in uk_to_us.items():
            # Case-insensitive replacement preserving case
            pattern = re.compile(re.escape(uk), re.IGNORECASE)
            text = pattern.sub(lambda m: _match_case(us, m.group()), text)
    elif audience == Audience.UK:
        for uk, us in uk_to_us.items():
            pattern = re.compile(re.escape(us), re.IGNORECASE)
            text = pattern.sub(lambda m: _match_case(uk, m.group()), text)

    return text


def _match_case(replacement: str, original: str) -> str:
    """Match the case of the original string in the replacement."""
    if original.isupper():
        return replacement.upper()
    elif original[0].isupper():
        return replacement.capitalize()
    else:
        return replacement.lower()

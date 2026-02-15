"""
Parse the mineral-exploration-machine-learning README to extract paper/report/thesis links.

This module fetches the README from the GitHub repository and extracts
all references to papers, reports, theses, and other academic resources.
"""

import json
import logging
import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import requests

from paper_checker.models import Paper, ResourceType, AccessibilityStatus

logger = logging.getLogger(__name__)

# Default repository to scan
DEFAULT_REPO_OWNER = "RichardScottOZ"
DEFAULT_REPO_NAME = "mineral-exploration-machine-learning"
DEFAULT_REPO_URL = f"https://github.com/{DEFAULT_REPO_OWNER}/{DEFAULT_REPO_NAME}"

# GitHub API URL for fetching raw README content
GITHUB_API_README_URL = (
    "https://api.github.com/repos/{owner}/{repo}/readme"
)

# Labels that indicate academic resources
PAPER_LABELS = {"paper", "papers"}
THESIS_LABELS = {"thesis", "theses", "phd", "honours thesis", "master's thesis"}
REPORT_LABELS = {"report", "reports"}
RESOURCE_LABELS = PAPER_LABELS | THESIS_LABELS | REPORT_LABELS

# Academic/publisher domains whose URLs indicate paper/publication references.
# Each entry is a substring matched against the URL.  Order does not matter.
ACADEMIC_URL_PATTERNS = (
    "researchgate.net/publication/",
    "researchgate.net/profile/",
    "arxiv.org/abs/",
    "arxiv.org/pdf/",
    "arxiv.org/html/",
    "sciencedirect.com/science/article/",
    "link.springer.com/article/",
    "link.springer.com/chapter/",
    "link.springer.com/epdf/",
    "nature.com/articles/",
    "ieeexplore.ieee.org/abstract/",
    "ieeexplore.ieee.org/document/",
    "ieeexplore.ieee.org/stamp/",
    "tandfonline.com/doi/",
    "wiley.com/doi/",
    "doi.org/10.",
    "mdpi.com/",
    "frontiersin.org/articles/",
    "frontiersin.org/journals/",
    "copernicus.org/articles/",
    "journals.plos.org/",
    "library.seg.org/",
    "pure.mpg.de/",
    "eartharxiv.org/",
    "researchsquare.com/",
    "joss.theoj.org/",
    "publications.csiro.au/",
    "eprints.",
    "pubs.usgs.gov/",
    "pubs.er.usgs.gov/",
    "geoscan.nrcan.gc.ca/",
)

# Non-document URL patterns to exclude (datasets, repos, videos, blogs, notebooks, web services, portals)
NON_DOCUMENT_URL_PATTERNS = (
    "youtube.com/",
    "youtu.be/",
    "medium.com/",
    "colab.research.google.com/",
    "zenodo.org/record/",  # datasets
    "figshare.com/articles/dataset/",
    "data.gov",
    "data.gov.au",
    "portal.",  # data portals
    "viewer.",  # map viewers
    "wms?",  # WMS endpoints
    "wfs?",  # WFS endpoints
    "api.",  # API endpoints
    "/api/",
    "swagger",
    "openapi",
)


def _label_to_resource_type(label: str) -> ResourceType:
    """Map a link label to a ResourceType."""
    label_lower = label.lower().strip()
    if label_lower in PAPER_LABELS:
        return ResourceType.PAPER
    if label_lower in THESIS_LABELS:
        return ResourceType.THESIS
    if label_lower in REPORT_LABELS:
        return ResourceType.REPORT
    return ResourceType.PAPER


def _is_academic_url(url: str) -> bool:
    """Return True if *url* points to a known academic publication site."""
    url_lower = url.lower()
    return any(pattern in url_lower for pattern in ACADEMIC_URL_PATTERNS)


def _is_non_document_url(url: str) -> bool:
    """Return True if *url* points to a non-document resource (dataset, video, blog, etc.)."""
    url_lower = url.lower()
    return any(pattern in url_lower for pattern in NON_DOCUMENT_URL_PATTERNS)


def _is_github_repo(url: str) -> bool:
    """
    Return True if *url* is a GitHub repository (not a paper/report/thesis).
    
    GitHub URLs pointing to papers/reports are typically:
    - releases with PDF attachments
    - specific files ending in .pdf
    - issues/discussions about papers
    
    Regular repo URLs (code) should be excluded unless explicitly labeled as paper/report/thesis.
    """
    if 'github.com' not in url.lower():
        return False
    
    # If it's a PDF file, it's likely a paper
    if url.endswith('.pdf'):
        return False
    
    # If it's a release, might contain papers
    if '/releases/' in url:
        return False
    
    # Otherwise, it's probably just a code repo
    return True


def fetch_readme(
    owner: str = DEFAULT_REPO_OWNER,
    repo: str = DEFAULT_REPO_NAME,
) -> str:
    """
    Fetch the raw README content from a GitHub repository using the GitHub API.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.

    Returns:
        The raw markdown text of the README.

    Raises:
        RuntimeError: If the README cannot be fetched.
    """
    api_url = GITHUB_API_README_URL.format(owner=owner, repo=repo)
    headers = {
        "Accept": "application/vnd.github.v3.raw",
        "User-Agent": "paper-accessibility-checker/0.1.0",
    }

    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Failed to fetch README from {owner}/{repo}: {exc}"
        ) from exc


def _find_section_for_line(lines: List[str], line_idx: int) -> str:
    """Walk backwards from *line_idx* to find the nearest markdown heading."""
    for i in range(line_idx, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def _build_section_path(lines: List[str], line_idx: int) -> str:
    """
    Build full section hierarchy path from markdown headings.
    
    Walks backwards from line_idx to collect all heading levels (#, ##, ###, ####)
    and returns a path like "Prospectivity/Oceania/Australia/South_Australia".
    
    Args:
        lines: All lines from the README
        line_idx: Current line index
        
    Returns:
        Full section path with "/" separators, ASCII-ized for filesystem safety
    """
    # Collect all headings with their levels
    headings = []  # List of (level, text) tuples
    
    for i in range(line_idx, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith("#"):
            # Count heading level
            level = 0
            for char in stripped:
                if char == "#":
                    level += 1
                else:
                    break
            text = stripped.lstrip("#").strip()
            headings.append((level, text))
    
    if not headings:
        return ""
    
    # Reverse to get top-down order
    headings.reverse()
    
    # Build hierarchy: only include headings that form a proper nesting
    path_parts = []
    last_level = 0
    
    for level, text in headings:
        if level > last_level:
            # Deeper level - add to path
            path_parts.append(text)
            last_level = level
        elif level == last_level:
            # Same level - replace last part
            if path_parts:
                path_parts[-1] = text
            else:
                path_parts.append(text)
        else:
            # Shallower level - pop back and add
            while path_parts and last_level >= level:
                path_parts.pop()
                last_level -= 1
            path_parts.append(text)
            last_level = level
    
    # Join with "/" and ASCII-ize for filesystem safety
    path = "/".join(path_parts)
    # Replace spaces with underscores, remove special chars
    path = re.sub(r'[^\w\s/\-]', '', path)
    path = path.replace(" ", "_")
    return path


def _indent_level(line: str) -> int:
    """Calculate indentation level, normalizing tabs to 4 spaces."""
    raw = line.expandtabs(4)
    return len(raw) - len(raw.lstrip())


def _extract_parent_context(lines: List[str], line_idx: int) -> Tuple[str, str]:
    """
    For a sub-item (indented bullet with a paper/thesis/report link), look at
    the parent bullet to get a title and possibly a repository URL.

    Returns (parent_title, parent_url).
    """
    current_indent = _indent_level(lines[line_idx])
    for i in range(line_idx - 1, -1, -1):
        line = lines[i]
        indent = _indent_level(line)
        if indent < current_indent and line.strip().startswith(("*", "-")):
            # Found parent bullet — extract its link
            m = re.search(r'\[([^\]]+)\]\((https?://[^)]+)\)', line)
            if m:
                return m.group(1), m.group(2)
            # Parent has no link — use its text, cleaning markdown artifacts
            text = re.sub(r'^\s*[\*\-]\s*', '', line).strip()
            text = re.sub(r'^\[|\]$', '', text).strip()
            return text, ""
    return "", ""


def parse_readme(readme_text: str, aggressive: bool = True) -> List[Paper]:
    """
    Parse a README markdown string and extract all paper/report/thesis entries.

    Handles several link patterns found in the mineral-exploration-machine-learning
    README:
        1. ``[paper](url)`` / ``[Paper](url)`` / ``[report](url)`` etc.
        2. ``[paper] -> url`` or ``[paper]url`` (broken/arrow-style/typo links)
        3. Lines mentioning *thesis* / *PhD thesis* with a URL
        4. Bare academic URLs on a line (e.g. ``- https://researchgate.net/publication/...``)
        5. Markdown links ``[Title](academic_url)`` pointing to known academic domains

    When aggressive=True (default), also handles:
        - Missing https:// prefix: ``[paper](www.sciencedirect.com/...)``
        - Double parens: ``[paper]((url))``
        - Bare URLs without protocol prefix

    Each extracted entry is returned as a :class:`Paper` object with as much
    metadata filled in as possible (title from the parent bullet, section as a
    keyword, URL, and resource type).
    
    Duplicate detection: Papers with the same URL will have their `duplicate_of`
    field set to the ID (1-based index) of the first occurrence.

    Args:
        readme_text: Raw markdown content.
        aggressive: Enable aggressive parsing for messy/broken links (default: True).

    Returns:
        List of Paper objects extracted from the README.
    """
    papers: List[Paper] = []
    seen_urls: dict = {}  # url -> first paper index (1-based)
    lines = readme_text.splitlines()

    for idx, line in enumerate(lines):
        extracted = _extract_entries_from_line(line, lines, idx, aggressive)
        for paper in extracted:
            # Track URL for duplicate detection
            if paper.url:
                if paper.url in seen_urls:
                    # This is a duplicate - set duplicate_of to first occurrence
                    paper.duplicate_of = seen_urls[paper.url]
                else:
                    # First occurrence - record it (1-based index)
                    seen_urls[paper.url] = len(papers) + 1
            papers.append(paper)

    return papers


def _is_anchor_link(url: str) -> bool:
    """Check if a URL is a GitHub self-referencing anchor link (e.g. repo#section)."""
    parsed = urlparse(url)
    # GitHub repo URLs have at most 2 path segments (/owner/repo); an anchor
    # fragment on such a URL is a table-of-contents link, not an academic resource.
    netloc = parsed.netloc.lower()
    is_github = netloc == "github.com" or netloc.endswith(".github.com")
    return bool(parsed.fragment) and (
        is_github
        and parsed.path.rstrip("/").count("/") <= 2
        and not re.search(r'\.(pdf|html|htm)$', parsed.path, re.IGNORECASE)
    )


def _normalize_url(url: str, aggressive: bool = True) -> Optional[str]:
    """
    Normalize and fix common URL issues.
    
    Args:
        url: Raw URL string
        aggressive: If True, attempt to fix missing protocols and other issues
        
    Returns:
        Normalized URL or None if invalid
    """
    if not url:
        return None
    
    # Strip whitespace and common trailing punctuation
    url = url.strip().rstrip(',;>)')
    
    # Check for file:/// paths - these are human errors
    # Return a special marker so caller can set HUMAN_ERROR status
    if url.startswith('file:///'):
        return 'file:///__HUMAN_ERROR__'
    
    # If aggressive mode and URL looks like it's missing protocol
    if aggressive:
        # Handle www. prefix without protocol
        if url.startswith('www.'):
            url = 'https://' + url
        # Handle common academic domains without protocol
        elif any(domain in url.lower() for domain in [
            'researchgate.net', 'arxiv.org', 'sciencedirect.com',
            'springer.com', 'ieee.org', 'doi.org'
        ]) and not url.startswith(('http://', 'https://')):
            url = 'https://' + url
    
    # Must have a protocol at this point
    if not url.startswith(('http://', 'https://')):
        return None
    
    return url


def _extract_entries_from_line(
    line: str, lines: List[str], idx: int, aggressive: bool = True
) -> List[Paper]:
    """Extract zero or more Paper entries from a single README line."""
    results: List[Paper] = []
    section = _find_section_for_line(lines, idx)
    section_path = _build_section_path(lines, idx)
    
    # Check if line contains [UNSEEN] tag
    unseen_tag = '[UNSEEN]' in line or '[unseen]' in line

    # --- Pattern 1: [paper](url), [Paper](url), [report](url), etc. ---
    # Also handle double parens: [paper]((url))
    pattern1_regex = (
        r'\[(' + '|'.join(re.escape(l) for l in RESOURCE_LABELS) + 
        r')\]\(\(?([^)]+)\)?\)'
    )
    for m in re.finditer(pattern1_regex, line, re.IGNORECASE):
        label = m.group(1)
        raw_url = m.group(2)
        url = _normalize_url(raw_url, aggressive)
        if not url:
            continue
        # Check for file:/// human error
        if url == 'file:///__HUMAN_ERROR__':
            paper = Paper(
                title=_extract_parent_context(lines, idx)[0] or "Invalid file:/// URL",
                url=raw_url,
                resource_type=_label_to_resource_type(label),
                keywords=[section] if section else [],
                section_path=section_path,
                accessibility_status=AccessibilityStatus.HUMAN_ERROR,
                unseen_tag=unseen_tag,
            )
            results.append(paper)
            continue
        # Skip non-document URLs
        if _is_non_document_url(url):
            continue
        if _is_anchor_link(url):
            continue
        resource_type = _label_to_resource_type(label)
        title, parent_url = _extract_parent_context(lines, idx)
        if not title:
            title = _title_from_url(url)
        paper = Paper(
            title=title,
            url=url,
            resource_type=resource_type,
            keywords=[section] if section else [],
            section_path=section_path,
            unseen_tag=unseen_tag,
        )
        results.append(paper)

    # --- Pattern 2: [paper] -> url  or [paper]url  (broken/typo links) ---
    # Matches both the arrow-style "[paper] -> url" and the typo variant
    # "[paper]url" or "[paper] url" where parentheses are missing.
    noparen_pattern = re.compile(
        r'\[(' + '|'.join(re.escape(l) for l in RESOURCE_LABELS)
        + r')\]\s*(?:->\s*)?(\S+)',
        re.IGNORECASE,
    )
    for m in noparen_pattern.finditer(line):
        label = m.group(1)
        raw_url = m.group(2)
        # Skip if this looks like it was already captured by pattern 1
        if raw_url.startswith('('):
            continue
        url = _normalize_url(raw_url, aggressive)
        if not url:
            continue
        # Check for file:/// human error
        if url == 'file:///__HUMAN_ERROR__':
            paper = Paper(
                title=_extract_parent_context(lines, idx)[0] or "Invalid file:/// URL",
                url=raw_url,
                resource_type=_label_to_resource_type(label),
                keywords=[section] if section else [],
                section_path=section_path,
                accessibility_status=AccessibilityStatus.HUMAN_ERROR,
                unseen_tag=unseen_tag,
            )
            results.append(paper)
            continue
        # Skip non-document URLs
        if _is_non_document_url(url):
            continue
        resource_type = _label_to_resource_type(label)
        title, _ = _extract_parent_context(lines, idx)
        if not title:
            title = _title_from_url(url)
        paper = Paper(
            title=title,
            url=url,
            resource_type=resource_type,
            keywords=[section] if section else [],
            section_path=section_path,
            unseen_tag=unseen_tag,
        )
        results.append(paper)

    # --- Pattern 3: Lines containing thesis/PhD with a URL ---
    if re.search(r'(?:thesis|theses|phd)', line, re.IGNORECASE) and not results:
        # Look for URLs in various formats
        urls_found = set()  # Use set to avoid duplicates within same line
        # Normal URLs
        for url in re.findall(r'https?://\S+', line):
            # Clean markdown artifacts
            url = re.split(r'[\]\)],?', url)[0]
            url = url.rstrip(',;>)')
            urls_found.add(url)
        # Also check for backwards markdown: [url](text)
        for url in re.findall(r'\[(https?://[^\]]+)\]\([^\)]+\)', line):
            urls_found.add(url)
        
        for raw_url in urls_found:
            url = _normalize_url(raw_url, aggressive)
            if not url:
                continue
            # Check for file:/// human error
            if url == 'file:///__HUMAN_ERROR__':
                paper = Paper(
                    title=_extract_parent_context(lines, idx)[0] or "Invalid file:/// URL",
                    url=raw_url,
                    resource_type=ResourceType.THESIS,
                    keywords=[section] if section else [],
                    section_path=section_path,
                    accessibility_status=AccessibilityStatus.HUMAN_ERROR,
                    unseen_tag=unseen_tag,
                )
                results.append(paper)
                continue
            # Skip non-document URLs
            if _is_non_document_url(url):
                continue
            # Skip GitHub repo URLs (not academic papers)
            if _is_github_repo(url):
                continue
            # Try to extract a markdown-linked title (normal format)
            title_match = re.search(r'\[([^\]]+)\]\(\s*' + re.escape(raw_url), line)
            if title_match:
                title = title_match.group(1)
                # If title is the URL itself (backwards format), look for text after arrow
                if title.startswith('http'):
                    arrow_match = re.search(r'->\s*(.+?)(?:\s*$)', line)
                    if arrow_match:
                        title = arrow_match.group(1).strip()
                    else:
                        title, _ = _extract_parent_context(lines, idx)
                        if not title:
                            title = _title_from_url(url)
            else:
                title, _ = _extract_parent_context(lines, idx)
                if not title:
                    title = _title_from_url(url)
            paper = Paper(
                title=title,
                url=url,
                resource_type=ResourceType.THESIS,
                keywords=[section] if section else [],
                section_path=section_path,
                unseen_tag=unseen_tag,
            )
            results.append(paper)

    # --- Pattern 4 & 5: Academic URLs not already captured ---
    # Collect URLs already found by patterns 1-3 so we don't duplicate them.
    seen = {p.url for p in results if p.url}
    _extract_academic_urls(line, lines, idx, section, results, seen, section_path, aggressive, unseen_tag)

    return results


def _extract_academic_urls(
    line: str,
    lines: List[str],
    idx: int,
    section: str,
    results: List[Paper],
    seen: Optional[set] = None,
    section_path: str = "",
    aggressive: bool = True,
    unseen_tag: bool = False,
) -> None:
    """Detect academic paper URLs that are not wrapped in [paper]/[report]/[thesis] labels.

    Handles two sub-patterns:
        4. Bare academic URLs on a bullet line, e.g.
           ``- https://www.researchgate.net/publication/...``
        5. Markdown links whose text is a paper title and whose URL points to a
           known academic domain, e.g.
           ``* [GeoCoDa](https://www.researchgate.net/publication/...)``
    """
    if seen is None:
        seen = set()

    # Check if line mentions thesis/PhD to determine resource type
    is_thesis_line = bool(re.search(r'(?:thesis|theses|phd)', line, re.IGNORECASE))
    
    # Collect all URLs on the line - in aggressive mode, also look for URLs without protocol
    if aggressive:
        # Match URLs with protocol OR domain-like patterns (but not inside markdown brackets)
        url_pattern = r'(?<!\[)(?:https?://\S+|(?:www\.|[a-z0-9-]+\.(?:com|org|net|edu|gov|io|co\.uk))/\S+)'
    else:
        url_pattern = r'https?://\S+'
    
    for raw_url in re.findall(url_pattern, line):
        url = _normalize_url(raw_url, aggressive)
        if not url:
            continue
        # Check for file:/// human error
        if url == 'file:///__HUMAN_ERROR__':
            # Don't add file:/// URLs from academic URL pattern - they should be caught by explicit patterns
            continue
        if url in seen:
            continue
        # Skip non-document URLs
        if _is_non_document_url(url):
            continue
        # Skip GitHub repos unless they're academic URLs
        if _is_github_repo(url) and not _is_academic_url(url):
            continue
        if not _is_academic_url(url):
            continue
        if _is_anchor_link(url):
            continue

        # Try to get a markdown-linked title: [Title](url)
        # Also handle [Title] (url) with an extra space before the paren
        title_match = re.search(
            r'\[([^\]]+)\]\s*\(\s*' + re.escape(raw_url), line
        )
        if title_match:
            title = title_match.group(1)
            # Skip generic labels that would have been caught by pattern 1
            if title.lower().strip() in RESOURCE_LABELS:
                continue
        else:
            # Try extracting a title from "-> Title" after the URL.
            # The title ends at a bracket (used for annotations like [includes model])
            # or at end of line.
            arrow_match = re.search(
                re.escape(raw_url) + r'\s*->\s*(.+?)(?:\s*\[|$)', line
            )
            if arrow_match:
                title = arrow_match.group(1).strip()
            else:
                title, _ = _extract_parent_context(lines, idx)
                if not title:
                    title = _title_from_url(url)

        # Determine resource type based on line content
        resource_type = ResourceType.THESIS if is_thesis_line else ResourceType.PAPER
        
        paper = Paper(
            title=title,
            url=url,
            resource_type=resource_type,
            keywords=[section] if section else [],
            section_path=section_path,
            unseen_tag=unseen_tag,
        )
        results.append(paper)
        seen.add(url)


def _title_from_url(url: str) -> str:
    """Derive a human-readable title from a URL when no other title is available."""
    parsed = urlparse(url)
    # Use the last meaningful path segment
    path = parsed.path.rstrip("/")
    if path:
        segment = path.split("/")[-1]
        # Remove common file extensions only
        segment = re.sub(r'\.(pdf|html|htm|xml|txt|doc|docx)$', '', segment, flags=re.IGNORECASE)
        # Replace separators with spaces
        segment = segment.replace("-", " ").replace("_", " ")
        if segment:
            return segment
    return url


def scan_repo(
    owner: str = DEFAULT_REPO_OWNER,
    repo: str = DEFAULT_REPO_NAME,
) -> List[Paper]:
    """
    Fetch the README from a GitHub repository and extract all paper/report/thesis
    entries.

    This is the main entry point for scanning the mineral-exploration-machine-learning
    repository (or any other GitHub repository).

    Args:
        owner: GitHub repository owner (default: RichardScottOZ).
        repo: GitHub repository name (default: mineral-exploration-machine-learning).

    Returns:
        List of Paper objects extracted from the README.
    """
    readme_text = fetch_readme(owner, repo)
    return parse_readme(readme_text)

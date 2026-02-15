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

from paper_checker.models import Paper, ResourceType

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
            # Parent has no link — use its text
            text = re.sub(r'^\s*[\*\-]\s*', '', line).strip()
            return text, ""
    return "", ""


def parse_readme(readme_text: str) -> List[Paper]:
    """
    Parse a README markdown string and extract all paper/report/thesis entries.

    Handles several link patterns found in the mineral-exploration-machine-learning
    README:
        1. ``[paper](url)`` / ``[Paper](url)`` / ``[report](url)`` etc.
        2. ``[paper] -> url`` (broken/arrow-style link)
        3. Lines mentioning *thesis* / *PhD thesis* with a URL
        4. Bare URLs on their own line that mention thesis or report

    Each extracted entry is returned as a :class:`Paper` object with as much
    metadata filled in as possible (title from the parent bullet, section as a
    keyword, URL, and resource type).

    Args:
        readme_text: Raw markdown content.

    Returns:
        List of Paper objects extracted from the README.
    """
    papers: List[Paper] = []
    seen_urls: set = set()
    lines = readme_text.splitlines()

    for idx, line in enumerate(lines):
        extracted = _extract_entries_from_line(line, lines, idx)
        for paper in extracted:
            # Deduplicate by URL
            if paper.url and paper.url in seen_urls:
                continue
            if paper.url:
                seen_urls.add(paper.url)
            papers.append(paper)

    return papers


def _is_anchor_link(url: str) -> bool:
    """Check if a URL is a GitHub self-referencing anchor link (e.g. repo#section)."""
    parsed = urlparse(url)
    return bool(parsed.fragment) and (
        "github.com" in parsed.netloc
        and parsed.path.rstrip("/").count("/") <= 2
        and not re.search(r'\.(pdf|html|htm)$', parsed.path, re.IGNORECASE)
    )


def _extract_entries_from_line(
    line: str, lines: List[str], idx: int
) -> List[Paper]:
    """Extract zero or more Paper entries from a single README line."""
    results: List[Paper] = []
    section = _find_section_for_line(lines, idx)

    # --- Pattern 1: [paper](url), [Paper](url), [report](url), etc. ---
    for m in re.finditer(
        r'\[(' + '|'.join(re.escape(l) for l in RESOURCE_LABELS) + r')\]\((https?://[^)]+)\)',
        line,
        re.IGNORECASE,
    ):
        label = m.group(1)
        url = m.group(2)
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
        )
        results.append(paper)

    # --- Pattern 2: [paper] -> url  (arrow-style broken links) ---
    arrow_pattern = re.compile(
        r'\[(' + '|'.join(re.escape(l) for l in RESOURCE_LABELS)
        + r')\]\s*->\s*(https?://\S+)',
        re.IGNORECASE,
    )
    for m in arrow_pattern.finditer(line):
        label = m.group(1)
        url = m.group(2).rstrip(')')
        resource_type = _label_to_resource_type(label)
        title, _ = _extract_parent_context(lines, idx)
        if not title:
            title = _title_from_url(url)
        paper = Paper(
            title=title,
            url=url,
            resource_type=resource_type,
            keywords=[section] if section else [],
        )
        results.append(paper)

    # --- Pattern 3: Lines containing thesis/PhD with a URL ---
    if re.search(r'(?:thesis|theses|phd)', line, re.IGNORECASE) and not results:
        urls = re.findall(r'(https?://\S+)', line)
        for raw_url in urls:
            url = raw_url.rstrip(')').rstrip(',')
            # Try to extract a markdown-linked title
            title_match = re.search(r'\[([^\]]+)\]\(' + re.escape(raw_url), line)
            if title_match:
                title = title_match.group(1)
            else:
                title, _ = _extract_parent_context(lines, idx)
                if not title:
                    title = _title_from_url(url)
            paper = Paper(
                title=title,
                url=url,
                resource_type=ResourceType.THESIS,
                keywords=[section] if section else [],
            )
            results.append(paper)

    return results


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

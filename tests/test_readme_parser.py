"""
Tests for the README parser module.
"""

import pytest

from paper_checker.models import Paper, ResourceType
from paper_checker.readme_parser import (
    parse_readme,
    _label_to_resource_type,
    _title_from_url,
    _extract_parent_context,
    DEFAULT_REPO_OWNER,
    DEFAULT_REPO_NAME,
)


def test_label_to_resource_type():
    """Test mapping labels to resource types."""
    assert _label_to_resource_type("paper") == ResourceType.PAPER
    assert _label_to_resource_type("Paper") == ResourceType.PAPER
    assert _label_to_resource_type("papers") == ResourceType.PAPER
    assert _label_to_resource_type("thesis") == ResourceType.THESIS
    assert _label_to_resource_type("PhD") == ResourceType.THESIS
    assert _label_to_resource_type("report") == ResourceType.REPORT
    assert _label_to_resource_type("Report") == ResourceType.REPORT


def test_title_from_url():
    """Test deriving title from URL."""
    assert _title_from_url("https://arxiv.org/abs/2301.12345") == "2301.12345"
    assert _title_from_url("https://example.com/some-paper-title.pdf") == "some paper title"
    assert _title_from_url("https://example.com/") == "https://example.com/"


def test_parse_readme_paper_link():
    """Test parsing standard [paper](url) links."""
    readme = """\
# Section One
* [My Cool Project](https://github.com/example/project) -> Description
\t* [paper](https://arxiv.org/abs/2301.12345)
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].url == "https://arxiv.org/abs/2301.12345"
    assert papers[0].resource_type == ResourceType.PAPER
    assert papers[0].title == "My Cool Project"
    assert "Section One" in papers[0].keywords


def test_parse_readme_report_link():
    """Test parsing [Report](url) links."""
    readme = """\
# Reports
* [National Survey](https://example.gov/survey)
\t* [Report](https://example.gov/report.pdf)
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].url == "https://example.gov/report.pdf"
    assert papers[0].resource_type == ResourceType.REPORT


def test_parse_readme_arrow_link():
    """Test parsing [paper] -> url style links."""
    readme = """\
# Section
* [pyClusterwise](https://pypi.org/project/pyClusterWise/)
  * [paper] -> https://www.sciencedirect.com/science/article/pii/S0169136825001519 -> Description
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].url == "https://www.sciencedirect.com/science/article/pii/S0169136825001519"
    assert papers[0].resource_type == ResourceType.PAPER
    assert papers[0].title == "pyClusterwise"


def test_parse_readme_thesis_inline():
    """Test parsing lines mentioning thesis with inline URLs."""
    readme = """\
# Theses
- https://example.edu/thesis/12345 -> PhD thesis about ML
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].url == "https://example.edu/thesis/12345"
    assert papers[0].resource_type == ResourceType.THESIS


def test_parse_readme_thesis_markdown_link():
    """Test parsing thesis references that are markdown links."""
    readme = """\
# Prospectivity
* [Machine learning for geological mapping](https://eprints.utas.edu.au/18571/) -> PhD thesis with code
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].url == "https://eprints.utas.edu.au/18571/"
    assert papers[0].resource_type == ResourceType.THESIS


def test_parse_readme_deduplication():
    """Test that duplicate URLs are skipped."""
    readme = """\
# Section
* [Project A](https://github.com/a)
\t* [paper](https://arxiv.org/abs/1111)
* [Project B](https://github.com/b)
\t* [paper](https://arxiv.org/abs/1111)
"""
    papers = parse_readme(readme)
    assert len(papers) == 1


def test_parse_readme_multiple_papers():
    """Test parsing multiple paper entries."""
    readme = """\
# Deep Learning
* [Project A](https://github.com/a)
\t* [paper](https://arxiv.org/abs/1111)
* [Project B](https://github.com/b)
\t* [paper](https://arxiv.org/abs/2222)

# Geology
* [Project C](https://github.com/c)
\t* [paper](https://doi.org/10.1234/5678)
"""
    papers = parse_readme(readme)
    assert len(papers) == 3
    urls = {p.url for p in papers}
    assert "https://arxiv.org/abs/1111" in urls
    assert "https://arxiv.org/abs/2222" in urls
    assert "https://doi.org/10.1234/5678" in urls


def test_parse_readme_empty():
    """Test parsing an empty README."""
    papers = parse_readme("")
    assert papers == []


def test_parse_readme_no_papers():
    """Test parsing a README with no paper links."""
    readme = """\
# My Project
This is a project without any paper links.
* [GitHub](https://github.com/example)
"""
    papers = parse_readme(readme)
    assert papers == []


def test_parse_readme_honours_thesis_link():
    """Test parsing [Honours Thesis](url) links."""
    readme = """\
# Theses
* [Some Project](https://github.com/example)
\t* [Honours Thesis](https://www.researchgate.net/thesis.pdf)
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].resource_type == ResourceType.THESIS


def test_extract_parent_context():
    """Test extracting parent bullet context."""
    lines = [
        "# Section",
        "* [Parent Project](https://github.com/parent) -> Description",
        "\t* [paper](https://arxiv.org/abs/1234)",
    ]
    title, url = _extract_parent_context(lines, 2)
    assert title == "Parent Project"
    assert url == "https://github.com/parent"


def test_extract_parent_context_no_parent():
    """Test extracting parent context when there is no parent."""
    lines = [
        "# Section",
        "* [paper](https://arxiv.org/abs/1234)",
    ]
    title, url = _extract_parent_context(lines, 1)
    # No parent bullet with smaller indent
    assert title == ""
    assert url == ""


def test_anchor_link_filtered():
    """Test that GitHub anchor links (e.g. repo#section) are filtered out."""
    readme = """\
# Table of Contents
* [Papers](https://github.com/RichardScottOZ/mineral-exploration-machine-learning#papers)
"""
    papers = parse_readme(readme)
    assert papers == []


def test_thesis_url_cleaned():
    """Test that thesis URLs with markdown artifacts are cleaned."""
    readme = """\
# Ontology
* [geosim](https://github.com/smolang/SemanticObjects/tree/geosim)
\t* [https://www.duo.uio.no/handle/10852/111467](Knowledge Modelling) -> PhD thesis
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].url == "https://www.duo.uio.no/handle/10852/111467"
    assert "]" not in papers[0].url


def test_default_repo_constants():
    """Test that default repo constants are set correctly."""
    assert DEFAULT_REPO_OWNER == "RichardScottOZ"
    assert DEFAULT_REPO_NAME == "mineral-exploration-machine-learning"
